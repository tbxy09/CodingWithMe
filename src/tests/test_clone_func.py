import asyncio
from importlib.abc import InspectLoader
from metagpt.actions.clone_class import CloneFunction
import ast
from pydantic import BaseModel
from pilot.utils import PromptTemplate
import uvicorn

from sdk.api_db import AgentDB

# Original function 
source_code = """
def original_function(x, y):
    return x + y
"""
# Function template
template_code = "def new_function(a, b):\\n    # New implementation here\\n"

SMOL_DEV_SYSTEM_PROMPT = """
You are a top tier AI developer who is trying to write a program that will generate code for the user based on their intent.
Do not leave any todos, fully implement every feature requested.

When writing code, add comments to explain what you intend to do and why it aligns with the program plan and specific instructions from the original prompt.
"""

ZeroShotReactPrompt = PromptTemplate(input_variables=['instruction', 'agent_scratchpad', 'tool_names', 'tool_description'], template='Answer the following questions as best you can. You have access to the following tools:\n{tool_description}.\nUse the following format:\nQuestion: the input question you must answer\nThought: you should always think about what to do\nAction: the action to take, should be one of [{tool_names}]\nAction Input: the input to the action\nObservation: the result of the action\n... (this Thought/Action/Action Input/Observation can repeat N times)\nThought: I now know the final answer\nFinal Answer: the final answer to the original input question\nBegin!\nQuestion: {instruction}\nThought:{agent_scratchpad}\n    ', validate_template=True, skip_on_failure=True)


class MyLoader(InspectLoader):
    def get_source(self, fullname):
        # provide an implementation for this method
        pass
class MyTransformer(ast.NodeTransformer):
    def visit_FunctionDef(self, node):
        return node  # Return modified node

def get_source_code(arg:object):
    import inspect
    # Get the module object from the module name
    members = inspect.getmembers(arg, predicate=inspect.isfunction)
    member_functions = [member[0] for member in members]
    # print(member_functions)
    parsed_code = ast.parse(inspect.getsource(arg))
    # print(ast.dump(parsed_code, annotate_fields=True, indent=2))

    return inspect.getsource(arg),parsed_code

import logging
logger = logging.getLogger(__name__)
logger.addHandler(logging.StreamHandler())
def pretty_print(source_code,template_func):
    from metagpt.actions.clone_function import  highlight
    logger.info(f"Template function: {highlight(source_code,'python')}")
    logger.info(f"Template function: {highlight(template_func,'python')}")

class Test_CloneFunction(BaseModel):
    """Test the CloneFunction class."""
    src_module: object
    template_module: object
    source_code: str = ""
    template_code: str = ""
    def module2code(self):
        import astor
        self.source_code = get_source_code(self.src_module)[0]
        self.template_code = get_source_code(self.template_module)[1]
        transformer = MyTransformer()
        template_ast = transformer.visit(self.template_code)
        # print(ast.dump(new_ast, annotate_fields=True, indent=2))
        self.template_code = astor.to_source(template_ast)
        pretty_print(self.source_code,self.template_code)
    async def clone_function(self):
        import os
        self.module2code()
        cf = CloneFunction()
        new_function_code = await cf.run(template_func=self.template_code, source_code=self.source_code)
        os.system("touch new_function.py")
        os.system(f"echo '{new_function_code}' > new_function.py")

import pytest
@pytest.mark.asyncio
@pytest.mark.skip(reason="ignore the test")
async def test_clone_function():
    from smol_dev import api
    from pilot import ReactChatAgent
    test_clone_function = Test_CloneFunction(src_module=CloneFunction,template_module=api)
    # asyncio.run(test_clone_function.clone_function())
    await test_clone_function.clone_function()


@pytest.mark.asyncio
async def test_react():
    from pilot import ReactChatAgent
    from pilot.utils import RunShell
    from sdk.api_agent import ServerAgent
    from sdk.api_app import create_app
    import os
    

    pilot_agent = ReactChatAgent(
        version="0.0.1",
        # description="elon is an experienced and visionary entrepreneur. He is able to create a startup from scratch and get a strong team to support his ideas",
        description="user is a developer. He is able to create an app from scratch and improve the app with a bunch of tools and agents",
        plugins=[
            RunShell(),
            # ReadFile()
        ],
        target_tasks=[
            "create a new project and update the project",
            "arrange a bunch of tools and agents to do coding"],
        prompt_template=ZeroShotReactPrompt,
    )
    # pilot_agent.run()
    # add llm handler to server agent
    # db = AgentDB(
    #     user="admin",
    #     password="admin",
    #     host="localhost",
    # )
    database_name = os.getenv("DATABASE_STRING")
    logging.info(f"Database string: {database_name}")
    # workspace = LocalWorkspace(os.getenv("AGENT_WORKSPACE"))
    db = AgentDB(database_name, debug_enabled=False)
    # api agent to follow agent protocal
    agent = ServerAgent(db)
    
    # build api server
    agent.setup_agent(pilot_agent.api_task, pilot_agent.api_step, pilot_agent.artifact_handler)
    app = create_app()
    def option_task(data:object):
        print(f"option_task: {data}")
        return
    def healthz():
        return "ok"
    app.add_api_route("/ap/v1/agent/tasks", option_task, methods=["OPTIONS"])
    app.add_api_route("/ap/v1/agent/tasks", agent.create_task, methods=["POST"])
    # GET /agent/tasks/{task_id}/artifacts - For the benchmark to download artifacts
    app.add_api_route("/ap/v1/agent/tasks/{task_id}/artifacts", agent.list_artifacts, methods=["GET"])
    app.add_api_route("/ap/v1/agent/tasks/{task_id}/steps", agent.execute_step, methods=["POST"])
    # GET /agent/healthz - Liveness probe for health checks
    app.add_api_route("/ap/v1/agent/healthz", healthz, methods=["GET"])

    # run api server
    uvicorn.run(app, host="localhost", port=8300)


    # agent("What is the weather like today?")
    # pilot_agent.run(" check in current path if any project markdown files include 'prompt' in the content, and extract the line which include 'prompt' in the file")
    # agent.run("find file in current path which is python file and pick the latest modified one, and read its content and split it into parts by function or class")        
test_react()