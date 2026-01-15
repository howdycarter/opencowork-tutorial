"""
OpenCowork Agent - Open-source Claude Cowork alternative.

Uses OpenAI Agents SDK with any OpenAI-compatible API (Ollama, HuggingFace, etc.)
3 tools: run_shell, fetch_url, search_web
"""

import os
from agents import Agent, OpenAIChatCompletionsModel
from openai import AsyncOpenAI

from tools import run_shell, fetch_url, search_web

# =============================================================================
# MODEL CONFIGURATION
# =============================================================================
# All providers use OpenAI-compatible APIs directly (no LiteLLM)
#
# Ollama (local):
#   OPENCOWORK_MODEL=qwen2.5:7b
#   OPENCOWORK_BASE_URL=http://localhost:11434/v1
#   OPENCOWORK_API_KEY=ollama
#
# HuggingFace (use router.huggingface.co with model:provider format):
#   OPENCOWORK_MODEL=Qwen/Qwen2.5-72B-Instruct:novita
#   OPENCOWORK_BASE_URL=https://router.huggingface.co/v1
#   OPENCOWORK_API_KEY=hf_your_token
#
#   Provider options: :novita, :together, :fireworks-ai, :groq, :auto, :fastest, :cheapest
#
# Any OpenAI-compatible endpoint:
#   OPENCOWORK_MODEL=your-model
#   OPENCOWORK_BASE_URL=https://your-endpoint/v1
#   OPENCOWORK_API_KEY=your-key

MODEL_ID = os.environ.get("OPENCOWORK_MODEL", "qwen2.5:7b")
BASE_URL = os.environ.get("OPENCOWORK_BASE_URL", "http://localhost:11434/v1")
API_KEY = os.environ.get("OPENCOWORK_API_KEY", "ollama")


def create_agent() -> Agent:
    """Create and configure the OpenCowork agent."""

    # Universal OpenAI-compatible client
    client = AsyncOpenAI(
        base_url=BASE_URL,
        api_key=API_KEY,
    )
    model = OpenAIChatCompletionsModel(
        model=MODEL_ID,
        openai_client=client,
    )

    agent = Agent(
        name="OpenCowork",
        instructions="""You are OpenCowork, a local task assistant with shell access.

# Your Tools

1. **run_shell** - Execute shell commands in the user's granted directory
   - Standard Unix tools: ls, cat, cp, mv, rm, mkdir, find, grep, sed, awk, etc.
   - Scripting: python, bash
   - Version control: git
   - Supports pipes (|) and chaining (&&)

2. **fetch_url** - Fetch and extract text from web pages

3. **search_web** - Search the web for information

# How to Work

You have full shell access within the granted directory. Use it efficiently:

**File operations:**
```bash
ls -la                           # List files
cat file.txt                     # Read file
cp src dst                       # Copy
mv old new                       # Move/rename
rm file                          # Delete (be careful!)
mkdir -p dir/subdir              # Create directories
```

**Batch operations (powerful!):**
```bash
# Move all PDFs to a folder
mkdir -p pdfs && mv *.pdf pdfs/

# Find and list large files
find . -size +10M -exec ls -lh {} \\;

# Organize by extension
for ext in pdf jpg png; do mkdir -p "$ext" && mv *."$ext" "$ext/" 2>/dev/null; done

# Search file contents
grep -r "pattern" --include="*.txt"
```

**Write and run scripts:**
```bash
cat > script.py << 'EOF'
import os
for f in os.listdir('.'):
    print(f)
EOF
python script.py
```

**Git:**
```bash
git status
git add .
git commit -m "message"
git log --oneline -5
```

# Your Routine

1. **Understand** - Parse the user's request
2. **Plan** - Think through the steps
3. **Execute** - Use shell commands efficiently (batch when possible)
4. **Report** - Summarize what you did

# Rules

- All operations are sandboxed to the granted directory
- Be careful with rm - ask if unsure
- For complex tasks, write a script instead of many commands
- Explain what you're doing as you work
- If something fails, try an alternative approach

# Style

- Be efficient - use pipes and chaining
- Prefer one-liners over multiple commands
- For repetitive tasks, write loops or scripts
- Keep explanations brief but clear
""",
        tools=[run_shell, fetch_url, search_web],
        model=model,
    )

    return agent


# Pre-configured agent instance
agent = create_agent()
