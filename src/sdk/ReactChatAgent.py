from pydantic import Field, BaseModel
from pilot.Output import BaseOutput
from sdk.CodeImp import CodeMonkeyRefactoredArgs
from pilot.utils.shell import RunShellArgs
from typing import List, Union, Optional, Type, Dict, Callable, Tuple
import openai
import os
import json
import enum
import logging
import jinja2

from pilot.util import format_plugin_schema
from pilot.utils.basetool import BaseTool
from pilot.utils.base_agent import BaseAgent
from pilot.utils.agent_model import AgentType, AgentOutput
from pilot.utils.prompt_template import PromptTemplate
from pilot.utils.base import AgentFinish, AgentAction
from pydantic import create_model, BaseModel
from pygments import highlight, lexers, formatters
import instructor


class ChatCompletionArgs(BaseModel):
    engine: str
    messages: list[dict]
    response_model: Optional[Type[BaseModel]] = None
    function_call: Optional[Dict] = None
    functions: Optional[List[Callable]] = None
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None
    top_p: Optional[float] = None
    frequency_penalty: Optional[float] = None
    stop: Optional[List[str]] = None


class Tool(enum.Enum):
    CodeMonkey = "CodeMonkey"
    RunShell = "bash_shell"


class TalksEntity(BaseModel):
    # id: int = Field(..., description="id of the action")
    developer: str = Field(...,
                           description="extract the the developer part of the conversation, ")
    coding_worker: str = Field(...,
                               description="extract the the coding worker part of the conversation, ")
    # tool: Tool = Field(..., description="tool to use to do the action")
    # tool_input: Union[RunShellArgs,
    #   CodeMonkeyRefactoredArgs] = Field(..., description="input to the tool")
    # questions: str = Field(
    #     None, description="question from coding worker for unclear parts, if no, just say no more questions")
    # dependencies: List[int] = Field(
    #     ..., description="list of action ids that this action depends on")


class ActionItem(BaseModel):
    id: int = Field(..., description="id of the action")
    tool: Tool = Field(..., description="tool to use to do the action")
    tool_input: Union[RunShellArgs,
                      CodeMonkeyRefactoredArgs] = Field(..., description="input to the tool")
    dependencies: List[int] = Field(
        ..., description="list of action ids that this action depends on")


class FinalAnswerEntity(BaseModel):
    output: Optional[str] = Field(
        ..., description="if it is a final state, text summary of the final answer")
    ActionList: List[ActionItem] = Field(
        ..., description="list of actions with order")


class ResponseEntity(BaseModel):
    action: Union[TalksEntity, FinalAnswerEntity] = Field(
        ..., description="state of talks between developer and coding worker, still in discussion or reach a final answer state, no unclear parts")


# print(ResponseEntity.schema_json(indent=2))
class User(BaseModel):
    name: str = Field(description="The name of the person")
    age: int = Field(description="The age of the person")
    role: str = Field(description="The role of the person")


# user = User(name="Jason Liu", age=20, role="student")
# logger = PathLogger(__name__)
# logger.debug(json.dumps(ResponseEntity.model_json_schema(), indent=2))
# project = Project({})
# agent = Agent('user', project)
# system_message = ""
# system_message += "Any Instruction you get which labeled as **IMPORTANT**, you follow strictly."

# convo = AgentConvo(agent,system_message)
FINAL_ANSWER_ACTION = "Final Answer:"
output = BaseOutput()
openai.api_type = "azure"
openai.api_base = os.getenv("AZURE_OPENAI_ENDPOINT")
openai.api_version = "2023-07-01-preview"
openai.api_key = os.getenv("AZURE_API_KEY")
deployment_name = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME")


class ReactChatAgent(BaseAgent):
    name: str = "ReactAgent"
    type: AgentType = AgentType.react
    version: str
    description: str
    # target_tasks: list[str]
    prompt_template: PromptTemplate
    respone: object
    plugins: List[Union[BaseTool, BaseAgent]]
    examples: Union[str, List[str]] = None  # type: ignore
    args_schema: Optional[Type[BaseModel]] = create_model(
        "ReactArgsSchema", instruction=(str, ...))
    logger: Optional[object]

    intermediate_steps: List[Tuple[AgentAction, str]] = []
    intermediate_steps_index: int = 0

    raw_message: List[str] = []

    def set_logger(self, logger):
        self.logger = logger

    def artifact_handler(self):
        self.logger.info("artifact_handler")
        return

    # server agent api, hand to agent to wrap the response for a agent protocol
    def api_task(self, input):
        self.logger.info(f"api_task: {input}")
        self.run_monkey(input)
        # self.run(input)
        # self.get_final_answer()
        return

    def api_step(self, step):
        self.logger.info(f"api_step: {step}")
        self.run(step)
        return

    def _compose_plugin_description(self) -> str:
        """
        Compose the worker prompt from the workers.

        Example:
        toolname1[input]: tool1 description
        toolname2[input]: tool2 description
        """
        prompt = ""
        try:
            for plugin in self.plugins:
                prompt += f"{plugin.name}: {plugin.description}\n"
        except Exception:
            raise ValueError("Worker must have a name and description.")
        return prompt

    def _construct_raw_message(self, raw: List[str]) -> str:
        return "\n".join(raw)

    def _construct_action_scratchpad(
            self, intermediate_steps: List[Tuple[TalksEntity, str]]
    ) -> str:
        """Construct the scratchpad that lets the agent continue its thought process."""
        thoughts = ""
        # for action, justdoit, observation, sufix in intermediate_steps:
        for action in intermediate_steps:
            #     if action.questions is None or action.questions == "":
            #         action.questions = "no more questions"
            thoughts += f"\nDeveloper:"
            thoughts += action.developer
            thoughts += f"\nCoding worker: {action.coding_worker}"
            # thoughts += f"\nCoding worker: {action.coding_worker} \nQuestions:"
            # thoughts += f"{action.questions}\nDeveloper:"
            # thoughts += f"\nAction Input: {action.tool_input}"
        # replace <content> with content
        # thoughts = re.sub(r"<(.*?)>", r"\1", thoughts)
        return thoughts

    def _construct_scratchpad(
            self, intermediate_steps: List[Tuple[AgentAction, str]]
    ) -> str:
        """Construct the scratchpad that lets the agent continue its thought process."""
        thoughts = ""
        # for action, justdoit, observation, sufix in intermediate_steps:
        for action, observation in intermediate_steps:
            thoughts += action.log
            thoughts += f"\nObservation: {observation}\nThought:"
        # replace <content> with content
        # thoughts = re.sub(r"<(.*?)>", r"\1", thoughts)
        return thoughts

    def _parse_output(self, text: str) -> Union[AgentAction, AgentFinish]:
        import re
        includes_answer = FINAL_ANSWER_ACTION in text
        regex = (
            r"Action\s*\d*\s*:[\s]*(.*?)[\s]*Action\s*\d*\s*Input\s*\d*\s*:[\s]*(.*)"
        )
        action_match = re.search(regex, text, re.DOTALL)
        if action_match:
            if includes_answer:
                raise Exception(
                    "Parsing LLM output produced both a final answer "
                    f"and a parse-able action: {text}"
                )
            action = action_match.group(1).strip()
            action_input = action_match.group(2)
            tool_input = action_input.strip(" ")
            # ensure if its a well formed SQL query we don't remove any trailing " chars
            if tool_input.startswith("SELECT ") is False:
                tool_input = tool_input.strip('"')

            return AgentAction(action, tool_input, text)

        elif includes_answer:
            return AgentFinish(
                {"output": text.split(FINAL_ANSWER_ACTION)[-1].strip()}, text
            )

        if not re.search(r"Action\s*\d*\s*:[\s]*(.*?)", text, re.DOTALL):
            raise Exception(
                f"Could not parse LLM output: `{text}`",
            )
        elif not re.search(
                r"[\s]*Action\s*\d*\s*Input\s*\d*\s*:[\s]*(.*)", text, re.DOTALL
        ):
            raise Exception(
                f"Could not parse LLM output: `{text}`"
            )
        else:
            raise Exception(f"Could not parse LLM output: `{text}`")

    def _compose_condition_prompt(self, instruction) -> str:
        """
        Compose the prompt from template, worker description, examples and instruction.
        """
        agent_scratchpad = self._construct_scratchpad(self.intermediate_steps)
        tool_description = self._compose_plugin_description()
        tool_names = ", ".join([plugin.name for plugin in self.plugins])
        # if self.prompt_template is None:
        self.prompt_template = PromptTemplate(
            input_variables=["instruction", "agent_scratchpad",
                             "tool_names", "tool_description"],
            template="""
Action 1: Tool A
If success:
  Action 2: Tool B
Else: 
  Action 2: Tool C
"""
        )

    def _compose_prompt(self, instruction) -> str:
        """
        Compose the prompt from template, worker description, examples and instruction.
        """
        # agent_scratchpad = self._construct_action_scratchpad(
        #     self.intermediate_steps)
        agent_scratchpad = self._construct_raw_message(self.raw_message)
        tool_description = self._compose_plugin_description()
        tool_names = ", ".join([plugin.name for plugin in self.plugins])
        # if self.prompt_template is None:
        self.prompt_template = PromptTemplate(
            input_variables=["instruction", "agent_scratchpad",
                             "tool_names", "tool_description"],
            # current file path
            template=open(os.path.join(os.path.dirname(__file__),
                          "prompts/talks_dev_coder.md"), "r").read())
        test_prompt = self.get_prompt(self.prompt_template.template, {
            "instruction": instruction,
            "agent_scratchpad": agent_scratchpad,
            "tool_description": tool_description,
            "tool_names": tool_names
        })
        print(test_prompt)
        return self.prompt_template.format(
            instruction=instruction,
            agent_scratchpad=agent_scratchpad,
            tool_description=tool_description,
            tool_names=tool_names
        )

    def _format_function_map(self) -> Dict[str, Callable]:
        # Map the function name to the real function object.
        function_map = {}
        for plugin in self.plugins:
            if isinstance(plugin, BaseTool):
                function_map[plugin.name] = plugin._run
            else:
                function_map[plugin.name] = plugin.run
        return function_map

    def _format_multi_plugins_schema(self, plugins: List[Union[BaseTool, BaseAgent]]):
        """Format list of tools into the open AI function API.

        :param plugins: List of tools to be formatted.
        :type plugins: List[Union[BaseTool, BaseAgent]]
        :return: Formatted tools.
        :rtype: Dict
        """
        schema = {
            'type': 'object',
            'properties': {
                # "needs_plan_or_replan": {
                #     "type": "boolean",
                #     "description": "whether the task needs a plan or replan",
                # },
                "tools": {
                    'type': 'array',
                    'description': 'List of actions item that need to be done to complete the task. if a replan is needed, the list will only contain remaining actions which is fail or unknown.',
                    'items': {
                        'type': 'object',
                        'description': 'one of the action items that need to be done to complete the task.',
                        'properties': {
                            'name': {
                                'type': 'string',
                                'enum': [plugin.name for plugin in plugins],
                                'description': 'Name of the tool.',
                            },
                        }
                    },
                }
            }
        }
        for (i, plugin) in enumerate(plugins):
            schema['properties']['tools']['items']['properties'][plugin.name] = plugin.args_schema.schema()
        return {
            'name': 'process_tools',
            'description': 'Process list of tools',
            'parameters': schema,
        }

    def _response_from(self, response: Dict):
        # message = response["choices"][0]["message"]
        message = response
        # assert "function_calls" in message, "No function call detected"
        if "function_calls" not in message:
            func_name = self.intermediate_steps[self.intermediate_steps_index][0].tool
            func_args = self.intermediate_steps[self.intermediate_steps_index][0].tool_input
            self.intermediate_steps[-1][-1] = (
                self._format_function_map()[func_name](**func_args))
            self.intermediate_steps_index += 1
            return
        # remove items after self.intermediate_steps_index
        while len(self.intermediate_steps) > self.intermediate_steps_index and len(self.intermediate_steps) > 0:
            self.intermediate_steps.pop()
            # self.intermediate_steps[self.intermediate_steps_index][-1] = "throw the plan away"
            # self.intermediate_steps[self.intermediate_steps_index][-2] = "no observation"
            # self.intermediate_steps[self.intermediate_steps_index].remove_last_2_messages()
            # self.intermediate_steps[self.intermediate_steps_index].pop()
            # self.intermediate_steps[self.intermediate_steps_index].pop()
            # self.intermediate_steps_index += 1
        # self.intermediate_steps.remove(self.intermediate_steps_index)
        function_calls = message["function_calls"]['arguments']['tools']
        func = function_calls[0]
        func_name = func["name"]
        func_args = func[func_name]
        self.intermediate_steps.append([AgentAction(
            func["name"], func_args, f"function call: {func['name']} with arguments: {func_args}")])
        self.intermediate_steps[-1].append(
            f"function call: {func['name']} with arguments: {func_args}")
        self.intermediate_steps[-1].append(self._format_function_map()[
                                           func["name"]](**func_args))
        self.intermediate_steps_index += 1
        # output.panel_print(f"Action: {func['name']}")
        # output.panel_print(f"Tool Input: {func_args}")
        self.intermediate_steps[-1].append('DONE, not give the same plan')
        # logging.info(f"Tool Input: {func['arguments']}")
        for func in function_calls[1:]:
            func_name = func["name"]
            func_args = func[func_name]
            self.intermediate_steps.append([AgentAction(
                func["name"], func_args, f"function call: {func['name']} with arguments: {func_args}")])
            self.intermediate_steps[-1].append("")
            self.intermediate_steps[-1].append("")
            self.intermediate_steps[-1].append("")
            # output.panel_print(f"Action: {func['name']}")
            # output.panel_print(f"Tool Input: {func_args}")
        return

    def get_prompt(self, template, data=None):
        from jinja2 import Environment, FileSystemLoader
        if data is None:
            data = {}
        # step_statuses = {'step_1': 'failed'}
        jinja_env = Environment()
        rendered = jinja_env.from_string(
            template).render(data)
        return rendered

    def _format_function_schema(self) -> List[Dict]:
        # List the function schema.
        function_schema = []
        for plugin in self.plugins:
            if isinstance(plugin, BaseTool):
                function_schema.append(plugin.schema)
            else:
                function_schema.append(plugin.schema)
        return function_schema

    def save_checkpoint(self, args):
        # dump self.intermediate_steps to path
        import json
        path = "checkpoint.json"
        with open(path, 'w') as f:
            if len(self.intermediate_steps) > 0:
                json.dump(self.intermediate_steps, f)
            else:
                json.dump(args, f)

    def pretty_print(self, json_object):
        json_str = json.dumps(json_object, indent=2)
        self.logger.debug(
            highlight(json_str, lexers.JsonLexer(), formatters.TerminalFormatter()))

    def send_msg(self, args):
        # Validate args
        args.dict()
        return openai.ChatCompletion.create(**args.dict())

    def run_monkey(self, instruction, max_iterations=10):
        # development_plan = [
        #     "Implement the `create_ship_placement` method to place a ship on the game board.",
        #     "Implement the `create_turn` method to allow players to take turns and target a grid cell.",
        #     "Implement the `get_game_status` method to check if the game is over and return the game status.",
        #     "Implement the `get_winner` method to return the winner of the game.",
        #     "Implement the `get_game` method to retrieve the state of the game.",
        #     "Implement the `delete_game` method to delete a game given its ID.",
        #     "Implement the `create_game` method to create a new game.",
        # ]
        development_plan = '''- Create a file called tic_tac_toe.py.
        - Implement the game logic to handle player moves and determine the outcome.
        - Prompt the players for their moves in the format "x,y".
        - Print the appropriate outcome when the game ends: "Player 1 won!", "Player 2 won!", or "Draw".
        - Handle incorrect locations by ignoring the input and prompting for a new location.
        - Handle already filled squares by ignoring the input and prompting for a new location.
        - Ensure the tic_tac_toe.py file is executable through the command `python tic_tac_toe.py`.'''
        # development_plan = open(os.path.join(os.path.dirname(
        #     __file__), "./prompts/execute_commands.prompt"), "r").read()

        # development_plan = '\n'.join(development_plan)
        development_plan = development_plan.split('\n')
        self.plugins[1].run(project_name="tic-tac-toe",
                            development_plan=development_plan[0])
        for i in range(1, len(development_plan)):
            self.plugins[1].implement_code_changes(development_plan[i])

    def format_function_call(self):
        FUNC_CALL_LIST = {
            "definitions": [
            ],
            "function_calls": self._format_function_map()
        }
        for plugin in self.plugins:
            if isinstance(plugin, Union[BaseTool, BaseAgent]):
                FUNC_CALL_LIST["definitions"].append(
                    format_plugin_schema(plugin))
            else:
                raise Exception("Not support agent yet")
        FUNC_MULTI_TURN_CALL_LIST = {
            "definitions": [
            ],
            "function_calls": {
                'ActionItems': lambda items: items
            }
        }
        for plugin in self.plugins:
            if isinstance(plugin, Union[BaseTool, BaseAgent]):
                FUNC_MULTI_TURN_CALL_LIST["definitions"].append(
                    self._format_multi_plugins_schema(self.plugins))
            else:
                raise Exception("Not support agent yet")
        return FUNC_MULTI_TURN_CALL_LIST

    def run(self, instruction, max_iterations=10):
        """
        Run the agent with the given instruction.

        :param instruction: Instruction to run the agent with.
        :type instruction: str
        :param max_iterations: Maximum number of iterations of reasoning steps, defaults to 10.
        :type max_iterations: int, optional
        :return: AgentOutput object.
        :rtype: AgentOutput
        """
        self.clear()
        logging.info(
            f"Running {self.name + ':' + self.version} with instruction: {instruction}")

        from pilot.util import save_prompt_to_file

        for _ in range(max_iterations):
            # for _ in range(1):
            prompt = self._compose_prompt(instruction)
            workfolder = os.path.dirname(
                os.path.abspath(__file__))
            prompt_path = os.path.join(
                workfolder, "prompts/execute_commands.prompt")
            save_prompt_to_file(prompt_path=prompt_path, prompt_content=prompt)
            ret = None
            try:
                with open("checkpoint.json", 'r') as f:
                    ret = json.load(f)
            except Exception:
                ret = None
            ignore_checkpoints = True
            if ret == None or len(ret) == 0 or ignore_checkpoints:
                openai.api_type = "azure"
                openai.api_base = os.getenv("AZURE_OPENAI_ENDPOINT")
                openai.api_version = "2023-07-01-preview"
                openai.api_key = os.getenv("AZURE_API_KEY")
                deployment_name = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME")
                response = None
                tool_description = self._compose_plugin_description()
                function_list = self.format_function_call()
                try:
                    args = {
                        'engine': deployment_name,
                        'temperature': 0.1,
                        # 'response_model': [ActionItem,FinalAnswerEntity],
                        # 'functions': function_list["definitions"],
                        # 'function_call': {'name': function_list["definitions"][0]["name"]},
                        'messages': [
                            {"role": "system", "content": ""},
                            {"role": "assistant",
                                "content": ""
                             },
                            # {"role": "system", "content": f"{instruction}"},
                            # {"role": "assistant", "content": f""},
                            {"role": "user", "content": prompt},
                            # {"role": "user", "content": "explain the your plan and answer the question if has any and continue the talks imitatation, if no more questions just reponse 'No more question' and coding worker summarize an action list using yaml description."}
                            # {"role": "user", "content":"any questions?"},
                        ],
                        # 'stop': ['\nDeveloper:', '\n\tDeveloper:']
                        'stop': ['No more questions', 'no more questions', 'Final Answer']
                    }
                    ChatCompletionArgs(**args)
                    response = openai.ChatCompletion.create(
                        **args)
                except Exception as e:
                    if e.__class__.__name__ == "ValidationError":
                        str_items = e.errors()[0]['loc']
                        error = f"field '{e.errors()[0]['loc'][-1]}' from {'.'.join(str_items[:-1])}"
                        print(f" {e.errors()[0]['type']}: {error}")
                    raise e
                ret = self.postProcess(response)
                if isinstance(ret, dict) and "text" in ret:
                    self.logger.debug(ret['text'])
                    self.raw_message.append(ret['text'])
                elif isinstance(ret, dict) and "stop" in ret:
                    self.logger.debug(ret)
                    response = self.get_final_answer(
                        content=self._construct_raw_message(self.raw_message))
                    self.logger.debug(response)
                    self.postProcess(response)

                continue

        return None

    def postProcess2(self, response):
        action = response.action
        if isinstance(action, FinalAnswerEntity):
            self.logger.info(action.model_dump_json())
            # break
        # tool_name = action.tool.value
        # tool_explanation = action.explanation
        self.intermediate_steps.append(action)
        # if isinstance(tool_input, BaseModel):
        #     tool_input = tool_input.model_dump()
        #     result = self._format_function_map()[tool_name](**tool_input)
        # if isinstance(tool_input, dict):
        #     result = self._format_function_map()[tool_name](**tool_input)
        # else:
        #     result = self._format_function_map()[tool_name](tool_input)
        # if isinstance(result, AgentOutput):
        #     total_cost += result.cost
        #     total_token += result.token_usage
        # if isinstance(result, str):
        #     self.intermediate_steps.append(
        #         (AgentAction(tool_name, tool_input, tool_explanation), ""))
        # else:
        #     self.intermediate_steps.append(
        #         (AgentAction(tool_name, tool_input, tool_explanation), ""))

    def postProcess(self, response):
        while response["choices"][0]["finish_reason"] == 'function_call' or \
                (response["choices"][0]["finish_reason"] == 'stop' and "function_call" in response["choices"][0]["message"]):
            response_message = response["choices"][0]["message"]
            function_name = response_message["function_call"]["name"]
            return {"function_calls": {
                "name": function_name,
                "arguments": json.loads(response_message["function_call"]["arguments"])
            }}
        if response["choices"][0]["finish_reason"] == 'stop' and "content" not in response["choices"][0]["message"]:
            return {"stop": response["choices"][0]["finish_reason"]}
        return {
            'text': response["choices"][0]["message"]["content"]
        }

        # content = self._construct_raw_message(self.raw_message)

    def get_final_answer(self, content):
        # with open(os.path.join(os.path.dirname(__file__), "prompts/execute_commands_cp2.prompt"), "r") as f:
        #     self.raw_message = f.readlines()
        # instructor.patch()
        # content = self._construct_raw_message(self.raw_message)
        self.logger.debug(content)
        args = {
            'engine': deployment_name,
            'temperature': 0.9,
        }
        # args['response_model'] = FinalAnswerEntity
        args["function_call"] = {
            "name": "process_tools"
        }
        args["functions"] = self.format_function_call()["definitions"]
        args['messages'] = [{
            "role": "system",
            "content": ""
        },
            {
            "role": "user",
            "content": f"extract action item from {content}"
        }
        ]
        return openai.ChatCompletion.create(**args)
        # instructor.unpatch()
        # # with open("response.json", 'w') as f:
        # #     json.dump(response.model_dump_json(), f)
        # for ac in response.ActionList:
        #     result = self._format_function_map()[ac.tool.value](
        #         **ac.tool_input.model_dump())
        #     self.logger.debug(result)

    def stream(self, instruction: Optional[str] = None, output: Optional[BaseOutput] = None, max_iterations: int = 10):
        pass

    def clear(self):
        """
        Clear and reset the agent.
        """
        self.intermediate_steps.clear()
