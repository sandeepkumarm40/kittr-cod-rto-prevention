"""
Upload all project files to GitHub repository using GitHub API.
No local Git installation required.

Usage:
  python upload_to_github.py <YOUR_GITHUB_TOKEN>
"""
import os
import sys
import base64
import json
import urllib.request
from pathlib import Path

REPO_OWNER = "sandeepkumarm40"
REPO_NAME = "kittr-cod-rto-prevention"
ROOT_DIR = Path(__file__).parent.resolve()

EXCLUDE_DIRS = {".git", "__pycache__", ".pytest_cache", ".venv", "venv", ".idea", ".vscode"}
EXCLUDE_FILES = {"upload_to_github.py"}

def upload_file(rel_path, token):
    full_path = ROOT_DIR / rel_path
    with open(full_path, "rb") as f:
        content_b64 = base64.b64encode(f.read()).decode("utf-8")

    api_url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/contents/{rel_path.replace(os.sep, '/')}"

    # Check if file already exists to get its SHA (needed for update)
    sha = None
    try:
        check_req = urllib.request.Request(api_url, headers={
            "Authorization": f"Bearer {token}",
            "User-Agent": "UploadScript"
        })
        with urllib.request.urlopen(check_req) as resp:
            data = json.loads(resp.read().decode())
            sha = data.get("sha")
    except urllib.error.HTTPError as e:
        if e.code != 404:
            print(f"  Warning checking {rel_path}: {e}")

    payload = {
        "message": f"Upload {rel_path.replace(os.sep, '/')}",
        "content": content_b64,
        "branch": "main"
    }
    if sha:
        payload["sha"] = sha

    req = urllib.request.Request(
        api_url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "User-Agent": "UploadScript",
            "Content-Type": "application/json"
        },
        method="PUT"
    )

    try:
        with urllib.request.urlopen(req) as resp:
            if resp.status in (200, 201):
                print(f"  [OK] {rel_path}")
            else:
                print(f"  [HTTP {resp.status}] {rel_path}")
    except Exception as e:
        print(f"  [ERROR] {rel_path}: {e}")

def main():
    if len(sys.argv) < 2:
        print("Usage: python upload_to_github.py <GITHUB_TOKEN>")
        print("Get a token from: https://github.com/settings/tokens (classic token with 'repo' scope)")
        sys.exit(1)

    token = sys.argv[1].strip()
    print(f"Uploading files to {REPO_OWNER}/{REPO_NAME}...")

    uploaded_count = 0
    for root, dirs, files in os.walk(ROOT_DIR):
        dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]
        for f in files:
            if f in EXCLUDE_FILES:
                continue
            full = Path(root) / f
            rel = full.relative_to(ROOT_DIR)
            rel_str = str(rel)
            upload_file(rel_str, token)
            uploaded_count += 1

    print(f"\nDone! Uploaded {uploaded_count} files to GitHub.")

if __name__ == "__main__":
    main()
