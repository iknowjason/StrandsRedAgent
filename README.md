# StrandsRedAgent

A little Red Team Planner Agent for MITRE initial access.

Built with [Strands Agents SDK](https://github.com/strands-agents/sdk-python) and [MCP (Model Context Protocol)](https://modelcontextprotocol.io/). Uses a supervisor-worker architecture where a routing agent delegates to specialized workers: a **Planner** for passive OSINT reconnaissance and a **Campaign** agent for MITRE ATT&CK-mapped phishing simulation.

> **Authorization required.** This tool is for authorized penetration testing and red team engagements only. Obtain explicit written authorization before use against any target.

## What It Does

- **Passive OSINT** — WHOIS, crt.sh subdomain enumeration, HTTP header fingerprinting, Brave Search, subfinder, LinkedIn recon
- **MITRE ATT&CK Mapping** — Phishing campaigns mapped to T1566.001, T1566.002, T1078, T1190
- **Phishing Simulation** — Generates campaign templates and delivers via AWS SES (sandbox-safe)
- **Graceful Degradation** — Missing tools/API keys are silently skipped; the agent only sees what's available

## Architecture

```
User Input (Goal)
    |
[Supervisor] --> "planner" or "campaign"
    |
[Planner Agent]                    [Campaign Agent]
 - osint_pipeline(domain)           - generate_phishing_campaign(company)
   - WHOIS lookup                   - MITRE-mapped templates (5 campaigns)
   - crt.sh subdomains              - ses_check_sender / ses_verify_sender
   - HTTP headers                   - ses_send_phishing
   - Brave Search (optional)        - Multi-turn conversation
 - subfinder (optional)
```

**Supervisor** routes to the right worker. **Planner** does passive recon. **Campaign** handles social engineering simulation. All communication happens over MCP (port 8001).

## Quick Start

```bash
git clone https://github.com/iknowjason/StrandsRedAgent.git
cd StrandsRedAgent

python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
# Edit .env with your API key(s)

# Terminal 1: MCP server
python mcp_server.py

# Terminal 2: Agent client
python client.py
```

See [INSTALL.md](INSTALL.md) for full Ubuntu 24.04 setup including external tool binaries.

## Model Providers

The default provider is **xAI Grok** (least restrictive for red team operations). To switch providers, edit the `PROVIDER` and `MODEL_ID` constants at the top of `client.py`:

| Provider | Env Var | Example Model |
|----------|---------|---------------|
| xAI Grok (default) | `XAI_API_KEY` | `grok-4-fast-reasoning` |
| OpenAI | `OPENAI_API_KEY` | `gpt-5.4` |
| Anthropic | `ANTHROPIC_API_KEY` | `claude-sonnet-4-5-20250929` |

## Tool Gating

Each tool checks for its dependencies at server startup. If a binary or API key is missing, the tool is silently skipped — the LLM agent never sees it.

| Tool | Dependency | Type |
|------|-----------|------|
| `brave_search` | `BRAVE_API_KEY` | env var |
| `linkedin_recon` | `SERPER_API_KEY` | env var |
| `subfinder` | `subfinder` binary | PATH |
| `ses_*` (phishing delivery) | `aws` CLI | PATH |
| `osint_pipeline` | none (always available) | - |
| `generate_phishing_campaign` | none (always available) | - |

## Token Tuning

If agents hit token limits, adjust the constants at the top of `client.py`:

```python
SUPERVISOR_MAX_TOKENS = 300      # Supervisor routing budget
WORKER_MAX_TOKENS = 3200         # Worker response budget
WORKER_WINDOW_SIZE = 12          # Sliding window for multi-turn
PLANNER_MAX_AGENT_CYCLES = 3     # Max tool-call loops for planner
CAMPAIGN_MAX_AGENT_CYCLES = 2    # Max tool-call loops for campaign
```

## Project Structure

```
StrandsRedAgent/
├── mcp_server.py          # FastMCP server (port 8001)
├── client.py              # Multi-agent client with supervisor routing
├── agents/
│   ├── supervisor.py      # Routes goals to planner or campaign
│   ├── planner.py         # Passive OSINT reconnaissance
│   └── campaign.py        # Phishing campaign simulation
├── tools/
│   ├── tool_check.py      # Dependency gating (binary + env checks)
│   ├── osint.py           # Brave Search (gated)
│   ├── linkedin.py        # LinkedIn via Serper (gated)
│   ├── subfinder.py       # Subdomain discovery (gated)
│   ├── osint_pipeline.py  # WHOIS + crt.sh + headers + Brave
│   ├── planner_tool.py    # Planner placeholder
│   ├── phishing_tool.py   # MITRE-mapped phishing templates
│   ├── campaign_state.py  # Campaign memory viewer
│   └── ses_phishing.py    # AWS SES delivery (gated)
├── memory/
│   └── campaign_memory.py # Shared state across agents
├── mitre/
│   └── attack_graph.py    # MITRE ATT&CK initial access graph
├── requirements.txt
├── INSTALL.md             # Ubuntu 24.04 setup guide
├── .env.example
└── .gitignore
```

## License

MIT
