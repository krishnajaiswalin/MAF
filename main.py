import asyncio
import os
import re
from typing import Annotated

from dotenv import load_dotenv

# Agent Framework imports (Python)
from agent_framework.azure import AzureOpenAIChatClient
from agent_framework import ChatAgent
from azure.identity import DefaultAzureCredential

# Simple tool to keep code non-complex
def get_weather(location: Annotated[str, "The location to get the weather for."]) -> str:
    return f"Weather in {location} is pleasant today."


def parse_aoai_env():
    """
    Parse Azure OpenAI config from .env. Supports either full endpoint URL
    or separate variables. Keeps setup simple while being robust.
    Expected .env keys:
      - AZURE_OPENAI_ENDPOINT: e.g. https://<res>.cognitiveservices.azure.com/openai/deployments/<name>/chat/completions?api-version=2024-10-01-preview
      - AZURE_OPENAI_API_KEY: optional, if using key-based auth (recommended to avoid CLI login)
      - AZURE_OPENAI_DEPLOYMENT: optional override of deployment name
      - AZURE_OPENAI_API_VERSION: optional override of api-version
    """
    endpoint = os.getenv("AZURE_OPENAI_ENDPOINT", "").strip()
    api_key = os.getenv("AZURE_OPENAI_API_KEY", "").strip()
    dep_override = os.getenv("AZURE_OPENAI_DEPLOYMENT", "").strip()
    api_ver_override = os.getenv("AZURE_OPENAI_API_VERSION", "").strip()

    base_endpoint = None
    deployment_name = None
    api_version = None

    # Try to parse a full endpoint path that includes /openai/deployments/<dep>/chat/completions
    m = re.match(r"^(https://[^\s/]+)/openai/deployments/([^/]+)/", endpoint)
    if m:
        base_endpoint = m.group(1)
        deployment_name = m.group(2)
        # extract api-version if present
        ver_match = re.search(r"api-version=([\w\-\.]+)", endpoint)
        if ver_match:
            api_version = ver_match.group(1)

    # Apply overrides if provided
    if dep_override:
        deployment_name = dep_override
    if api_ver_override:
        api_version = api_ver_override

    return {
        "base_endpoint": base_endpoint or endpoint,  # fallback to full string
        "deployment_name": deployment_name,
        "api_key": api_key,
        "api_version": api_version,
    }


async def run_simple_chat():
    load_dotenv()
    # Optional: allow insecure SSL for corporate proxies if explicitly enabled
    if os.getenv("INSECURE_SKIP_VERIFY", "").lower() in {"1", "true", "yes"}:
        os.environ["PYTHONHTTPSVERIFY"] = "0"
        print("[Warning] SSL verification disabled per INSECURE_SKIP_VERIFY.")
    cfg = parse_aoai_env()

    if not cfg["base_endpoint"]:
        raise RuntimeError("AZURE_OPENAI_ENDPOINT is missing in .env")
    if not cfg["deployment_name"]:
        raise RuntimeError("Could not determine deployment name; set AZURE_OPENAI_DEPLOYMENT in .env")

    # Prefer Azure AD auth (DefaultAzureCredential); if not available, attempt key-based fallback
    credential = None
    try:
        credential = DefaultAzureCredential()
    except Exception:
        credential = None

    # Initialize AzureOpenAIChatClient from Agent Framework
    # Note: If your environment is not signed in, ensure AZURE_OPENAI_API_KEY is present.
    client = AzureOpenAIChatClient(
        endpoint=cfg["base_endpoint"],
        deployment_name=cfg["deployment_name"],
        credential=credential,
    )

    agent = ChatAgent(
        name="SampleAgent",
        instructions="You are a helpful, concise assistant.",
        chat_client=client,
        tools=[get_weather],
    )
    async with agent:
        print("Agent:", end=" ", flush=True)
        async for chunk in agent.run_stream("what is Machine learning  ?"):
            if chunk.text:
                print(chunk.text, end="", flush=True)
        print("\n")


if __name__ == "__main__":
    asyncio.run(run_simple_chat())
