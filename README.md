# OpenCowork Tutorial

> ⚠️ **Not for production use.** This is the supporting material for a [video tutorial](https://youtu.be/jMgzHt2MIJ8).

Open-source alternative to Claude Cowork. Grant folder access, describe a task, and let an AI agent execute it autonomously.

Works with **Ollama** (local) or **HuggingFace** (cloud).

## Features

- **Shell-first design** — One `run_shell` tool replaces 10+ file tools
- **Allowlist security** — Only permitted commands can run
- **Universal client** — Any OpenAI-compatible API (Ollama, HuggingFace, etc.)
- **3 tools**: `run_shell`, `fetch_url`, `search_web`

## Quick Start

### 1. Install dependencies

```bash
# Using uv (recommended)
uv sync

# Or pip
pip install -r requirements.txt
```

### 2. Configure

```bash
cp .env.example .env
```

Edit `.env` with your settings:

**Ollama (local):**
```bash
OPENCOWORK_MODEL=qwen2.5:7b
OPENCOWORK_BASE_URL=http://localhost:11434/v1
OPENCOWORK_API_KEY=ollama
```

**HuggingFace (cloud):**
```bash
OPENCOWORK_MODEL=Qwen/Qwen2.5-72B-Instruct:novita
OPENCOWORK_BASE_URL=https://router.huggingface.co/v1
OPENCOWORK_API_KEY=hf_your_token
```

### 3. Run

```bash
python main.py
```

Grant folder access when prompted, then describe your task.

## Example Tasks

```
📋 Task: Organize this folder by file type
📋 Task: Find all images larger than 1MB
📋 Task: Create a script to find duplicate files
📋 Task: Research "topic" and save a summary
```

## Architecture

```
┌─────────────────────────────────┐
│        Your Task                │
└───────────────┬─────────────────┘
                ▼
┌─────────────────────────────────┐
│     OpenAI Agents SDK           │
│  (Agent loop, tool dispatch)    │
└───────────────┬─────────────────┘
                ▼
┌─────────────────────────────────┐
│   Any OpenAI-Compatible API     │
│  Ollama (local) or HuggingFace  │
└───────────────┬─────────────────┘
                ▼
┌─────────────────────────────────┐
│        3 Tools                  │
│  run_shell / fetch_url / search │
└─────────────────────────────────┘
```

## Security

- **Allowlist**: Only specific commands allowed (ls, cat, mv, grep, python, git, etc.)
- **Path blocking**: `../` traversal and sensitive paths blocked
- **Sandbox**: All commands run in the granted directory

⚠️ This is a demo. For production, use OS-level sandboxing (Docker, bubblewrap, etc.)

## HuggingFace Providers

Use the `model:provider` format:

```bash
OPENCOWORK_MODEL=Qwen/Qwen2.5-72B-Instruct:novita
OPENCOWORK_MODEL=deepseek-ai/DeepSeek-R1:together
OPENCOWORK_MODEL=meta-llama/Llama-3-70b:fireworks-ai
```

Options: `:novita`, `:together`, `:fireworks-ai`, `:groq`, `:auto`, `:fastest`, `:cheapest`

## License

MIT
