# Agent Council

A multi-agent decision framework led by a single **Leader (Agent A)** that commands a panel of specialised sub-agents. The Leader routes every query, dispatches only the relevant agents, and passes final judgment before anything reaches the user. A live terminal UI shows which agent is running and tracks token usage in real time. Shared prompt caching keeps costs minimal, and local Ollama models can replace cloud calls for cheap tasks entirely.

---

## Why this beats a standard agent

| | Single agent | Agent Council |
|---|---|---|
| **Perspective** | One frame of reference | Strategist · Critic · Researcher · Executor — each with a distinct mandate |
| **Blind spots** | Model agrees with itself | Critic's only job is to find the flaw — structurally different output |
| **Routing cost** | Full context every call | Haiku (or free local model) routes for ~$0.0001 per question |
| **Context cost** | Re-sent every call | Shared context block cached once, read from cache by every agent |
| **Memory** | Lost between sessions | Auto-compressing session memory + persistent long-term JSON store |
| **Knowledge** | Training data only | Drop `.md` files into `knowledge/` — relevant snippets auto-injected |
| **Local inference** | Cloud only | Ollama detected at startup; cheap tasks (routing, compression) run free |
| **Extensibility** | Prompt engineering | Add a skill file → wired in via `config.yaml`, no other changes |
| **Observability** | Black box | Live UI shows agent status, model, token count, and cache hits |

### Real example: single agent vs council

**Question:** *"Should we build a custom LLM eval pipeline or use Braintrust?"*

**Single agent:** "Building custom gives you full control and flexibility. Start with a lightweight Python script…" — one agreeable perspective, no challenge.

**Agent Council:**

> **Strategist:** Off-the-shelf tools solve the eval problem faster and free engineering time for the actual product. Custom pipelines become a maintenance liability. Build custom only if requirements are genuinely novel.
>
> **Critic:** The "full control" argument is a trap. You're not in the evaluation tooling business. Custom pipelines under-invest in UI, collaboration, and regression tracking — exactly the parts that make evals useful over time. What specifically can't Braintrust do?
>
> **Executor:** Sign up for Braintrust today, port your first 10 test cases this week. If you hit a hard wall in 30 days, you'll have concrete requirements for a custom build.
>
> **Leader — Final Decision:** Use Braintrust. The Critic found no specific gap that justifies a build, and the Executor's framing shows you don't yet have the data to make that case. Revisit in 4 weeks with evidence, not assumptions.

The council is more reliable because the Critic is *structurally required* to disagree. A single model asked "is this a good idea?" will rationalise yes.

---

## How it works

```
Your question
     │
     ▼
  Leader (Agent A)
     │── Route: Haiku (or local model) picks 1–3 relevant agents   ~$0.0001
     │
     ├── Strategist  ◄─┐
     ├── Critic       ◄─┤  each receives: role + shared cached context + question
     ├── Researcher   ◄─┤  shared context is written once → read from cache by all
     └── Executor    ◄─┘
     │
     ▼
  Leader (Agent A)
     └── Judge: synthesises all responses → final answer
     │
     ▼
  Live UI updates throughout · token counts shown on completion
```

**Cost levers:**
- Routing runs on Haiku or a free local Ollama model
- All agents share one cached context block — you pay for one write, many reads
- System prompts use `cache_control: ephemeral` — repeated calls only pay for user-message tokens
- Session memory auto-compresses with Haiku when it grows long

---

## Install

```bash
git clone git@github.com:dskarthik96/agent-council.git
cd agent-council

pip install -r requirements.txt

cp .env.example .env
# edit .env and add your ANTHROPIC_API_KEY

python setup.py        # interactive setup wizard — configures agents and knowledge
```

That's it. No database, no Docker, no infra.

---

## Run

```bash
# Interactive session (recommended to start)
python run.py --interactive

# Single question
python run.py "Should we migrate to a monorepo?"

# Memory commands
python run.py --memory list
python run.py --memory show <key>

# Knowledge base
python run.py --kb list
python run.py --kb add <name> path/to/file.md
```

**Inside interactive mode:**
```
You: Should we hire a contractor or build in-house?

  [live panel updates as agents respond]

You: memory save hiring-decision      ← save this session to long-term memory
You: kb list                           ← show knowledge base entries
You: exit
```

---

## Setup wizard

`python setup.py` walks you through:

1. **Project name and context** — saved to `knowledge/project-context.md`, injected into every agent
2. **Which skills to enable** — pick from built-in set or add your own
3. **Per-agent custom instructions** — focus each agent on your domain
4. **Model selection** — override defaults per agent
5. **Local model detection** — auto-detects Ollama; routing runs free if available

All output goes to `config.yaml`. Edit it directly anytime.

---

## Add a custom skill

Create `skills/my_skill.py`:

```python
from skills.base import BaseSkill

class LegalAdvisorSkill(BaseSkill):
    name = "legal"
    description = "Identifies regulatory risks, IP concerns, compliance requirements"
    default_model = "claude-sonnet-4-6"
    system_prompt = """\
You are the Legal Advisor on this council.
Identify regulatory risks, IP concerns, and contractual obligations.
Ask: what could get us sued? What compliance requirements apply?"""
```

Register it in `skills/__init__.py`:

```python
from .my_skill import LegalAdvisorSkill
REGISTRY["legal"] = LegalAdvisorSkill
```

Add it to `config.yaml`:

```yaml
agents:
  legal:
    skill: legal
    extra_instructions: "focus on EU/UK jurisdiction"
```

Done. No other changes.

---

## Add knowledge

Drop any `.md` file into `knowledge/`. It is keyword-searched on every query and relevant snippets are injected into agents automatically.

```bash
# via CLI
python run.py --kb add company-strategy docs/strategy.md

# or just copy the file
cp ~/docs/product-principles.md knowledge/
```

---

## Use local models (free routing)

Install [Ollama](https://ollama.com), pull a model, done:

```bash
ollama pull llama3.2
```

Enable in `config.yaml`:
```yaml
local_models:
  enabled: true
```

Or re-run `python setup.py` — it auto-detects Ollama and asks. Routing and session compression will use the local model at zero API cost.

---

## Add MCP tools

Add server blocks under `mcp.servers` in `config.yaml`:

```yaml
mcp:
  servers:
    - name: filesystem
      command: npx
      args: [-y, "@modelcontextprotocol/server-filesystem", /Users/you/docs]
    - name: brave-search
      command: npx
      args: [-y, "@modelcontextprotocol/server-brave-search"]
      env:
        BRAVE_API_KEY: your_key
```

The council connects on startup and tools become available to the Leader.

---

## File map

```
agent-council/
├── run.py                  entry point
├── setup.py                interactive setup wizard
├── config.yaml             all configuration — edit this to customise
├── .env.example            copy to .env, add ANTHROPIC_API_KEY
├── requirements.txt
│
├── skills/                 ← plug-in agent skills (export / share independently)
│   ├── base.py             BaseSkill + SkillResponse — the skill interface
│   ├── strategist.py       long-term thinking
│   ├── critic.py           finds flaws
│   ├── researcher.py       synthesises knowledge
│   └── executor.py         concrete next steps
│
├── leader/
│   └── agent.py            Leader Agent A — routes, dispatches, judges
│
├── core/
│   ├── context.py          shared context builder (prompt cache manager)
│   └── models.py           model registry + local Ollama detection
│
├── memory/
│   ├── session.py          in-session context with auto-compression
│   └── store.py            persistent long-term JSON memory
│
├── ui/
│   └── terminal.py         live Rich terminal panel
│
├── mcp/
│   └── client.py           MCP server connector
│
└── knowledge/              drop .md files here
```

---

## Environment variables

| Variable | Required | Description |
|---|---|---|
| `ANTHROPIC_API_KEY` | Yes | Your Anthropic API key — get one at console.anthropic.com |
