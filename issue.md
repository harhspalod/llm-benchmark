The core issue with [Claude Code](https://docs.anthropic.com/en/docs/claude-code/overview?utm_source=chatgpt.com) was that it’s designed specifically around Anthropic’s own API behavior, while your local Ollama models only imitate a subset of that API.

Several things collided:

* Claude Code expected Anthropic-native features
* LiteLLM translated only part of them
* Ollama models supported even less

So the chain became:

```txt
Claude Code → Anthropic-style requests
→ LiteLLM proxy
→ Ollama local model
```

and some request fields broke compatibility.

The biggest failures were:

### 1. Duplicate `/v1/v1`

You originally set:

```bash
ANTHROPIC_BASE_URL=http://localhost:4000/v1
```

But Claude Code already appends `/v1`.

So requests became:

```txt
/v1/v1/messages
```

which caused 404 errors.

---

### 2. Thinking mode

Claude Code sends advanced Anthropic parameters like:

```json
"thinking": {...}
```

Your local model:

DeepSeek-Coder 6.7B

does not support those reasoning/thinking configs.

That caused:

```txt
does not support thinking
```

and repeated retries.

---

### 3. Model identity mismatch

Claude Code internally assumed it was talking to models like:

* Opus
* Sonnet

But LiteLLM was serving:

* DeepSeek
* CodeLlama
* Mistral

Claude Code kept trying Anthropic-specific workflows against non-Anthropic models.

---

### 4. Agent/tool protocol differences

Claude Code uses:

* tool calling
* permission flows
* structured agent behaviors
* special retry logic

Small local Ollama models are mainly text generators. They aren’t trained to behave like full Claude agents.

So:

* retries looped
* tool calls broke
* generation stalled

---

### 5. OpenCode vs Claude Code

[OpenCode](https://github.com/opencode-ai/opencode?utm_source=chatgpt.com) is more provider-agnostic.

It works better with:

* Ollama
* OpenAI-compatible APIs
* local models

Claude Code is tightly integrated with Anthropic’s ecosystem.

That’s why your direct Ollama + curl test succeeded instantly, while Claude Code struggled.



zenalyst@zenalysts-MacBook-Pro codellama % opencode models
opencode/big-pickle
opencode/deepseek-v4-flash-free
opencode/minimax-m2.5-free
opencode/nemotron-3-super-free
opencode/ring-2.6-1t-free
anthropic/claude-3-5-haiku-20241022
anthropic/claude-3-5-haiku-latest
anthropic/claude-3-5-sonnet-20240620
anthropic/claude-3-5-sonnet-20241022
anthropic/claude-3-7-sonnet-20250219
anthropic/claude-3-haiku-20240307
anthropic/claude-3-opus-20240229
anthropic/claude-3-sonnet-20240229
anthropic/claude-haiku-4-5
anthropic/claude-haiku-4-5-20251001
anthropic/claude-opus-4-0
anthropic/claude-opus-4-1
anthropic/claude-opus-4-1-20250805
anthropic/claude-opus-4-20250514
anthropic/claude-opus-4-5
anthropic/claude-opus-4-5-20251101
anthropic/claude-opus-4-6
anthropic/claude-opus-4-6-fast
anthropic/claude-opus-4-7
anthropic/claude-sonnet-4-0
anthropic/claude-sonnet-4-20250514
anthropic/claude-sonnet-4-5
anthropic/claude-sonnet-4-5-20250929
anthropic/claude-sonnet-4-6
zenalyst@zenalysts-MacBook-Pro codellama % 
