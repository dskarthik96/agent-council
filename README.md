# Council — Multi-Agent Decision System

A lightweight orchestration framework where a single controller routes questions to a panel of specialised AI agents, gathers their independent perspectives, and synthesises a single decision. Built on the Anthropic API with prompt caching, auto-compressing memory, a file-based knowledge base, and MCP integration hooks.

---

## Why this beats a standard single agent

| | Standard agent | Council |
|---|---|---|
| **Perspective** | One model, one frame of reference | 4 specialists with distinct roles (Strategist, Critic, Executor, Researcher) |
| **Blind spots** | Model agrees with itself | Critic actively tries to break every answer |
| **Token cost** | Full context sent every call | Haiku routes cheaply; only 1–3 relevant agents called per question |
| **Memory** | Lost between sessions | Compressed session memory + persistent long-term JSON store |
| **Knowledge** | Only training data | Drop `.md` files into `knowledge/` — agents get relevant snippets injected |
| **Tooling** | Manual tool wiring | MCP client: add any MCP server in `config.yaml`, tools auto-register |
| **Models** | One model for everything | Haiku for routing/compression, Sonnet for reasoning, configurable per agent |

**The core insight:** A single LLM asked "is this a good idea?" will almost always say yes and fill in supporting reasoning. A Critic agent whose entire system prompt is "find the flaw" produces a qualitatively different answer — and the synthesis of both is more reliable than either alone.

---

## Example: single agent vs council

**Question:** *"Should I build a custom LLM evaluation pipeline or use an off-the-shelf tool like Braintrust?"*

### Standard agent response
> Building a custom pipeline gives you full control and flexibility. You can tailor it to your exact metrics and integrate it with your existing infrastructure. I'd recommend starting with a lightweight Python script...

One perspective. Agreeable. Misses the tradeoffs.

---

### Council response

**Agents consulted:** Strategist, Critic, Executor

**Strategist:**
> Off-the-shelf tools solve the evaluation problem faster, freeing engineering time for the actual product. Custom pipelines become a maintenance liability — they need to evolve with your models and metrics. Build custom only if your evaluation requirements are genuinely novel.

**Critic:**
> The "full control" argument is a trap. You're not in the evaluation tooling business. Custom pipelines routinely under-invest in UI, collaboration, and regression tracking — the parts that make evals actually useful over time. Braintrust has 18 months of iteration on exactly this. What specifically can't it do that justifies the build cost?

**Executor:**
> Fastest path: sign up for Braintrust today, port your first 10 test cases this week. If you hit a hard wall in 30 days, you'll have concrete requirements for a custom build. Decision point is 4 weeks away, not today.

**Decision:**
> Use Braintrust. The Critic identified no specific gap that justifies a custom build, and the Executor's framing surfaces that you don't yet have the data to make the build case. Revisit in 4 weeks with concrete evidence of limitations, not assumptions.

---

## Quick start

**Prerequisites:** Python 3.11+, an `ANTHROPIC_API_KEY`

```bash
cd council
pip install -r requirements.txt

export ANTHROPIC_API_KEY=sk-ant-...

# Ask a single question
python council.py "Should I hire a contractor or build this feature in-house?"

# Interactive mode (multi-turn, context persists across questions)
python council.py --interactive
```

---

## All commands

```bash
# Single question
python council.py "Your question here"

# Interactive session
python council.py --interactive

# Long-term memory
python council.py --memory list
python council.py --memory show <key>

# Knowledge base
python council.py --kb list
python council.py --kb add <name> path/to/file.md
```

**Inside interactive mode:**
```
You: Should we migrate to a monorepo?
You: memory save monorepo-decision      ← persists this session to long_term/
You: memory list                         ← show all saved memories
You: kb list                             ← list knowledge base entries
You: exit
```

---

## How it works

```
Your question
     │
     ▼
  Router (Haiku)  ←  reads agent descriptions from config.yaml
     │  decides which 1–3 agents are relevant (cheap: ~$0.0001)
     ▼
  Agent calls (parallel concepts, sequential execution)
  ├── Strategist (Sonnet)  ─── sees: system prompt + KB snippets + compressed context
  ├── Critic     (Sonnet)  ─── sees: system prompt + KB snippets + compressed context
  └── Executor   (Haiku)   ─── sees: system prompt + KB snippets + compressed context
     │
     ▼
  Synthesiser (Sonnet)
     │  combines perspectives → final decision
     ▼
  Session memory updated
  (auto-compressed with Haiku after 10 exchanges)
```

**Token cost levers:**
- Routing is Haiku (~$0.0001 per question)
- Session compression is Haiku (~$0.0003 when triggered)
- System prompts are cached (`cache_control: ephemeral`) — repeated calls only pay for user-message tokens
- Only relevant agents are called — not all four every time

---

## Adding agents

Edit `config.yaml`:

```yaml
agents:
  lawyer:
    model: claude-sonnet-4-6
    role: |
      You are the Legal Advisor on this council. Identify regulatory risks,
      IP concerns, and contractual obligations. Ask: what could get us sued?
      What compliance requirements apply? What do we need a lawyer to review?
```

No code changes needed.

---

## Adding knowledge

Drop any `.md` file into `council/knowledge/`. It is automatically searched by keyword on every question and relevant snippets are injected into the agents' context.

```bash
# via CLI
python council.py --kb add company-context context.md

# or just copy the file
cp ~/docs/product-strategy.md council/knowledge/
```

---

## Adding MCP tools

Add a server block to `config.yaml` under `mcp.servers`:

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
        BRAVE_API_KEY: your_key_here
```

The council connects on startup and the tools become available to the orchestrator.

---

## File map

```
council/
├── council.py           entry point — CLI and interactive mode
├── config.yaml          agent definitions, model assignments, MCP servers
├── requirements.txt
├── core/
│   ├── agent.py         Agent class — one instance per council member
│   ├── orchestrator.py  routes, calls agents, synthesises decisions
│   └── kb.py            knowledge base — keyword search over .md files
├── memory/
│   ├── session.py       in-session context with auto-compression
│   └── store.py         persistent long-term JSON memory
├── mcp/
│   └── client.py        MCP server connector and tool adapter
└── knowledge/           drop .md files here
```

---

## Environment variables

| Variable | Required | Description |
|---|---|---|
| `ANTHROPIC_API_KEY` | Yes | Your Anthropic API key |
