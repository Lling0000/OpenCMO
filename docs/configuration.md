# Configuration Guide

OpenCMO can run with only an OpenAI-compatible model provider, then grow into a fuller monitoring setup as optional integrations are added. This guide explains the most important settings in `.env.example` so new users can decide what to configure first.

## Minimal local setup

Copy the example file and set an API key:

```bash
cp .env.example .env
```

Required:

```bash
OPENAI_API_KEY=sk-your-api-key-here
```

Optional, when using a compatible provider instead of the default OpenAI endpoint:

```bash
OPENAI_BASE_URL=https://your-provider.example/v1
OPENCMO_MODEL_DEFAULT=your-model-name
```

OpenCMO supports OpenAI-compatible providers such as OpenAI, DeepSeek, NVIDIA NIM, Kimi-compatible gateways, and local Ollama deployments.

## Common provider examples

DeepSeek:

```bash
OPENAI_API_KEY=sk-your-deepseek-key
OPENAI_BASE_URL=https://api.deepseek.com/v1
OPENCMO_MODEL_DEFAULT=deepseek-chat
```

NVIDIA NIM:

```bash
OPENAI_API_KEY=nvapi-your-nvidia-key
OPENAI_BASE_URL=https://integrate.api.nvidia.com/v1
OPENCMO_MODEL_DEFAULT=moonshotai/kimi-k2.5
```

Local Ollama:

```bash
OPENAI_API_KEY=ollama
OPENAI_BASE_URL=http://localhost:11434/v1
OPENCMO_MODEL_DEFAULT=llama3
```

## Optional integrations

These settings are not required for the first scan, but they unlock richer monitoring and reporting workflows.

| Area | Variables | When to configure |
| --- | --- | --- |
| GEO platforms | `ANTHROPIC_API_KEY`, `GOOGLE_AI_API_KEY`, `MOONSHOT_API_KEY`, `DASHSCOPE_API_KEY`, `DEEPSEEK_API_KEY`, `ZHIPU_API_KEY`, `DOUBAO_API_KEY` | Add these when you want broader AI-search visibility checks across Claude, Gemini, Kimi, Qwen, DeepSeek, GLM, or Doubao. |
| Web search and SERP | `TAVILY_API_KEY`, `PAGESPEED_API_KEY` | Add these for stronger search, keyword, crawler, and PageSpeed coverage. |
| Community monitoring | `YOUTUBE_API_KEY`, `TWITTER_BEARER_TOKEN`, `BLUESKY_HANDLE`, `BLUESKY_APP_PASSWORD` | Add these when you want richer community discovery beyond unauthenticated sources. |
| Reports and signup email | `OPENCMO_SMTP_HOST`, `OPENCMO_SMTP_PORT`, `OPENCMO_SMTP_USER`, `OPENCMO_SMTP_PASS`, `OPENCMO_SMTP_FROM`, `OPENCMO_REPORT_EMAIL` | Add these to send weekly reports and email verification codes through SMTP. |
| Dashboard access | `OPENCMO_WEB_TOKEN`, `OPENCMO_WEB_HOST` | Add these when exposing the dashboard outside local development. |
| Publishing | `REDDIT_CLIENT_ID`, `REDDIT_CLIENT_SECRET`, `TWITTER_API_KEY`, `OPENCMO_AUTO_PUBLISH` | Add these only when you are ready to enable controlled publishing workflows. |

## Local development notes

- Keep `.env` out of version control.
- Start with one working model provider before adding optional keys.
- If SMTP is not configured, verification codes are logged to stderr for local development.
- Set `OPENCMO_WEB_HOST=0.0.0.0` only when you intentionally want to bind the web service beyond `localhost`.
- Use the dashboard Settings panel for API keys when you prefer not to edit `.env` directly.

