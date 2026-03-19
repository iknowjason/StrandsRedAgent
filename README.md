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

## AWS SES Phishing Delivery

The Campaign agent uses **Amazon Simple Email Service (SES)** to deliver phishing emails. This section covers everything needed to get SES working.

### Prerequisites

1. **AWS CLI** must be installed and on your PATH
2. **AWS credentials** must be configured (access keys or named profile)
3. **Sender and recipient identities** must be verified in SES

> If you skip SES setup, the campaign planner still works — you just can't deliver emails. The `ses_*` tools are silently skipped when the `aws` CLI is not found.

### 1. Install the AWS CLI

```bash
# Ubuntu/Debian
sudo apt install -y awscli

# Or install v2 directly
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
unzip awscliv2.zip
sudo ./aws/install
```

Verify it's installed:

```bash
aws --version
```

### 2. Configure AWS Credentials

The AWS CLI needs credentials with SES permissions. You have two options:

**Option A: Programmatic Access Keys (default profile)**

```bash
aws configure
```

This prompts for:

| Field | Value |
|-------|-------|
| AWS Access Key ID | Your IAM access key |
| AWS Secret Access Key | Your IAM secret key |
| Default region | `us-east-1` (or your SES region) |
| Output format | `json` |

Credentials are stored in `~/.aws/credentials` and `~/.aws/config`.

**Option B: Named Profile**

If you use multiple AWS accounts, configure a named profile:

```bash
aws configure --profile redteam
```

Then export the profile before running the agent:

```bash
export AWS_PROFILE=redteam
```

**Minimum IAM permissions required:**

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ses:SendEmail",
        "ses:VerifyEmailIdentity",
        "ses:GetIdentityVerificationAttributes"
      ],
      "Resource": "*"
    }
  ]
}
```

### 3. SES Identity Verification

**This is the most important step.** SES requires identity verification before it will send or receive email.

#### SES Sandbox Mode (default for new accounts)

New AWS accounts start in the **SES sandbox**. In sandbox mode, **both the sender AND recipient email addresses must be verified**. This is ideal for red team testing because you control both sides.

#### Verify the sender (your red team address)

```bash
# Send a verification email to the sender address
aws ses verify-email-identity --email-address sender@yourdomain.com --region us-east-1
```

The owner of `sender@yourdomain.com` will receive an email from AWS with a verification link. **Click the link** to complete verification.

Check verification status:

```bash
aws ses get-identity-verification-attributes \
  --identities sender@yourdomain.com \
  --region us-east-1
```

Expected output when verified:

```json
{
  "VerificationAttributes": {
    "sender@yourdomain.com": {
      "VerificationStatus": "Success"
    }
  }
}
```

#### Verify the recipient (the phishing target)

In sandbox mode, the recipient must also be verified:

```bash
# Send verification email to the target address
aws ses verify-email-identity --email-address target@example.com --region us-east-1
```

The target must click the verification link. For red team engagements, coordinate this with the client or use a test mailbox you control.

Check recipient verification:

```bash
aws ses get-identity-verification-attributes \
  --identities target@example.com \
  --region us-east-1
```

#### Verify a whole domain (optional, production use)

If you've moved out of sandbox mode or want to verify an entire domain:

```bash
aws ses verify-domain-identity --domain yourdomain.com --region us-east-1
```

This returns a TXT record you must add to your domain's DNS. Once the DNS propagates, all addresses at that domain are verified.

#### List all verified identities

```bash
aws ses list-identities --region us-east-1
```

#### Check multiple identities at once

```bash
aws ses get-identity-verification-attributes \
  --identities sender@yourdomain.com target@example.com \
  --region us-east-1
```

### SES Quick Reference

| Task | Command |
|------|---------|
| Verify sender email | `aws ses verify-email-identity --email-address EMAIL --region us-east-1` |
| Verify recipient email | `aws ses verify-email-identity --email-address EMAIL --region us-east-1` |
| Check verification status | `aws ses get-identity-verification-attributes --identities EMAIL --region us-east-1` |
| List all verified identities | `aws ses list-identities --region us-east-1` |
| Verify a domain | `aws ses verify-domain-identity --domain DOMAIN --region us-east-1` |
| Check send quota | `aws ses get-send-quota --region us-east-1` |
| Request production access | `aws sesv2 put-account-details` (via AWS Console is easier) |

### Workflow Summary

```
1. aws configure                          # Set up credentials
2. aws ses verify-email-identity ...      # Verify sender
3. (click verification link in email)
4. aws ses verify-email-identity ...      # Verify recipient (sandbox)
5. (recipient clicks verification link)
6. python client.py                       # Run the agent
7. "Create a phishing campaign for ..."   # Agent handles the rest
```

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
