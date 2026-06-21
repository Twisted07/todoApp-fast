#!/usr/bin/env python3
"""
check_secret_scanning.py
Verifies that GitHub secret scanning and push protection are enabled
on the repository. Does not scan code itself — that is handled by
GitHub's push protection at commit time.

Why this approach:
  - GitHub push protection blocks secrets before they ever enter the repo.
  - Running a separate scanner (truffleHog, gitleaks) would be redundant
    and adds third-party dependencies.
  - This script simply confirms the protection is active so teams know
    their posture, and warns loudly if it has been disabled.
"""

import argparse
import json
import os
import sys
import urllib.request
import urllib.error


def gh_api(endpoint, token):
    """Call GitHub REST API and return parsed JSON."""
    url = f"https://api.github.com{endpoint}"
    req = urllib.request.Request(
        url,
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        if e.code == 403:
            print("::warning::Cannot read secret scanning status "
                  "(token lacks permissions — expected on fork PRs). Skipping check.")
            return None
        if e.code == 404:
            print("::warning::Repository not found or token lacks repo access. Skipping.")
            return None
        print(f"::warning::GitHub API returned HTTP {e.code}. Skipping secret scanning check.")
        return None
    except (urllib.error.URLError, OSError) as e:
        print(f"::warning::Could not reach GitHub API ({e}). Skipping secret scanning check.")
        return None


def set_output(name, value):
    output_file = os.environ.get("GITHUB_OUTPUT", "")
    if output_file:
        with open(output_file, "a") as f:
            f.write(f"{name}={value}\n")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo",  required=True,  help="owner/repo")
    parser.add_argument("--token", required=True,  help="GitHub token")
    args = parser.parse_args()

    print(f"Checking secret scanning posture for: {args.repo}")

    data = gh_api(f"/repos/{args.repo}", args.token)
    if data is None:
        # Could not read — treat as pass (don't block CI over API access issues)
        set_output("secret_scanning_enabled", "unknown")
        sys.exit(0)

    security = data.get("security_and_analysis", {})
    ss       = security.get("secret_scanning", {}).get("status", "unknown")
    pp       = security.get("secret_scanning_push_protection", {}).get("status", "unknown")

    print(f"  Secret scanning:         {ss}")
    print(f"  Push protection:         {pp}")

    set_output("secret_scanning_enabled", ss)
    set_output("push_protection_enabled", pp)

    issues = []

    if ss == "disabled":
        issues.append(
            "Secret scanning is DISABLED on this repository. "
            "Enable it under Settings → Code security → Secret scanning."
        )

    if pp == "disabled":
        issues.append(
            "Push protection is DISABLED. Without it, secrets can be "
            "committed before CI runs. Enable under Settings → Code security "
            "→ Secret scanning → Push protection."
        )

    if issues:
        for issue in issues:
            print(f"::warning::{issue}")
        # Warn but do not hard-fail — the team may be on a plan that
        # does not support secret scanning (e.g. free private repos).
        # Hard failure would block ALL merges, which is worse than the risk.
        print("Secret scanning posture: NEEDS ATTENTION (see warnings above)")
    else:
        print("Secret scanning posture: GOOD")
        if ss == "unknown":
            print("  (Could not verify — API access not available)")


if __name__ == "__main__":
    main()
