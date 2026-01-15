"""
OpenCowork Tools - Sandboxed shell access and web operations.

Architecture: 3 tools only
- run_shell: Allowlisted shell commands (file ops, search, scripting, git)
- fetch_url: Web content extraction
- search_web: Research queries
"""

import re
import shlex
import subprocess
from pathlib import Path

import httpx
from agents import function_tool

# =============================================================================
# SANDBOX CONFIGURATION
# =============================================================================

ALLOWED_DIRECTORIES: list[Path] = []

# Logging callback - set from main.py to log tool calls
TOOL_LOGGER: callable = None


def log_tool_call(tool_name: str, args: dict) -> None:
    """Log a tool call if logger is set."""
    if TOOL_LOGGER:
        TOOL_LOGGER(tool_name, args)

# Allowlisted base commands (safer than blocklist)
ALLOWED_COMMANDS = {
    # File operations
    "ls", "cat", "head", "tail", "less", "more",
    "cp", "mv", "rm", "mkdir", "rmdir", "touch",
    # Search
    "find", "grep", "rg", "fd", "locate",
    # Text processing
    "sort", "uniq", "wc", "cut", "tr", "sed", "awk", "xargs",
    # Utilities
    "echo", "printf", "date", "stat", "file", "du", "df", "basename", "dirname",
    "true", "false", "test", "[",
    # Scripting (sandboxed to cwd)
    "python", "python3", "bash", "sh",
    # Archive
    "tar", "zip", "unzip", "gzip", "gunzip", "bzip2", "xz",
    # JSON/data
    "jq",
    # Version control
    "git",
    # Diff/patch
    "diff", "patch",
}

# Explicitly blocked patterns (defense in depth)
BLOCKED_PATTERNS = [
    # Privilege escalation
    r"\bsudo\b",
    r"\bsu\b",
    # Network tools (use fetch_url/search_web instead)
    r"\bcurl\b",
    r"\bwget\b",
    r"\bnc\b",
    r"\bnetcat\b",
    r"\bssh\b",
    r"\bscp\b",
    r"\brsync\b",
    # Permission changes
    r"\bchmod\b",
    r"\bchown\b",
    # Process control
    r"\bkill\b",
    r"\bpkill\b",
    r"\bkillall\b",
    # Sensitive system paths
    r"/dev/",
    r"/proc/",
    r"/sys/",
    r"/etc/passwd",
    r"/etc/shadow",
    r"~/.ssh",
    r"\.ssh/",
    # Path traversal attempts
    r"\.\./",           # ../ anywhere
    r"/\.\.",           # /.. anywhere
]


def extract_base_commands(command: str) -> list[str]:
    """Extract all base command names from a shell command string.

    Handles pipes (|), chains (&&, ||, ;), and subshells.
    """
    # Split on pipes and logical operators
    # This is simplified - a full parser would be more robust
    parts = re.split(r'\s*(?:\||&&|\|\||;)\s*', command)

    commands = []
    for part in parts:
        part = part.strip()
        if not part:
            continue

        # Handle command substitution $(...)
        # For safety, we just extract the outer command
        # Inner commands would run in the same sandbox anyway

        # Get the first word (base command)
        try:
            tokens = shlex.split(part)
            if tokens:
                # Handle env vars like VAR=value cmd
                for token in tokens:
                    if '=' not in token or token.startswith('-'):
                        commands.append(token)
                        break
        except ValueError:
            # shlex failed, try simple split
            words = part.split()
            if words:
                commands.append(words[0])

    return commands


def validate_command(command: str) -> tuple[bool, str]:
    """Validate a shell command against allowlist and blocklist.

    Returns (is_valid, error_message).
    """
    # Check blocked patterns first
    for pattern in BLOCKED_PATTERNS:
        if re.search(pattern, command, re.IGNORECASE):
            return False, f"Blocked pattern detected: {pattern}"

    # Extract and validate all base commands
    base_commands = extract_base_commands(command)

    if not base_commands:
        return False, "No command detected"

    for cmd in base_commands:
        # Strip path prefix if present (e.g., /usr/bin/ls -> ls)
        cmd_name = Path(cmd).name

        if cmd_name not in ALLOWED_COMMANDS:
            return False, f"Command not in allowlist: {cmd_name}"

    return True, ""


def validate_paths_in_command(command: str) -> tuple[bool, str]:
    """Check that any absolute paths in the command are within sandbox.

    Returns (is_valid, error_message).
    """
    if not ALLOWED_DIRECTORIES:
        return False, "No directories have been granted access"

    # Find potential absolute paths
    # This is a heuristic - won't catch everything but catches common cases
    path_pattern = r'(?:^|\s)(/[^\s]+)'
    matches = re.findall(path_pattern, command)

    for path_str in matches:
        try:
            path = Path(path_str).resolve()

            # Check if within any allowed directory
            in_sandbox = False
            for allowed in ALLOWED_DIRECTORIES:
                try:
                    if path.is_relative_to(allowed):
                        in_sandbox = True
                        break
                except ValueError:
                    continue

            if not in_sandbox:
                return False, f"Path outside sandbox: {path_str}"

        except (OSError, ValueError):
            # Invalid path, let the shell handle it
            continue

    return True, ""


# =============================================================================
# SHELL TOOL
# =============================================================================

@function_tool
def run_shell(command: str) -> str:
    """Execute a shell command within the sandboxed directory.

    Allowed commands: ls, cat, cp, mv, rm, mkdir, find, grep, sort, sed, awk,
    python, bash, git, tar, zip, jq, and more standard Unix tools.

    Supports pipes (|) and chaining (&&, ||).

    Examples:
    - ls -la
    - find . -name "*.pdf" | head -10
    - mkdir -p images && mv *.jpg images/
    - cat > script.py << 'EOF'
      import os
      print(os.listdir('.'))
      EOF
    - python script.py
    - git status

    Args:
        command: Shell command to execute

    Returns:
        Command output (stdout + stderr)
    """
    log_tool_call("run_shell", {"command": command})

    if not ALLOWED_DIRECTORIES:
        return "Error: No directories have been granted access. Use 'grant' command first."

    # Validate command against allowlist
    is_valid, error = validate_command(command)
    if not is_valid:
        return f"Blocked: {error}\n\nAllowed commands: {', '.join(sorted(ALLOWED_COMMANDS))}"

    # Validate any absolute paths
    is_valid, error = validate_paths_in_command(command)
    if not is_valid:
        return f"Blocked: {error}"

    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=60,
            cwd=str(ALLOWED_DIRECTORIES[0]),
            env={
                **subprocess.os.environ,
                "HOME": str(ALLOWED_DIRECTORIES[0]),  # Sandbox home
            }
        )

        output = result.stdout
        if result.stderr:
            if output:
                output += "\n"
            output += f"[stderr]: {result.stderr}"

        if not output.strip():
            if result.returncode == 0:
                return "Command completed successfully (no output)"
            else:
                return f"Command failed with exit code {result.returncode}"

        # Truncate long output
        if len(output) > 10000:
            output = output[:10000] + f"\n\n... [truncated, {len(output)} chars total]"

        return output

    except subprocess.TimeoutExpired:
        return "Error: Command timed out after 60 seconds"
    except Exception as e:
        return f"Error: {e}"


# =============================================================================
# WEB TOOLS
# =============================================================================

@function_tool
def fetch_url(url: str) -> str:
    """Fetch and extract text content from a URL.

    Useful for reading documentation, articles, or any web content.

    Args:
        url: URL to fetch (must start with http:// or https://)

    Returns:
        Extracted text content from the page
    """
    log_tool_call("fetch_url", {"url": url})

    try:
        from bs4 import BeautifulSoup
    except ImportError:
        return "Error: beautifulsoup4 not installed. Run: pip install beautifulsoup4"

    if not url.startswith(('http://', 'https://')):
        return "Error: URL must start with http:// or https://"

    try:
        headers = {"User-Agent": "Mozilla/5.0 (compatible; OpenCowork/1.0)"}
        response = httpx.get(url, timeout=15, follow_redirects=True, headers=headers)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")

        # Remove non-content elements
        for tag in soup(["script", "style", "nav", "footer", "header", "aside", "form"]):
            tag.decompose()

        # Extract text
        text = soup.get_text(separator="\n", strip=True)

        # Clean up
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        text = "\n".join(lines)

        if len(text) > 8000:
            text = text[:8000] + "\n\n... [truncated]"

        return text

    except httpx.HTTPStatusError as e:
        return f"HTTP Error: {e.response.status_code}"
    except httpx.TimeoutException:
        return "Error: Request timed out"
    except Exception as e:
        return f"Error: {e}"


@function_tool
def search_web(query: str) -> str:
    """Search the web using DuckDuckGo.

    Returns top results with titles, URLs, and snippets.

    Args:
        query: Search query

    Returns:
        Formatted search results
    """
    log_tool_call("search_web", {"query": query})

    try:
        from ddgs import DDGS
    except ImportError:
        return "Error: ddgs not installed. Run: pip install ddgs"

    try:
        results = list(DDGS().text(query, max_results=5))

        if not results:
            return f"No results found for: {query}"

        formatted = []
        for i, r in enumerate(results, 1):
            formatted.append(
                f"{i}. **{r['title']}**\n"
                f"   {r['href']}\n"
                f"   {r.get('body', '')[:200]}"
            )

        return "\n\n".join(formatted)

    except Exception as e:
        return f"Error: {e}"
