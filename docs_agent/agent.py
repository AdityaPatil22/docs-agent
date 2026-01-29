"""
Docs Agent - An agent to answer documentation related questions.

Supports:
- Google Gemini models (when GOOGLE_API_KEY is set)
- LiteLLM models (when MODEL_API and MODEL_ID are set)
- MCP toolsets for documentation search
"""

import logging
import os
import traceback

from google.adk.agents import Agent, LlmAgent

from docs_agent.loader import load_instruction, load_mcp_toolsets

# Enable debug logging for troubleshooting
logging.basicConfig(level=logging.DEBUG)
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
try:
    system_instruction = load_instruction(INSTRUCTION_PATH)
    logger.debug(f"Loaded instruction with {len(system_instruction)} characters")
except Exception as e:
    logger.error(f"Failed to load instructions: {e}")
    traceback.print_exc()
    system_instruction = "You are a helpful documentation assistant."

try:
    mcp_toolsets = load_mcp_toolsets(MCP_CONFIG_PATH)
    logger.debug(f"Loaded {len(mcp_toolsets)} MCP toolsets")
except Exception as e:
    logger.error(f"Failed to load MCP toolsets: {e}")
    traceback.print_exc()
    mcp_toolsets = []

# -----------------------
# Model selection
# -----------------------
if GOOGLE_API_KEY:
    logger.info("Using Gemini model")
    model = "gemini-2.0-flash"
else:
    logger.info("Using LiteLLM model")

    if not MODEL_ID:
        raise RuntimeError(
            "GOOGLE_API_KEY is not set, and MODEL_ID is missing"
        )

    from google.adk.models.lite_llm import LiteLlm

    # Build kwargs for LiteLlm - only include api_base if set
    litellm_kwargs = {"model": MODEL_ID}
    if MODEL_API:
        litellm_kwargs["api_base"] = MODEL_API
    if MODEL_TOKEN:
        litellm_kwargs["extra_headers"] = {"Authorization": f"Bearer {MODEL_TOKEN}"}

    model = LiteLlm(**litellm_kwargs)

# -----------------------
# Create the agent
# -----------------------
try:
    logger.debug(f"Creating agent with model: {model}")
    logger.debug(f"Number of tools: {len(mcp_toolsets)}")
    root_agent = Agent(
        name="docs_agent",
        model=model,
        description="Agent to answer documentation related questions.",
        instruction=system_instruction,
        tools=mcp_toolsets,
    )
    logger.info("Agent created successfully")
except Exception as e:
    logger.error(f"Failed to create agent: {e}")
    traceback.print_exc()
    raise
