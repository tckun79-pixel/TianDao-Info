#!/usr/bin/env python3
"""
TianDao-Info v2.7 — push_to_github.py
Use GitPython to commit all project files and push to GitHub.
Auto-creates the repository via GitHub API if it doesn't exist.
"""

import getpass
import json
import logging
import os
import sys
import urllib.request
import urllib.error
from datetime import datetime
from pathlib import Path

import git

BASE_DIR = Path(__file__).parent.resolve()
LOG_DIR = BASE_DIR / "logs"
LOG_DIR.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_DIR / f"push_to_github_{datetime.now():%Y%m%d}.log", encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger("push_to_github")

REPO_NAME = "TianDao-Info"
REMOTE_URL_TEMPLATE = "https://github.com/{user}/{REPO_NAME}.git"
GITHUB_API_TEMPLATE = "https://api.github.com/user/repos"

RELEVANT_EXTENSIONS = {".py", ".sh", ".md", ".txt", ".json", ".yml", ".yaml", ".env", ".toml"}
RELEVANT_NAMES = {"SPEC.md", "README.md", "requirements.txt", ".env.example",
                  "process_quotes.py", "daily_select.py", "discord_post.py",
                  "dashboard.py", "push_to_github.py", "run_pipeline.sh"}


def get_github_credentials() -> tuple[str, str]:
    token = os.environ.get("GITHUB_TOKEN", "")
    user = os.environ.get("GITHUB_USER", "")
    if not token or not user:
        log.warning("GITHUB_TOKEN / GITHUB_USER not set — will push to existing remote only.")
    return user, token


def create_github_repo(user: str, token: str, repo_name: str, private: bool = True) -> bool:
    """Create GitHub repo via API. Returns True if created or already exists."""
    api_url = GITHUB_API_TEMPLATE.format(user=user)
    payload = json.dumps({
        "name": repo_name,
        "description": "TianDao-Info v2.7 — Chinese Quote Management System",
        "private": private,
        "auto_init": False,
    }).encode("utf-8")

    req = urllib.request.Request(
        api_url,
        data=payload,
        headers={
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github.v3+json",
            "Content-Type": "application/json",
            "User-Agent": "TianDao-Info/2.7",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            if resp.status in (200, 201):
                log.info("GitHub repo '%s' created.", repo_name)
                return True
            body = resp.read().decode("utf-8", errors="replace")
            log.error("Unexpected status creating repo: %d — %s", resp.status, body)
            return False
    except urllib.error.HTTPError as exc:
        if exc.code == 422:  # Already exists
            log.info("Repo '%s' already exists (422).", repo_name)
            return True
        body = exc.read().decode("utf-8", errors="replace")
        log.error("HTTP error creating repo: %d — %s", exc.code, body)
        return False
    except urllib.error.URLError as exc:
        log.error("URL error creating repo: %s", exc.reason)
        return False


def set_remote_url(repo: git.Repo, user: str):
    """Set or update the origin remote URL with credentials."""
    token = os.environ.get("GITHUB_TOKEN", "")
    remote_url = f"https://{user}:{token}@github.com/{user}/{REPO_NAME}.git"
    try:
        repo.remote("origin").set_url(remote_url)
    except ValueError:
        repo.create_remote("origin", remote_url)
    log.info("Remote URL configured for user '%s'.", user)


def get_tracked_files(repo: git.Repo) -> set:
    """Return set of files currently tracked."""
    return {item.b_path for item in repo.index.iter_items()}


def is_relevant(path: str) -> bool:
    """Return True for files we want to commit."""
    p = Path(path)
    if p.name in RELEVANT_NAMES:
        return True
    if p.suffix in RELEVANT_EXTENSIONS:
        return True
    # Data files
    if str(path).startswith("data/"):
        return True
    return False


def commit_all_changes(repo: git.Repo, message: str = None) -> bool:
    """Stage and commit all relevant changed/new files."""
    all_paths = []
    # New untracked files
    for path in repo.untracked_files:
        if is_relevant(path):
            repo.index.add(path)
            all_paths.append(path)

    # Changed tracked files
    diffs = {item.a_path for item in repo.index.diff(None)}  # unstaged changes
    diffs |= {item.a_path for item in repo.index.diff("HEAD")}  # staged changes
    for path in diffs:
        if is_relevant(path):
            repo.index.add(path)
            all_paths.append(path)

    if not all_paths and not repo.is_dirty():
        log.info("Nothing to commit — working tree clean.")
        return False

    if not all_paths:
        log.info("No relevant files changed.")
        return False

    commit_msg = message or f"TianDao-Info v2.7 update — {datetime.now():%Y-%m-%d %H:%M}"
    repo.index.commit(commit_msg)
    log.info("Committed %d file(s): %s", len(all_paths), all_paths)
    return True


def push_to_remote(repo: git.Repo) -> bool:
    """Push to origin."""
    try:
        origin = repo.remote("origin")
    except ValueError:
        log.error("No 'origin' remote configured. Run with GITHUB_USER/GITHUB_TOKEN set.")
        return False

    try:
        origin.push(refspec="main:main", set_upstream=True)
        log.info("Push to origin successful.")
        return True
    except git.exc.GitCommandError as exc:
        log.error("Push failed: %s", exc)
        return False


# ── Main ───────────────────────────────────────────────────────────────────────
def main():
    log.info("=== push_to_github.py v2.7 starting ===")

    user, token = get_github_credentials()

    # Initialise or open repo
    if not (BASE_DIR / ".git").exists():
        log.info("Initializing new Git repo at %s", BASE_DIR)
        repo = git.Repo.init(str(BASE_DIR))
    else:
        repo = git.Repo(str(BASE_DIR))
        log.info("Opened existing repo at %s", BASE_DIR)

    # Auto-create GitHub repo if credentials available
    if user and token:
        create_github_repo(user, token, REPO_NAME, private=True)
        set_remote_url(repo, user)
    else:
        log.info("No GitHub credentials — assuming remote already configured.")

    # Check remote is set
    try:
        remote_url = repo.remote("origin").url
        log.info("Remote origin: %s", remote_url.replace(token, "***") if token else remote_url)
    except ValueError:
        log.warning("No origin remote. Add one manually: git remote add origin <url>")

    if not commit_all_changes(repo):
        log.info("Nothing to commit — exiting.")
        log.info("=== push_to_github.py complete (no-op) ===")
        return

    pushed = push_to_remote(repo)
    if pushed:
        log.info("=== push_to_github.py complete — pushed successfully ===")
    else:
        log.info("=== push_to_github.py complete — commit done, push failed ===")
        sys.exit(1)


if __name__ == "__main__":
    main()
