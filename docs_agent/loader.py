"""
Configuration and resource loader for the Docs Agent.

Supports loading:
- Instructions from markdown files
- MCP server configurations from YAML
- Both stdio and HTTP MCP transports
"""

import logging
import os
from datetime import datetime, timedelta
from pathlib import Path

import yaml
from google.adk.tools.mcp_tool import MCPToolset, StdioConnectionParams
from google.adk.tools.mcp_tool.mcp_session_manager import StreamableHTTPConnectionParams
from mcp.client.stdio import StdioServerParameters

from docs_agent.utils import resolve_file_path

logger = logging.getLogger(__name__)

# Default paths relative to this file
BASE_DIR = os.path.dirname(__file__)
DEFAULT_INSTRUCTION_PATH = os.path.join(BASE_DIR, "instructions", "docs_agent.md")
DEFAULT_MCP_CONFIG_PATH = os.path.join(BASE_DIR, "config", "mcp_config.yaml")


def _get_date_context() -> str:
    """Generate current date context for the agent instructions."""
    today = datetime.now()

    # Calculate useful date references
    first_of_month = today.replace(day=1)
    last_month_end = first_of_month - timedelta(days=1)
    last_month_start = last_month_end.replace(day=1)
    two_months_ago = (first_of_month - timedelta(days=32)).replace(day=1)
    week_ago = today - timedelta(days=7)
    two_weeks_ago = today - timedelta(days=14)
    month_ago = today - timedelta(days=30)

    return f"""
## Current Date Context (AUTO-GENERATED)

**Today's Date: {today.strftime("%Y-%m-%d")} ({today.strftime("%B %d, %Y")})**

Use these pre-calculated dates for time-based queries:
- **This month**: after={first_of_month.strftime("%Y-%m-%d")}
- **Last month**: after={last_month_start.strftime("%Y-%m-%d")}, before={last_month_end.strftime("%Y-%m-%d")}
- **Past 2 months**: after={two_months_ago.strftime("%Y-%m-%d")}
- **This week** (last 7 days): after={week_ago.strftime("%Y-%m-%d")}
- **Last week**: after={two_weeks_ago.strftime("%Y-%m-%d")}, before={week_ago.strftime("%Y-%m-%d")}
- **Last 30 days**: after={month_ago.strftime("%Y-%m-%d")}

**IMPORTANT**: Use these exact dates. Do NOT ask the user for date clarification.
"""


def load_instruction(instruction_path: str | None = None) -> str:
    """
    Load agent instructions from a markdown file.
    Automatically injects current date context.

    Args:
        instruction_path: Path to instruction file. Uses default if None.

    Returns:
        Instruction text as string with date context prepended
    """
    # Use resolve_file_path from utils
    env_name = "INSTRUCTION_PATH"
    if instruction_path:
        os.environ[env_name] = instruction_path

    try:
        path = resolve_file_path(env_name, DEFAULT_INSTRUCTION_PATH)
        with open(path, encoding="utf-8") as f:
            instruction = f.read()
        logger.info(f"Loaded instructions from {path}")

        # Inject current date context at the beginning
        date_context = _get_date_context()
        instruction = date_context + "\n" + instruction

        return instruction
    except FileNotFoundError as e:
        logger.warning(f"Instruction file not found: {e}, using default")
        return "You are a helpful documentation assistant."


def load_mcp_toolsets(config_path: str | None = None) -> list[MCPToolset]:
    """
    Load MCP toolsets from YAML configuration.

    Supports both stdio (local) and HTTP (remote) MCP servers.

    Args:
        config_path: Path to MCP config YAML. Uses default if None.

    Returns:
        List of configured MCPToolset instances
    """
    # Use resolve_file_path from utils
    env_name = "MCP_CONFIG_PATH"
    if config_path:
        os.environ[env_name] = config_path

    try:
        path = resolve_file_path(env_name, DEFAULT_MCP_CONFIG_PATH)
    except FileNotFoundError as e:
        logger.warning(f"MCP config not found: {e}")
        return []

    with open(path, encoding="utf-8") as f:
        config = yaml.safe_load(f) or {}

    toolsets = []
    servers = config.get("mcp_servers", [])

    if not servers:
        logger.warning(f"MCP config {path} contains no 'mcp_servers'")

    for server in servers:
        if not server.get("enabled", True):
            logger.info(f"Skipping disabled MCP server: {server.get('name')}")
            continue

        name = server.get("name", "unnamed")
        mode = server.get("mode", "stdio")
        timeout = server.get("timeout", 30.0)

        try:
            if mode == "stdio":
                toolset = _create_stdio_toolset(server, Path(path).parent, timeout)
            elif mode in ("http", "stream"):
                toolset = _create_http_toolset(server, timeout)
            else:
                logger.warning(f"Unknown MCP mode '{mode}' for server '{name}'")
                continue

            if toolset:
                toolsets.append(toolset)
                logger.info(f"Loaded MCP toolset: {name} (mode={mode})")

        except Exception as e:
            logger.error(f"Failed to create MCP toolset '{name}': {e}")

    logger.info(f"Loaded {len(toolsets)} MCP toolsets")
    return toolsets


def _expand_env_vars(value: str) -> str:
    """Expand environment variables in a string."""
    if isinstance(value, str) and "${" in value:
        import re

        pattern = r"\$\{([^}:]+)(?::-([^}]*))?\}"

        def replace(match):
            var_name = match.group(1)
            default = match.group(2) or ""
            return os.environ.get(var_name, default)

        return re.sub(pattern, replace, value)
    return value


def _resolve_path(path_str: str, base_dir: Path) -> str:
    """Resolve a path relative to base directory."""
    path_str = _expand_env_vars(path_str)
    path = Path(path_str)

    if not path.is_absolute():
        path = base_dir / path

    return str(path.resolve())


def _create_stdio_toolset(server: dict, base_dir: Path, timeout: float) -> MCPToolset:
    """Create a stdio-based MCP toolset."""
    command = server.get("command", "node")
    args = server.get("args", [])
    env_config = server.get("env", {})

    # For npx/npm commands, args are package names, not paths - don't resolve them
    if command in ("npx", "npm", "pnpm", "yarn"):
        resolved_args = [_expand_env_vars(str(arg)) for arg in args]
        cwd = str(base_dir)
    else:
        # Resolve paths in args for other commands (like node)
        resolved_args = [_resolve_path(arg, base_dir) for arg in args]
        # Get working directory from first arg (the script path)
        cwd = str(Path(resolved_args[0]).parent) if resolved_args else str(base_dir)

    # Merge environment variables
    env = {**os.environ}
    for key, value in env_config.items():
        env[key] = _expand_env_vars(str(value))

    connection_params = StdioConnectionParams(
        server_params=StdioServerParameters(
            command=command,
            args=resolved_args,
            env=env,
            cwd=cwd,
        ),
        timeout=timeout,
    )

    return MCPToolset(connection_params=connection_params)


def _create_http_toolset(server: dict, timeout: float) -> MCPToolset:
    """Create an HTTP/Stream-based MCP toolset."""
    url = server.get("url")

    if not url:
        raise ValueError("HTTP MCP server requires 'url' configuration")

    url = _expand_env_vars(url)

    connection_params = StreamableHTTPConnectionParams(url=url, timeout=timeout)

    return MCPToolset(connection_params=connection_params)
