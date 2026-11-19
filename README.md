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

You will need to grab a copy of a PDQ Deploy database from `C:\ProgramData\Admin Arsenal\PDQ Deploy\Database.db` on the desired PDQ server. This MCP server requires the `PDQ_DEPLOY_DB` environment variable to point to your SQLite database. Create that environment variable using the PowerShell cmdlet below:

```powershell
$Env:PDQ_DEPLOY_DB = "C:\Your\Path\Here\Database.db"
```

You are responsible for keeping your database copy up-to-date. **Avoid pointing this MCP server at a live PDQ Deploy database,** as doing so may cause performance and mutex issues for other users.

## Usage

1. Open your cloned repository in VS Code and select **Ctrl + Shift + P** to open the Command Palette.
2. Select the `MCP: List Servers` option and start the `pdq-deploy-mcp` server.
3. Select **Ctrl + Alt + I** to open the interactive chat window. You will need to sign into GitHub Copilot before you can use the provided LLMs.
4. Ask a question! e.g., who was responsible for the .NET 10 deployment last weekend?
5. Get your answer back! Rinse and repeat.
