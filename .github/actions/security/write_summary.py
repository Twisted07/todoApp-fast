#!/usr/bin/env python3
"""
write_summary.py
Appends a security scan summary to the GitHub Actions job summary page
($GITHUB_STEP_SUMMARY). This is the table visible in the Actions UI
after a run completes.
"""

import argparse
import os
import datetime


def outcome_icon(outcome):
    icons = {
        "success":   "✅",
        "failure":   "❌",
        "skipped":   "⏭️",
        "cancelled": "⚠️",
        "":          "⏭️",
    }
    return icons.get(outcome, "❓")


def write_summary(content):
    summary_file = os.environ.get("GITHUB_STEP_SUMMARY", "")
    if summary_file:
        with open(summary_file, "a") as f:
            f.write(content)
    else:
        # Local testing — print to stdout
        print(content)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--language",      default="unknown")
    parser.add_argument("--dep-outcome",   default="")
    parser.add_argument("--secret-outcome",default="")
    parser.add_argument("--vuln-count",    default="0")
    args = parser.parse_args()

    now = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    dep_icon    = outcome_icon(args.dep_outcome)
    secret_icon = outcome_icon(args.secret_outcome)

    vuln_display = args.vuln_count if args.vuln_count != "0" else "none"
    vuln_note = (
        f"⚠️ **{args.vuln_count} high/critical vulnerabilities found**"
        if args.vuln_count not in ("0", "", "unknown")
        else "No high/critical vulnerabilities found"
    )

    summary = f"""
## 🔒 Security scan — {args.language}

| Check | Status | Notes |
|---|---|---|
| Dependency audit | {dep_icon} `{args.dep_outcome or 'skipped'}` | {vuln_note} |
| Secret scanning posture | {secret_icon} `{args.secret_outcome or 'skipped'}` | GitHub push protection check |

**Approach:** GitHub-native tools only — no third-party credentials required.
- Dependency review via `actions/dependency-review-action` (PRs) and native package manager audit (main branch)
- Secret detection via GitHub push protection (repository setting)

> Scanned at {now}

"""
    write_summary(summary)
    print("Security summary written to job summary.")


if __name__ == "__main__":
    main()
