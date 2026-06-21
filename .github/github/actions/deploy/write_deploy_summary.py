#!/usr/bin/env python3
"""
write_deploy_summary.py
Writes a deploy summary to the GitHub Actions job summary page.
Visible directly in the Actions UI — no artifact download needed.
"""

import argparse
import datetime
import os


def write_summary(content):
    summary_file = os.environ.get("GITHUB_STEP_SUMMARY", "")
    if summary_file:
        with open(summary_file, "a") as f:
            f.write(content)
    else:
        print(content)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--environment", default="unknown")
    parser.add_argument("--target",      default="unknown")
    parser.add_argument("--status",      default="unknown")
    parser.add_argument("--url",         default="")
    parser.add_argument("--project",     default="project")
    parser.add_argument("--commit",      default="")
    parser.add_argument("--actor",       default="")
    args = parser.parse_args()

    now     = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    commit  = args.commit[:7] if args.commit else "unknown"
    icon    = "✅" if args.status == "success" else "❌"
    env_cap = args.environment.capitalize()

    url_line = (
        f"| URL | [{args.url}]({args.url}) |"
        if args.url else
        "| URL | Not available |"
    )

    repo    = os.environ.get("GITHUB_REPOSITORY", "")
    run_id  = os.environ.get("GITHUB_RUN_ID", "")
    run_url = f"https://github.com/{repo}/actions/runs/{run_id}" if run_id else ""
    run_link = f"[View run]({run_url})" if run_url else ""

    summary = f"""
## {icon} {env_cap} deploy — {args.project}

| Field | Value |
|---|---|
| Status | `{args.status}` |
| Environment | `{args.environment}` |
| Target | `{args.target}` |
| Commit | `{commit}` |
| Triggered by | `{args.actor}` |
{url_line}
| Time | {now} |
| Run | {run_link} |

"""

    if args.status != "success":
        summary += (
            "> ⚠️ Deploy failed. Check the step logs above for details.\n"
            "> Common causes: missing secrets, platform quota exceeded, "
            "build artifact not found.\n\n"
        )

    write_summary(summary)
    print("Deploy summary written.")


if __name__ == "__main__":
    main()
