<div align="center">

```
  ███╗   ███╗ █████╗ ███╗   ██╗██████╗  █████╗ ████████╗███████╗
  ████╗ ████║██╔══██╗████╗  ██║██╔══██╗██╔══██╗╚══██╔══╝██╔════╝
  ██╔████╔██║███████║██╔██╗ ██║██║  ██║███████║   ██║   █████╗
  ██║╚██╔╝██║██╔══██║██║╚██╗██║██║  ██║██╔══██║   ██║   ██╔══╝
  ██║ ╚═╝ ██║██║  ██║██║ ╚████║██████╔╝██║  ██║   ██║   ███████╗
  ╚═╝     ╚═╝╚═╝  ╚═╝╚═╝  ╚═══╝╚═════╝ ╚═╝  ╚═╝   ╚═╝   ╚══════╝
```

### Autonomous AI. Governed by Authority.

[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![ArmorIQ](https://img.shields.io/badge/ArmorIQ-SDK-FF6B35?style=for-the-badge&logo=shield&logoColor=white)](https://armoriq.ai)
[![Groq](https://img.shields.io/badge/Groq-Llama_3.1_70B-F55036?style=for-the-badge&logo=meta&logoColor=white)](https://groq.com)
[![Ed25519](https://img.shields.io/badge/Crypto-Ed25519-6C3483?style=for-the-badge&logo=gnuprivacyguard&logoColor=white)](https://en.wikipedia.org/wiki/EdDSA)
[![License](https://img.shields.io/badge/License-MIT-green?style=for-the-badge)](LICENSE)

---

> *We don't rely on the agent promising not to do something.*
> *The authority boundary makes the unauthorized action mathematically impossible.*

</div>

MANDATE is a cryptographically governed multi-agent code review pipeline built on the [ArmorIQ SDK](https://armoriq.ai). It demonstrates the difference between **capability** and **authority** in autonomous AI systems.

## The Problem

Modern AI agents are increasingly autonomous — they can read code, analyze vulnerabilities, and even write fixes. But **capability ≠ authority**. Just because an agent *can* rewrite your repository doesn't mean it *should be allowed to*.

Traditional guardrails rely on prompt engineering ("please don't write files"). MANDATE makes unauthorized actions **cryptographically impossible**.

## How It Works

```
                    ┌──────────────────────────┐
                    │  COORDINATOR (Root)       │
                    │  Mints Root IntentToken   │
                    │  via capture_plan()       │
                    └─────────┬────────────────┘
                              │ delegate()
              ┌───────────────┼───────────────┐
              ▼               ▼               ▼
    ┌─────────────┐  ┌──────────────┐  ┌──────────────┐
    │ LINTER      │  │ SECURITY     │  │ PERFORMANCE  │
    │ READ_DIFF   │  │ READ_DIFF    │  │ READ_DIFF    │
    │ RUN_LINTER  │  │ RUN_SCAN     │  │ RUN_PERF     │
    │ POST_COMMENT│  │ POST_COMMENT │  │ POST_COMMENT │
    └─────────────┘  └──────┬───────┘  └──────────────┘
                            │
                            ▼ invoke(WRITE_FILE)
                      ┌──────────────┐
                      │  🛡️ BLOCKED   │
                      │  Not in scope │
                      └──────────────┘
```

1. **`capture_plan()`** — The Coordinator declares the full plan of tool calls and receives a cryptographic IntentToken from ArmorIQ.
2. **`delegate()`** — The Coordinator issues scoped sub-tokens to each agent, limiting them to specific actions (e.g., `READ_DIFF`, `RUN_LINTER`, `POST_COMMENT`).
3. **`invoke()`** — Every tool execution is routed through ArmorIQ's proxy. If the action isn't in the agent's delegated scope, it is **blocked at the enforcement boundary**.

## Key Features

- **Ed25519 Agent Identities** — Each agent has a unique cryptographic keypair, proving independence.
- **Subtree Delegation** — Agents receive only the authority they need, nothing more.
- **LLM-Powered Analysis** — Uses Groq (Llama 3.1 70B) for real-time code review across lint, security, and performance.
- **Immutable Audit Trail** — Every allow/block decision is recorded with full context.
- **GitHub Actions Integration** — Runs automatically on pull requests.

## Quickstart

### Prerequisites
- Python 3.10+
- [ArmorIQ API Key](https://platform.armoriq.ai/dashboard/api-keys)
- [Groq API Key](https://console.groq.com)

### Setup

```bash
# Clone the repository
git clone https://github.com/bitmorphic/mandate.git
cd mandate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your real API keys
```

### Run the Demo

```bash
# GOVERNED mode — agent writes are BLOCKED
python demo/run_governed.py

# UNGOVERNED mode — agent writes SUCCEED (proves the capability exists)
python demo/run_ungoverned.py
```

### Run on Your Own Repo

```bash
# Review a real repository (governed by default)
python review_repo.py /path/to/your/repo --branch main

# Run without governance (dangerous!)
python review_repo.py /path/to/your/repo --branch main --ungoverned
```

### GitHub Actions (CI/CD)

Add `ARMORIQ_API_KEY` and `GROQ_API_KEY` as repository secrets. MANDATE will automatically review every pull request.

## Project Structure

```
ARMOUR_IQ/
├── coordinator/main.py       # Orchestrator — spawns agents, aggregates results
├── agents/
│   ├── base.py               # Base agent with governance integration
│   ├── linter/agent.py       # PEP 8 / style analysis (Groq LLM)
│   ├── security/agent.py     # OWASP vulnerability scanner (Groq LLM)
│   └── performance/agent.py  # Algorithmic complexity checker (Groq LLM)
├── governance/
│   ├── authority.py           # ArmorIQ SDK integration (capture_plan, delegate, invoke)
│   ├── identity.py            # Ed25519 keypair management
│   └── audit.py               # Immutable audit trail
├── tools/
│   ├── git_ops.py             # Git read/write operations
│   ├── remediation.py         # Dangerous: file write + commit capability
│   └── ...                    # Lint, security scan, performance tools
├── demo/
│   ├── run_governed.py        # Day 2: governance ON (writes blocked)
│   ├── run_ungoverned.py      # Day 1: governance OFF (writes succeed)
│   └── fixture/               # Deterministic vulnerable test code
├── llm/groq_client.py         # Groq API client for LLM analysis
├── review_repo.py             # CLI entry point for real repo reviews
├── .github/workflows/         # GitHub Actions CI/CD
├── requirements.txt
└── pyproject.toml
```

## ArmorIQ SDK Integration

MANDATE uses the three core SDK methods required by the ArmorIQ track:

| Method | Where | Purpose |
|--------|-------|---------|
| `capture_plan()` | `governance/authority.py` | Registers the full tool plan and mints the root IntentToken |
| `delegate()` | `governance/authority.py` | Issues scoped sub-tokens to each independent agent |
| `invoke()` | `governance/authority.py` | Routes every tool call through the ArmorIQ proxy PEP |

## License

MIT
