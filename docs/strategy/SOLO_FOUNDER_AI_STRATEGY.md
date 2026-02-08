# Solo Founder AI Strategy: Maximizing Intelligence per Dollar

As a solo founder, your goal is to minimize operational overhead while maximizing the "intelligence" of your system. This document outlines how Episteme handles this by balancing LLM APIs with managed open-weights models.

## The Strategy: "The Best Model for the Job"

We use a tiered model strategy defined in `.env`. This allows you to swap providers without changing a single line of application code.

### 1. Reasoning & Extraction (DeepSeek-V3 / R1)
*   **Tasks**: Signal extraction, complex summaries, reasoning-heavy tasks.
*   **Why**: DeepSeek offers GPT-4o level reasoning at **10-20x lower cost**. For signal extraction, which requires precision and understanding of "epistemic signals," DeepSeek-V3 is the current best-value performer.
*   **Cost**: ~$0.20 per 1M tokens vs ~$5.00+ for GPT-4o.

### 2. Fast UX (Groq + Llama 3.3)
*   **Tasks**: Title generation, quick classification, real-time feedback.
*   **Why**: Groq's LPU technology makes Llama 3.3 (70B) feel instantaneous (500+ tokens/sec). This is critical for UX where users wait for a title or a quick suggestion.
*   **Cost**: Extremely competitive, often with generous free tiers or low pay-as-you-go.

### 3. General Purpose & Fallback (GPT-4o / Gemini)
*   **Tasks**: Multimodal tasks (vision), massive context RAG (Gemini 2M window).
*   **Why**: OpenAI remains the most reliable fallback. Google Gemini 1.5/2.0 is superior for RAG over large PDFs due to **Context Caching** and its massive 2M token window.

---

## How to Configure

Update your `.env` file with your API keys and preferred model strings:

```bash
# Providers
DEEPSEEK_API_KEY=sk-...
GROQ_API_KEY=gsk-...
OPENAI_API_KEY=sk-...
GOOGLE_API_KEY=AIza...

# Model Selection (Format: provider:model_name)
AI_MODEL_REASONING=deepseek:deepseek-chat
AI_MODEL_FAST=groq:llama-3.3-70b-versatile
AI_MODEL_EXTRACTION=deepseek:deepseek-chat
```

## Supported Providers (in `apps/common/ai_models.py`)

| Prefix | Provider | Example Model |
| :--- | :--- | :--- |
| `openai:` | OpenAI | `openai:gpt-4o-mini` |
| `deepseek:` | DeepSeek | `deepseek:deepseek-chat` |
| `groq:` | Groq | `groq:llama-3.3-70b-versatile` |
| `google:` | Google Gemini | `google:gemini-1.5-pro` |
| `anthropic:` | Anthropic | `anthropic:claude-3-5-sonnet` |

## Why Not Self-Hosting?

As a solo founder, **your time is your most expensive resource**. 
*   **vLLM / Ollama** on your own GPU/Server requires maintenance, scaling, and monitoring.
*   **Managed APIs** (DeepSeek, Groq, Together) give you the same open-source models with 99.9% uptime and zero maintenance for pennies.

## Cost Savings Analysis (Example)

| Task | GPT-4o-mini | DeepSeek-V3 | Savings |
| :--- | :--- | :--- | :--- |
| 1,000 Extractions | ~$1.00 | ~$0.10 | 90% |
| 1,000 Summaries | ~$2.00 | ~$0.15 | 92% |

By switching reasoning tasks to DeepSeek, you can effectively run 10x more experiments for the same budget.
