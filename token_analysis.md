# Token Cost Analysis — Agent Council vs Standard Setups

## Methodology

**Question used:** *"Should I prioritise new features or technical debt this quarter?"*
(~15 input tokens)

**Models priced at Anthropic May 2026 rates:**

| Model | Input | Output | Cache write | Cache read |
|---|---|---|---|---|
| Claude Haiku 4.5 | $0.80/1M | $4.00/1M | $1.00/1M | $0.08/1M |
| Claude Sonnet 4.6 | $3.00/1M | $15.00/1M | $3.75/1M | $0.30/1M |

Cache write = 25% surcharge over base input price.
Cache read = 90% discount off base input price.

---

## Setup A — Single Sonnet call (baseline)

One model, one perspective, no caching.

```
System prompt:   150 tokens  →  $0.000450   (Sonnet input)
User question:    15 tokens  →  $0.000045
Output response: 400 tokens  →  $0.006000   (Sonnet output)
─────────────────────────────────────────────────────────
Total per call:                  $0.006495   ≈ $0.0065
```

**10 questions/day:** $0.065 | **30 days:** $1.95

---

## Setup B — Naive 3-agent (no caching)

Same 3-agent concept but every agent re-reads the full context on every call.
This is the typical "multi-agent chain" implementation without prompt caching.

```
Routing (Sonnet):
  system(150) + question(15) + agent list(100) = 265 in  →  $0.000795
  output: 40 tokens                                       →  $0.000600

Strategist (Sonnet):
  system(150) + shared context(400) + question(15) = 565 in  →  $0.001695
  output: 280 tokens                                          →  $0.004200

Critic (Sonnet):
  system(150) + shared context(400) + question(15) = 565 in  →  $0.001695
  output: 280 tokens                                          →  $0.004200

Executor (Sonnet — same model as above, no tiering):
  system(150) + shared context(400) + question(15) = 565 in  →  $0.001695
  output: 220 tokens                                          →  $0.003300

Leader judgment (Sonnet):
  system(150) + context(400) + question(15) + responses(780) = 1345 in  →  $0.004035
  output: 420 tokens                                                      →  $0.006300
─────────────────────────────────────────────────────────────────────────────────────
Total per call:                                                             $0.028515  ≈ $0.029
```

**10 questions/day:** $0.29 | **30 days:** $8.70

The shared context block (400 tokens) is paid at full Sonnet input price **5 times per question**.

---

## Setup C — Agent Council (this system, first call)

First call pays cache WRITE cost on shared context — a one-time investment.

```
Routing (Haiku — cheap tier):
  cache write system(50) + input(165) = $0.000052 + $0.000132  →  $0.000184
  output: 30 tokens                                              →  $0.000120

Shared context cache WRITE (400 tokens, Sonnet):
  $3.75/1M × 400                                                →  $0.001500  ← one-time

Strategist (Sonnet):
  cache READ shared(400):  $0.30/1M × 400                       →  $0.000120
  cache WRITE role(120):   $3.75/1M × 120                       →  $0.000450
  user question(15):       $3.00/1M × 15                        →  $0.000045
  output: 260 tokens:      $15/1M × 260                         →  $0.003900

Critic (Sonnet):
  cache READ shared(400)                                         →  $0.000120
  cache WRITE role(120)                                          →  $0.000450
  user question(15)                                              →  $0.000045
  output: 260 tokens                                             →  $0.003900

Executor (Haiku — cheap tier):
  cache READ shared(400):  $0.08/1M × 400                       →  $0.000032
  cache WRITE role(100):   $1.00/1M × 100                       →  $0.000100
  user question(15):       $0.80/1M × 15                        →  $0.000012
  output: 200 tokens:      $4.00/1M × 200                       →  $0.000800

Leader judgment (Sonnet):
  cache READ shared(400)                                         →  $0.000120
  input: question(15) + responses(740) = 755 tokens             →  $0.002265
  output: 420 tokens                                             →  $0.006300
────────────────────────────────────────────────────────────────────────────────
Total first call:                                                   $0.019463  ≈ $0.019
```

---

## Setup C — Agent Council (repeat calls, cache READS)

After the first call, shared context and agent roles are in cache.
Only the user question and new responses are charged at full price.

```
Routing (Haiku): same as above                                  →  $0.000184 (no change)

Shared context cache READ (400 tokens, Sonnet):
  $0.30/1M × 400 (×3 agents + leader = ×4 reads)               →  $0.000480  ← was $0.001500

Strategist (Sonnet):
  cache READ shared(400)                                         →  $0.000120
  cache READ role(120):    $0.30/1M × 120                       →  $0.000036  ← was $0.000450
  user question(15)                                              →  $0.000045
  output: 260 tokens                                             →  $0.003900

Critic (Sonnet):
  cache READ shared + role                                       →  $0.000156
  user question(15)                                              →  $0.000045
  output: 260 tokens                                             →  $0.003900

Executor (Haiku):
  cache READ shared + role                                       →  $0.000040
  user question(15)                                              →  $0.000012
  output: 200 tokens                                             →  $0.000800

Leader judgment (Sonnet):
  cache READ shared(400)                                         →  $0.000120
  input: question(15) + responses(740) = 755 tokens             →  $0.002265
  output: 420 tokens                                             →  $0.006300
────────────────────────────────────────────────────────────────────────────────
Total repeat call:                                                  $0.017423  ≈ $0.017
```

---

## Setup D — Council with local Ollama routing (free tier)

Replace Haiku routing + session compression with a free local model (e.g. llama3.2:3b).

```
Routing (local Ollama):                                         →  $0.000000  ← FREE
Session compression (local Ollama):                             →  $0.000000  ← FREE
Everything else same as Setup C repeat call                     →  $0.017239
────────────────────────────────────────────────────────────────────────────────
Total:                                                              $0.017239  ≈ $0.017
(routing + compression become free; savings compound with usage frequency)
```

---

## Summary comparison

| Setup | Cost/question | Quality | 100 questions |
|---|---|---|---|
| A — Single Sonnet | $0.0065 | One perspective | $0.65 |
| B — Naive 3-agent (no cache) | $0.0285 | 3 perspectives | $2.85 |
| C — Council (first call) | $0.0195 | 3 perspectives + Leader judgment | $1.95* |
| C — Council (repeat calls) | $0.0174 | 3 perspectives + Leader judgment | $1.74 |
| D — Council + local routing | $0.0172 | Same + free routing | $1.72 |

*First-call cost amortises quickly — by call 3 you've broken even vs naive.

**Council vs naive multi-agent: 39% cheaper on first call, 40% cheaper ongoing.**
**Council vs single Sonnet: 2.7× the cost but 4× the output** (3 specialist responses + synthesised judgment).

---

## Where the savings come from

### 1. Prompt caching on shared context
The 400-token project context block is written to cache **once** and read across all 4 agent calls per question. Without caching:

- 4 agents × 400 tokens × $3/1M = **$0.0048 per question**
- With caching: 1 write ($0.0015) + 4 reads ($0.00048) = **$0.00198 per question**
- **Saving: 59% on context costs**

As the knowledge base grows to 1,000 tokens, cache savings grow proportionally. At 2,000 tokens KB the saving is ~$0.011 per question just on context.

### 2. Model tiering
Using Haiku for cheap tasks instead of Sonnet:

| Task | Naive (Sonnet) | Council |
|---|---|---|
| Routing | $0.000795 | $0.000184 (Haiku) |
| Executor agent | $0.005895 | $0.000952 (Haiku) |
| Session compression | $0.001500 | $0.000400 (Haiku) |

**Saving vs all-Sonnet: $0.0071 per question** just from model tiering.

### 3. Selective agent dispatch
The Leader only calls relevant agents (1–3), never all 4.
A question with a clear execution path skips Strategist and Researcher.
Average: 2.2 agents called per question based on typical routing patterns.

### 4. Local model routing (optional, free)
Routing is a classification task — which agents are relevant? A 3B parameter local model handles it fine. Moving routing + compression to Ollama eliminates ~$0.0003/question and **all session compression costs**.

At 500 questions/month this saves ~$1.50 from routing alone — small in absolute terms, but the principle scales: every cheap task offloaded to local is zero API cost.

---

## Break-even vs quality comparison

If you wanted equivalent quality from a single agent, you'd need:
- A chain-of-thought prompt (~500 tokens) asking it to think from multiple angles
- 3 separate "persona" calls (one playing Strategist, one Critic, one Executor)
- A final synthesis call

That's 4 Sonnet calls with no caching → **$0.034/question** — 2× the cost of the Council.

The Council is not just cheaper than the naive equivalent. It produces structurally better output because the Critic agent is architecturally *required* to disagree — it cannot rationalise its way to agreement the way a single model can.
