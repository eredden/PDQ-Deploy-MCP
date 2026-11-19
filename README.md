# PDQ Deploy MCP Server

This project is an MCP (Model Context Protocol) server that provides **read-only** access to PDQ Deploy data through a local PDQ Deploy SQLite database. You can simply ask a question in plain English and have an AI agent query the PDQ Deploy database *for you!* This is good for open-ended, complex problems.

This project was created by [Evan Redden](https://www.linkedin.com/in/eredden).

## Requirements

- Python 3.10+ and version 2.0.0+ of the `mcp` module.
- Access to a PDQ Deploy SQLite database.
- An MCP-compatible client like GitHub Copilot in VS Code.

## Installation

Clone the repository locally:

```bash
git clone https://github.com/eredden/PDQ-Deploy-MCP

cd PDQ-Deploy-MCP
```

Install the required MCP server dependencies from `pyproject.toml`:

```bash
pip install -e .
```

## Setup

You will need a copy of the PDQ Deploy database `C:\ProgramData\Admin Arsenal\PDQ Deploy\Database.db` from the desired PDQ server. This will be supplied to the MCP server using the `--db-path` argument, so place it in a location where it is accessible to the MCP server. If you are using the `.mcp.json` config provided for GitHub Copilot in this repository, then you will want to place the .db file in `.\db\Database.db`.

You are responsible for keeping your database copy up-to-date. **Avoid pointing this MCP server at a live PDQ Deploy database,** as doing so may cause performance and mutex issues for other users.

## Usage

### Visual Studio Code

1. Open this repository in Visual Studio Code.
2. Open the .mcp.json file and select Start above the `pdq-deploy-mcp` string.
3. Open the Interactive Chat in VS Code using `CTRL + Alt + I` and ask questions about the database from there!

### Other Coding Assistants

You can run this MCP server manually using the following command:

```bash
python ".\server\server.py" --db-path ".\path\to\your\Database.db"
```

As for how to integrate it with other coding asisstants, it depends on your LLM assistant! Feel free to contribute information here if you find a way to do this.