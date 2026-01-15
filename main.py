#!/usr/bin/env python3
"""
OpenCowork - Open-source Claude Cowork alternative.

Run with: python main.py
"""

import asyncio
import os
import sys
import warnings
from pathlib import Path

# Silence noisy warnings
warnings.filterwarnings("ignore", category=UserWarning, module="pydantic")
warnings.filterwarnings("ignore", category=RuntimeWarning)

from agents import Runner

# Import tools module to set ALLOWED_DIRECTORIES
import tools
from agent import agent, MODEL_ID, BASE_URL, API_KEY
from dotenv import load_dotenv


# =============================================================================
# TOOL LOGGING
# =============================================================================

def get_tool_icon(tool_name: str) -> str:
    """Get icon for tool type."""
    icons = {
        "run_shell": "🔧",
        "fetch_url": "🌐",
        "search_web": "🔍",
    }
    return icons.get(tool_name, "⚡")


def tool_logger(tool_name: str, args: dict) -> None:
    """Log tool calls with their arguments."""
    icon = get_tool_icon(tool_name)

    if tool_name == "run_shell":
        cmd = args.get("command", "")
        # Truncate long commands
        if len(cmd) > 80:
            cmd = cmd[:77] + "..."
        print(f"  {icon} $ {cmd}")
    elif tool_name == "fetch_url":
        url = args.get("url", "")
        print(f"  {icon} GET {url}")
    elif tool_name == "search_web":
        query = args.get("query", "")
        print(f"  {icon} search: {query}")
    else:
        print(f"  {icon} {tool_name}({args})")

# Load environment variables from .env file
load_dotenv()

# Set up tool logging
tools.TOOL_LOGGER = tool_logger


def print_banner():
    """Print welcome banner."""
    print("""
╔═══════════════════════════════════════════════════════════╗
║                      OPENCOWORK                           ║
║         Open-source local task assistant                  ║
╠═══════════════════════════════════════════════════════════╣
║  Commands:                                                ║
║    quit     - Exit OpenCowork                             ║
║    grant    - Grant access to another directory           ║
║    folders  - List granted directories                    ║
╚═══════════════════════════════════════════════════════════╝
""")
    # Show model config
    print(f"🤖 Model: {MODEL_ID}")
    print(f"🔗 Server: {BASE_URL}")
    print()


def grant_folder_access():
    """Prompt user to grant folder access."""
    while True:
        folder = input("\n📁 Grant folder access (path): ").strip()

        if not folder:
            print("No folder specified. Please provide a path.")
            continue

        path = Path(folder).expanduser().resolve()

        if not path.exists():
            print(f"❌ Path does not exist: {path}")
            continue

        if not path.is_dir():
            print(f"❌ Not a directory: {path}")
            continue

        tools.ALLOWED_DIRECTORIES.append(path)
        print(f"✅ Access granted to: {path}")
        return path


async def run_task(task: str) -> str:
    """Run a task through the agent."""
    try:
        result = await Runner.run(agent, task, max_turns=30)
        return result.final_output
    except Exception as e:
        return f"Error: {e}"


async def main():
    """Main entry point."""

    # Check for API key (warn if using default "ollama" with non-local URL)
    if API_KEY == "ollama" and "localhost" not in BASE_URL and "127.0.0.1" not in BASE_URL:
        print("⚠️  Warning: OPENCOWORK_API_KEY not set for remote endpoint")
        print()

    print_banner()

    # Grant initial folder access
    working_dir = grant_folder_access()
    print(f"\n🚀 OpenCowork ready. Working directory: {working_dir}")
    print("Type your task and press Enter. Type 'quit' to exit.\n")

    # Main loop
    while True:
        try:
            task = input("📋 Task: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\n\nGoodbye! 👋")
            break

        if not task:
            continue

        # Handle commands
        if task.lower() == "quit":
            print("\nGoodbye! 👋")
            break

        if task.lower() == "grant":
            grant_folder_access()
            continue

        if task.lower() == "folders":
            print("\n📂 Granted directories:")
            for d in tools.ALLOWED_DIRECTORIES:
                print(f"   - {d}")
            print()
            continue

        # Run the task
        print("\n⏳ Working on it...\n")
        result = await run_task(task)
        print(f"\n📝 Result:\n{result}\n")
        print("-" * 60)


if __name__ == "__main__":
    asyncio.run(main())
