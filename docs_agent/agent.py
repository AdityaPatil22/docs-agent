"""
Docs Agent - An agent to answer documentation related questions.

Supports:
- Google Gemini models (when GOOGLE_API_KEY is set)
- LiteLLM models (when MODEL_API and MODEL_ID are set)
- MCP toolsets for documentation search
"""

import logging
import os

from google.adk.agents import Agent, LlmAgent

from docs_agent.loader import load_instruction, load_mcp_toolsets

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# -----------------------
# Common configuration
# -----------------------
MODEL_API = os.environ.get("MODEL_API")
MODEL_ID = os.environ.get("MODEL_ID")
MODEL_TOKEN = os.environ.get("MODEL_TOKEN", "")

INSTRUCTION_PATH = os.environ.get("INSTRUCTION_PATH")
MCP_CONFIG_PATH = os.environ.get("MCP_CONFIG_PATH")

GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY")

# -----------------------
# Load resources
# -----------------------
system_instruction = load_instruction(INSTRUCTION_PATH)

# TODO: Re-enable MCP toolsets after fixing connection issues
# mcp_toolsets = load_mcp_toolsets(MCP_CONFIG_PATH)
mcp_toolsets = []  # Temporarily disabled for debugging

# -----------------------
# Model selection
# -----------------------
if GOOGLE_API_KEY:
    logger.info("Using Gemini model")
    model = "gemini-2.0-flash"
else:
    logger.info("Using LiteLLM model")

    if not MODEL_API or not MODEL_ID:
        raise RuntimeError(
            "GOOGLE_API_KEY is not set, but MODEL_API / MODEL_ID is missing"
        )

    from google.adk.models.lite_llm import LiteLlm

    model = LiteLlm(
        model=MODEL_ID,
        api_base=MODEL_API,
        extra_headers={"Authorization": f"Bearer {MODEL_TOKEN}"}
        if MODEL_TOKEN
        else None,
    )

# -----------------------
# Create the agent
# -----------------------
root_agent = Agent(
    name="docs_agent",
    model=model,
    description="Agent to answer documentation related questions.",
    instruction=system_instruction,
    tools=mcp_toolsets,
)
