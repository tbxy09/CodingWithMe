from pilot import ReactChatAgent
from pilot.utils import RunShell
from pilot.prompts.prompts import ZeroShotReactPrompt
import uvicorn
from sdk.api_agent import ServerAgent
from sdk.api_app import create_app
from sdk.api_db import AgentDB
import os
import dotenv
import logging

logger = logging.getLogger()
logger.addHandler(logging.StreamHandler())
logger.setLevel(logging.DEBUG)

#load env
dotenv.load_dotenv()
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
# uvicorn.run(app, host="localhost", port=8300)


# agent("What is the weather like today?")
# pilot_agent.run(" check in current path if any project markdown files include 'prompt' in the content, and extract the line which include 'prompt' in the file")
# agent.run("find file in current path which is python file and pick the latest modified one, and read its content and split it into parts by function or class")       