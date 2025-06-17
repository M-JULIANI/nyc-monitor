import vertexai
from vertexai import agent_engines
from vertexai.preview.reasoning_engines import AdkApp
from rag.root_agent import root_agent_instance
import logging
import os
from dotenv import set_key, load_dotenv
from google.auth import default

# Load .env from the repo root
load_dotenv(os.path.abspath(os.path.join(
    os.path.dirname(__file__), "..", "..", ".env")))

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

GOOGLE_CLOUD_PROJECT = os.getenv("GOOGLE_CLOUD_PROJECT")
GOOGLE_CLOUD_LOCATION = os.getenv("GOOGLE_CLOUD_LOCATION")
STAGING_BUCKET = os.getenv("STAGING_BUCKET")
# Define the path to the .env file relative to this script
ENV_FILE_PATH = os.path.abspath(os.path.join(
    os.path.dirname(__file__), "..", "..", ".env"))

# Use default credentials which will work with both local and CI/CD environments
credentials, project_id = default()

vertexai.init(
    project=GOOGLE_CLOUD_PROJECT or project_id,
    location=GOOGLE_CLOUD_LOCATION,
    staging_bucket=STAGING_BUCKET,
    credentials=credentials,
)

# Function to update the .env file


def update_env_file(agent_engine_id, env_file_path):
    """Updates the .env file with the agent engine ID."""
    try:
        set_key(env_file_path, "AGENT_ENGINE_ID", agent_engine_id)
        print(
            f"Updated AGENT_ENGINE_ID in {env_file_path} to {agent_engine_id}")
    except Exception as e:
        print(f"Error updating .env file: {e}")


logger.info("Deploying Atlas Root Agent to Vertex AI ADK...")
app = AdkApp(
    agent=root_agent_instance.agent,  # Access the agent property from the instance
    enable_tracing=True,
)

logging.debug("Deploying agent to agent engine:")

remote_app = agent_engines.create(
    app,
    requirements=[
        "google-cloud-aiplatform[adk,agent-engines]==1.93.1",
        "google-adk",
        "python-dotenv",
        "google-auth",
        "tqdm",
        "requests",
        "deprecated",
        "pydantic",
        "cloudpickle",
        "fastapi",
        "uvicorn",
        "httpx",
        "aiohttp",
        "websockets",
        "protobuf",
        "grpcio",
        "googleapis-common-protos",
        "google-api-core",
        "google-auth-httplib2",
        "google-cloud-core",
        "typing_extensions",
        "annotated-types",
        "wrapt",
        "six",
        "certifi",
        "charset-normalizer",
        "idna",
        "urllib3",
        "toml",
        # Dependencies from pyproject.toml that are missing
        "llama-index>=0.12",
        "pydantic-settings>=2.8.1",
        "tabulate>=0.9.0",
        "slowapi>=0.1.8",
        "google-cloud-firestore>=2.18.0",
        "redditwarp>=0.3.0"
    ],
    extra_packages=[
        "./rag",
    ],
    display_name="Atlas Multi-Agent Investigation System"
)

# log remote_app
logging.info(
    f"Deployed Atlas Root Agent to Vertex AI successfully, resource name: {remote_app.resource_name}")

# Update the .env file with the new Agent Engine ID
update_env_file(remote_app.resource_name, ENV_FILE_PATH)
