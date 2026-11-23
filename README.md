<!-- mcp-name: io.github.eredden/pdq-deploy-mcp -->

# PDQ Deploy MCP Server

An MCP (Model Context Protocol) server providing **read-only** access to PDQ Deploy via a SQLite database clone. Created by [Evan Redden](https://linkedin.com/in/eredden).

## Requirements

- Python 3.10+ and `mcp` module (v2.0.0+)
- PDQ Deploy SQLite database access
- MCP-compatible client (GitHub Copilot in VS Code, Claude Desktop, Cursor)

## Installation

Install via PyPI:
```bash
pip install pdq-deploy-mcp
```

*Note: You can also run it using  `uvx pdq-deploy-mcp` if using `uv`.*

If you want to modify this project, then install it locally from source:
```bash
git clone "https://github.com/eredden/PDQ-Deploy-MCP"
cd "PDQ-Deploy-MCP"
pip install -e .
```

## Setup

You must create a clone of your PDQ Deploy SQLite database to read from. Do not use  `Copy-Item` or `robocopy` to copy the database, as copying mid-write will corrupt your clone. Use the native [BackupDatabase command](https://docs.pdq.com/current-version/Deploy/index.html?cli-deploy-backupdatabase.htm) provided with PDQ Deploy to avoid corruption:


```bash
PDQDeploy BackupDatabase -Path "C:/Backups/PDQ/" -Force
```
*Note: Never point this server at a live PDQ Deploy database, as it will create `SHARED` locks preventing database writes.*

## Usage

### MCP Clients

Add this to your client's configuration file and change the path that `--db-path` points to:

```json
{
  "mcpServers": {
    "pdq-deploy-mcp": {
      "command": "pdq-deploy-mcp",
      "args": [
        "--db-path", 
        "C:/path/to/your/Database.db"
      ]
    }
  }
}
```

*Note: use `"command": "uvx"` and prepend `"pdq-deploy-mcp"` to `args` if running via `uvx`.*

### Manual CLI Execution
```bash
pdq-deploy-mcp --db-path "C:/path/to/your/Database.db"
```