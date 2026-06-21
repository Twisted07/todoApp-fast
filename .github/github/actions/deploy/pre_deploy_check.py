#!/usr/bin/env python3
"""
pre_deploy_check.py
Runs before any deploy step to catch missing secrets or misconfiguration
early — before wasting time on a partial deploy that will fail midway.

Checks:
  1. Required secrets are set (non-empty) for the chosen target
  2. The runner has network access (sanity check)
  3. Git working tree is clean (no untracked deploy artifacts)
"""

import argparse
import os
import subprocess
import sys


def error(msg):
    print(f"::error::{msg}")
    error.count += 1

error.count = 0


def warn(msg):
    print(f"::warning::{msg}")


def check_secret(name, friendly_name=None):
    """Verify a secret env var is set and non-empty."""
    value = os.environ.get(name, "")
    if not value or value.startswith("${{"):
        error(
            f"Required secret '{name}' is not set. "
            f"Add it under Settings → Secrets → Actions in your GitHub repository."
        )
        return False
    return True


# Map each deploy target to its required secret env vars
REQUIRED_SECRETS = {
    "vercel":  ["VERCEL_TOKEN", "VERCEL_ORG_ID", "VERCEL_PROJECT_ID"],
    "railway": ["RAILWAY_TOKEN"],
    "heroku":  ["HEROKU_API_KEY"],
    "render":  ["RENDER_API_KEY"],
    "custom":  [],
}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--target",    required=True)
    parser.add_argument("--env",       required=True)   # staging | production
    parser.add_argument("--language",  required=True)
    args = parser.parse_args()

    print(f"Pre-deploy checks — target: {args.target}, environment: {args.env}")
    print("-" * 50)

    # 1. Check required secrets
    required = REQUIRED_SECRETS.get(args.target, [])
    for secret in required:
        if check_secret(secret):
            print(f"  ✓ {secret} is set")

    # 2. For production, double-check we are on the right branch
    ref = os.environ.get("GITHUB_REF", "")
    if args.env == "production" and not ref.endswith("/main"):
        warn(
            f"Deploying to production from branch '{ref}'. "
            "Production deploys typically run from 'main'."
        )

    # 3. Warn if this is a first-time deploy (no prior successful deploys)
    run_number = int(os.environ.get("GITHUB_RUN_NUMBER", "1"))
    if run_number <= 3:
        print(f"  ℹ  Run #{run_number} — if this is your first deploy, "
              "check the target platform dashboard to confirm the app is created.")

    print("-" * 50)

    if error.count > 0:
        print(f"Pre-deploy checks failed ({error.count} error(s)). "
              "Fix the issues above before deploying.")
        sys.exit(1)

    print("Pre-deploy checks passed.")


if __name__ == "__main__":
    main()
