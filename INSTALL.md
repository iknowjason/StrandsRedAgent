# Installation Guide (Ubuntu 24.04)

## Python Environment

```bash
sudo apt update
sudo apt install -y python3.13 python3.13-venv python3-pip

cd StrandsRedAgent
python3.13 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Environment Variables

```bash
cp .env.example .env
```

Edit `.env` and add your API key for your chosen provider. The default is xAI Grok:

```
XAI_API_KEY=xai-...
```

### Optional (enable gated tools)

```
BRAVE_API_KEY=...          # Enables brave_search OSINT
SERPER_API_KEY=...         # Enables LinkedIn recon
```

## External Tool Binaries

All external tools are optional. If a binary is missing, the corresponding MCP tool is silently skipped at startup.

### whois (used by osint_pipeline)

```bash
sudo apt install -y whois
```

### subfinder (passive subdomain discovery)

```bash
# Requires Go installed
go install -v github.com/projectdiscovery/subfinder/v2/cmd/subfinder@latest
```

Add `~/go/bin` to your PATH if not already:

```bash
echo 'export PATH="$HOME/go/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc
```

### AWS CLI (required for SES phishing delivery)

```bash
sudo apt install -y awscli
aws configure   # Set up credentials with SES permissions
```

If you don't need phishing email delivery, skip this — the campaign planner still works without it.

## Running

```bash
# Terminal 1: Start the MCP server
source .venv/bin/activate
python mcp_server.py

# Terminal 2: Start the agent client
source .venv/bin/activate
python client.py
```

The server runs on port 8001. The client connects automatically.

## Verifying Tool Gating

When a binary or API key is missing, the server prints `[SKIP]` during startup and the tool is not registered. The LLM agent never sees it.

Example output when subfinder is missing:

```
--- Red Team MCP Server (port 8001) ---
Registering tools...

  [osint (brave_search)]
  [linkedin]
  [subfinder]
  [SKIP] subfinder not found on PATH
  [osint_pipeline]
  [planner_tool]
  [phishing_tool]
  [campaign_state]

Tool registration complete.
```

## Troubleshooting

**"Connection refused" on client startup** — Make sure the MCP server is running in another terminal first.

**"XAI_API_KEY not set"** — Check your `.env` file exists and has the key for your chosen provider. The default expects `XAI_API_KEY`.

**Agent hits token limits** — Increase `WORKER_MAX_TOKENS` in `client.py`. The client prints tuning hints when this happens.
