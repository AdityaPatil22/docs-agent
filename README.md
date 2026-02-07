# Docs Agent

An AI-powered documentation assistant built with [Google ADK](https://github.com/google/adk-python) (Agent Development Kit). This agent helps users find and display Red Hat documentation using MCP (Model Context Protocol) toolsets.

## Features

- **Multi-Model Support**: Works with Google Gemini models or any LLM via LiteLLM
- **MCP Integration**: Connects to MCP servers for documentation search and UI component generation
- **Flexible Configuration**: YAML-based MCP server configuration with support for both stdio and HTTP transports
- **Automatic Date Context**: Injects current date context into agent instructions for time-based queries
- **Environment Variable Expansion**: Supports `${VAR:-default}` syntax in configuration files

## Project Structure

```
docs-agent/
├── docs_agent/
│   ├── agent.py           # Main agent configuration
│   ├── loader.py          # Configuration and resource loaders
│   ├── utils.py           # Utility functions
│   ├── config/
│   │   └── mcp_config.yaml    # MCP server configuration
│   └── instructions/
│       └── docs_agent.md      # Agent system instructions
├── requirements.txt
└── README.md
```

## Installation

1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd docs-agent
   ```

2. Create a virtual environment and install dependencies:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

## Configuration

### Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `GOOGLE_API_KEY` | Google API key for Gemini models | Yes (if using Gemini) |
| `MODEL_API` | LiteLLM API base URL | No |
| `MODEL_ID` | LiteLLM model identifier | Yes (if not using Gemini) |
| `MODEL_TOKEN` | Authorization token for LiteLLM | No |
| `INSTRUCTION_PATH` | Path to custom instruction file | No (uses default) |
| `MCP_CONFIG_PATH` | Path to custom MCP config | No (uses default) |

### Model Selection

The agent automatically selects the model based on environment variables:

- If `GOOGLE_API_KEY` is set → Uses `gemini-2.0-flash`
- Otherwise → Uses LiteLLM with the specified `MODEL_ID`

### MCP Server Configuration

Configure MCP servers in `docs_agent/config/mcp_config.yaml`:

```yaml
mcp_servers:
  # HTTP/Stream-based MCP server
  - name: docs-mcp
    mode: stream
    enabled: true
    url: "https://your-mcp-server.example.com/mcp"
    timeout: 60.0
    verify_ssl: true  # Set to false for self-signed certs

  # Stdio-based MCP server (local)
  - name: local-mcp
    mode: stdio
    enabled: true
    command: npx
    args:
      - "@your-org/mcp-package"
    timeout: 60.0
    env:
      CUSTOM_VAR: "${MY_ENV_VAR:-default_value}"
```

#### MCP Server Options

| Option | Description | Default |
|--------|-------------|---------|
| `name` | Server identifier | Required |
| `mode` | Transport mode: `stdio`, `http`, or `stream` | `stdio` |
| `enabled` | Enable/disable the server | `true` |
| `timeout` | Connection timeout in seconds | `30.0` |
| `url` | Server URL (for http/stream mode) | Required for http/stream |
| `command` | Command to run (for stdio mode) | `node` |
| `args` | Command arguments (for stdio mode) | `[]` |
| `env` | Environment variables (for stdio mode) | `{}` |
| `verify_ssl` | Verify SSL certificates (for http/stream) | `true` |

## Usage

### Running with Google ADK

```bash
# Set your API key
export GOOGLE_API_KEY="your-api-key"

# Run with ADK CLI
adk run docs_agent
```

### Running with LiteLLM

```bash
# Configure LiteLLM
export MODEL_ID="gpt-4"
export MODEL_API="https://api.openai.com/v1"
export MODEL_TOKEN="your-api-key"

# Run with ADK CLI
adk run docs_agent
```

### Custom Configuration

```bash
# Use custom instruction and config files
export INSTRUCTION_PATH="/path/to/custom/instructions.md"
export MCP_CONFIG_PATH="/path/to/custom/mcp_config.yaml"

adk run docs_agent
```

## Customizing Agent Instructions

Edit `docs_agent/instructions/docs_agent.md` to customize the agent's behavior. The loader automatically prepends current date context to help with time-based queries.

## Development

### Adding New MCP Servers

1. Add the server configuration to `mcp_config.yaml`
2. Restart the agent to load the new toolset

### Debugging

The agent uses Python's logging module. Enable debug logging by setting:

```python
logging.basicConfig(level=logging.DEBUG)
```

### Troubleshooting: `CancelledError` when running in CLI

If `adk run docs_agent` crashes with `asyncio.exceptions.CancelledError: Cancelled by cancel scope` right after you send a message (e.g. "hey"), the failure is usually during **MCP session initialization**: one of the MCP servers is not responding in time, and the framework cancels the wait.

**Isolate which server is failing:**

1. In `docs_agent/config/mcp_config.yaml`, set `enabled: false` for one MCP server and run again. If the agent works, the disabled server is the one causing the cancel.
2. **docs-mcp (stream)**: Ensure the URL is reachable (e.g. from your network/VPN). Slow or unreachable servers can trigger timeouts and cancellation.
3. **rhds-mcp (stdio)**: Ensure Node.js and `npx` are installed. The first run of `npx @scarlet-mesh/mcp-rhds` can be slow while the package is installed. Test manually:
   ```bash
   npx @scarlet-mesh/mcp-rhds
   ```
   If it doesn’t start or respond, fix the stdio server or disable it in config until it’s reliable.

**Quick test without MCP:** Temporarily set `enabled: false` for all entries under `mcp_servers` to confirm the agent runs without any MCP tools.

## Dependencies

- **google-adk**: Google Agent Development Kit
- **mcp**: Model Context Protocol client
- **pyyaml**: YAML configuration parsing
- **litellm**: Multi-provider LLM support (optional)

## License

See [LICENSE](LICENSE) for details.
