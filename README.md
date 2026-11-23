<!-- mcp-name: io.github.eredden/pdq-deploy-mcp -->

# PDQ Deploy MCP Server

This project is an MCP (Model Context Protocol) server that provides **read-only** access to PDQ Deploy through a clone of its SQLite database. You can simply ask a question in plain English and have an AI agent query  PDQ Deploy *for you!* This works well for open-ended, complex problems and questions that you can wait on while eating lunch.

This project was created by [Evan Redden](https://www.linkedin.com/in/eredden).

## Requirements

- Python 3.10+ and version 2.0.0+ of the `mcp` module.
- Access to a PDQ Deploy SQLite database.
- An MCP-compatible client like GitHub Copilot in VS Code.

## Installation

You can easily install this MCP server from PyPi using PIP:

```bash
pip install pdq-deploy-mcp
```

If you want to modify this repository, you can clone it and install the required modules instead:

```powershell
git clone "https://github.com/eredden/PDQ-Deploy-MCP"

cd "PDQ-Deploy-MCP"

pip install -e .
```

## Setup

You must create a clone of your PDQ Deploy SQLite database to read from. Do not use  `Copy-Item` or `robocopy` to copy the database, as copying mid-write will corrupt your clone. Use the native [BackupDatabase command](https://docs.pdq.com/current-version/Deploy/index.html?cli-deploy-backupdatabase.htm) provided with PDQ Deploy to avoid corruption:

```powershell
PDQDeploy BackupDatabase -Path "C:\Backups\PDQ\" -Force
```

If you are using the `.mcp.json` config provided for GitHub Copilot in this repository, then save the database in the default `.\db\Database.db` path of this repository.

**Do not point this MCP server at a live PDQ Deploy database.** Using the live database will create SHARED locks that prevent PDQ Deploy from writing to the SQLite database.

## Usage

### GitHub Copilot in Visual Studio Code

1. Open this repository in Visual Studio Code.
2. Open the .mcp.json file and select Start above the `pdq-deploy-mcp` string.
3. Open the Interactive Chat in Visual Studio Code using `CTRL + Alt + I`.
4. If you have not already authenticated with GitHub Coplot, then do that! 
5. Ask GitHub Copilot about anything related to PDQ Deploy!

### Other Coding Assistants

You can run this MCP server manually using the following command:

```bash
pdq-deploy-mcp --db-path ".\path\to\your\Database.db"
```

As for how to integrate it with other AI coding assistants, figure it out! Feel free to contribute information here if you find a way to do this.
