"""Where the repository is. Tool sets (toolsets/), results (out/) and caches (.cache/) live in the checkout, not in the package."""

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]  # src/repo2tools/paths.py -> the checkout
API_KEY_FILE = REPO_ROOT / ".vllm_api_key"  # local only; never committed, and unreadable from the sandbox
