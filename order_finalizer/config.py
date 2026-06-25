import os
from dotenv import load_dotenv

load_dotenv()

AZURE_OPENAI_API_KEY = os.getenv("AZURE_OPENAI_API_KEY")
_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT", "")
if _endpoint.endswith("/openai/v1"):
    _endpoint = _endpoint[:-10]
AZURE_OPENAI_ENDPOINT = _endpoint.rstrip("/")
AZURE_OPENAI_DEPLOYMENT_NAME = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME")
AZURE_OPENAI_API_VERSION = os.getenv("AZURE_OPENAI_API_VERSION")
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")
