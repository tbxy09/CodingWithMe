from sdk.CodeImp import CodeMonkeyRefactored
from pilot.utils import RunShell
from pilot.helpers.Project import Project
from pilot.helpers.prompts import ZeroShotReactPrompt
from sdk.api_agent import ServerAgent
from sdk.ReactChatAgent import ReactChatAgent
from sdk.api_app import create_app
from sdk.api_db import AgentDB
import os
import dotenv
from logger.debug import PathLogger
import logging


import debugpy
# wait for client to attach
debugpy.listen(('localhost', 7678))
debugpy.wait_for_client()

# load env
dotenv.load_dotenv()
project_dir = os.getenv("PROJECT_DIR")
project = Project(project_dir)
codeagent = CodeMonkeyRefactored()
pilot_agent = ReactChatAgent(
    logger=PathLogger(__name__),
    version="0.0.1",
    # description="elon is an experienced and visionary entrepreneur. He is able to create a startup from scratch and get a strong team to support his ideas",
    description="user is a developer. He is able to create an app from scratch and improve the app with a bunch of tools and agents",
    plugins=[
        RunShell(),
        codeagent
    ],
    target_tasks=[
        "create a new project and update the project",
        "arrange a bunch of tools and agents to do coding"],
    prompt_template=ZeroShotReactPrompt,
)
database_name = os.getenv("DATABASE_STRING")
logging.info(f"Database string: {database_name}")
# development_plan = [
#     "Implement the `create_ship_placement` method to place a ship on the game board.",
#     "Implement the `create_turn` method to allow players to take turns and target a grid cell.",
#     "Implement the `get_game_status` method to check if the game is over and return the game status.",
#     "Implement the `get_winner` method to return the winner of the game.",
#     "Implement the `get_game` method to retrieve the state of the game.",
#     "Implement the `delete_game` method to delete a game given its ID.",
#     "Implement the `create_game` method to create a new game.",
# ]
# development_plan = '\n'.join(development_plan)
# codeagent.run(project_name="battleship", development_plan=development_plan)
# quit()
# workspace = LocalWorkspace(os.getenv("AGENT_WORKSPACE"))
db = AgentDB(database_name, debug_enabled=False)
# api agent to follow agent protocal
agent = ServerAgent(db)

# build api server
agent.setup_agent(pilot_agent.api_task, pilot_agent.api_step,
                  pilot_agent.artifact_handler)
app = create_app()


def option_task(data: object):
    print(f"option_task: {data}")
    return


def healthz():
    return "ok"


app.add_api_route("/ap/v1/agent/tasks", option_task, methods=["OPTIONS"])
app.add_api_route("/ap/v1/agent/tasks", agent.create_task, methods=["POST"])
# GET /agent/tasks/{task_id}/artifacts - For the benchmark to download artifacts
app.add_api_route(
    "/ap/v1/agent/tasks/{task_id}/artifacts", agent.list_artifacts, methods=["GET"])
app.add_api_route(
    "/ap/v1/agent/tasks/{task_id}/steps", agent.execute_step, methods=["POST"])
# GET /agent/healthz - Liveness probe for health checks
app.add_api_route("/ap/v1/agent/healthz", healthz, methods=["GET"])
