# Claude Code Setup Guide

This guide shows you how to configure the CAU e-class MCP server with Claude Code.

## Step 1: Install the MCP Server

```bash
pip install git+https://github.com/won33/cau-eclass-mcp.git
```

Verify installation:
```bash
python -m cau_eclass_mcp --help
```

## Step 2: Configure Credentials

Choose one of the following methods:

### Option A: System Keyring (Recommended)

Save credentials to your OS keyring (Windows Credential Manager, macOS Keychain, etc.):

```bash
python -c "from cau_eclass_mcp.utils.credentials import CredentialManager; m = CredentialManager(); m.prompt_for_credentials()"
```

Enter your CAU student ID and password when prompted.

### Option B: Environment Variables

For temporary usage or if keyring is unavailable:

**Linux/macOS (bash/zsh)**:
```bash
export CAU_USERNAME="your_student_id"
export CAU_PASSWORD="your_password"
```

Add to `~/.bashrc` or `~/.zshrc` for persistence.

**Windows (PowerShell)**:
```powershell
$env:CAU_USERNAME="your_student_id"
$env:CAU_PASSWORD="your_password"
```

For persistence, use System Environment Variables (Windows Settings).

## Step 3: Configure Claude Code

### For Global Access

Edit Claude Code's global configuration file:

**Linux/macOS**: `~/.claude/claude.json`
**Windows**: `C:\Users\YourName\.claude\claude.json`

Add the MCP server configuration:

```json
{
  "mcpServers": {
    "cau-eclass": {
      "command": "python",
      "args": ["-m", "cau_eclass_mcp"]
    }
  }
}
```

### For Project-Specific Access

Create `.mcp.json` in your project root directory:

```json
{
  "cau-eclass": {
    "command": "python",
    "args": ["-m", "cau_eclass_mcp"]
  }
}
```

**Example**: If you have an Obsidian vault for school notes:
```
your-obsidian-vault/
├── .mcp.json          ← Create this file
├── 10_SCHOOL/
├── 20_LIFE/
└── DASHBOARD.md
```

## Step 4: Restart Claude Code

Close and restart Claude Code to load the new MCP server configuration.

## Step 5: Test the Connection

Open Claude Code and try these commands:

```
You: "Show my e-class dashboard"

Expected: Claude lists your active courses with IDs
```

```
You: "List announcements for [course name]"

Expected: Claude shows recent announcements for that course
```

## Troubleshooting

### "MCP server not found"

- Check that Python is in your PATH: `python --version`
- Verify installation: `pip show cau-eclass-mcp`
- Try absolute path to Python in `.mcp.json`:
  ```json
  {
    "cau-eclass": {
      "command": "/usr/bin/python3",
      "args": ["-m", "cau_eclass_mcp"]
    }
  }
  ```

### "Authentication failed"

- Verify credentials are correct
- Delete and re-enter credentials:
  ```bash
  python -c "from cau_eclass_mcp.utils.credentials import CredentialManager; m = CredentialManager(); m.delete_credentials(); m.prompt_for_credentials()"
  ```

### "MCP server not responding"

1. Test the server manually:
   ```bash
   python -m cau_eclass_mcp
   ```
   Press Ctrl+C to exit after verifying it starts.

2. Check Claude Code logs for error messages

3. Verify JSON syntax in `.mcp.json` (no trailing commas!)

### Session expired

Sessions are cached for 1 hour. If you see "session expired" errors, restart Claude Code to trigger re-authentication.

## Advanced Configuration

### Custom Python Environment

If using a virtual environment:

```json
{
  "cau-eclass": {
    "command": "/path/to/venv/bin/python",
    "args": ["-m", "cau_eclass_mcp"]
  }
}
```

### Multiple MCP Servers

You can configure multiple MCP servers in the same file:

```json
{
  "mcpServers": {
    "cau-eclass": {
      "command": "python",
      "args": ["-m", "cau_eclass_mcp"]
    },
    "other-server": {
      "command": "other-command",
      "args": ["--option", "value"]
    }
  }
}
```

## Example Usage

Once configured, you can naturally ask Claude about your e-class data:

- "What courses am I taking this semester?"
- "Show me announcements from the last week"
- "List all assignments due before Friday"
- "Which lectures haven't I watched yet?"
- "Summarize the latest announcement in 암호와 인증"

Claude will automatically use the MCP tools to fetch and display the information.

## Security Notes

- Credentials stored in keyring are encrypted by your OS
- Never commit `.mcp.json` with hardcoded credentials
- Use environment variables for CI/CD environments
- The MCP server only runs when Claude Code is active

---

**Need help?** Open an issue on [GitHub](https://github.com/won33/cau-eclass-mcp/issues)
