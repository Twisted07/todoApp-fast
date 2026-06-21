#!/usr/bin/env python3
"""
generate_report.py
Generates a self-contained HTML report combining:
  - Test results (unit + integration pass/fail)
  - Coverage percentage vs threshold
  - Code quality findings
Uploaded as a pipeline artifact on every run.
"""

import argparse
import datetime
import os
import sys


def badge(label, value, status):
    """Return an inline HTML badge."""
    colors = {
        "pass":    ("#1D9E75", "#E1F5EE"),
        "fail":    ("#D85A30", "#FAECE7"),
        "warn":    ("#BA7517", "#FAEEDA"),
        "skip":    ("#888780", "#F1EFE8"),
        "unknown": ("#888780", "#F1EFE8"),
    }
    text_color, bg_color = colors.get(status, colors["unknown"])
    return (
        f'<span style="display:inline-block;padding:2px 10px;border-radius:12px;'
        f'font-size:12px;font-weight:500;background:{bg_color};color:{text_color};'
        f'border:1px solid {text_color}33">{label}: {value}</span>'
    )


def outcome_to_status(outcome):
    mapping = {
        "success": "pass",
        "failure": "fail",
        "skipped": "skip",
        "cancelled": "skip",
        "": "skip",
    }
    return mapping.get(outcome, "unknown")


def coverage_status(pct_str, threshold):
    if pct_str == "unknown":
        return "unknown"
    try:
        pct = float(pct_str)
        return "pass" if pct >= threshold else "fail"
    except ValueError:
        return "unknown"


def overall_status(unit, coverage_st):
    if unit == "fail" or coverage_st == "fail":
        return ("FAILED", "#D85A30", "#FAECE7")
    if unit == "skip":
        return ("UNKNOWN", "#888780", "#F1EFE8")
    return ("PASSED", "#1D9E75", "#E1F5EE")


def generate_html(args):
    unit_st    = outcome_to_status(args.unit_outcome)
    integ_st   = outcome_to_status(args.integration_outcome)
    cov_st     = coverage_status(args.coverage_pct, float(args.threshold))

    overall_label, overall_color, overall_bg = overall_status(unit_st, cov_st)

    now = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    commit = os.environ.get("GITHUB_SHA", "unknown")[:7]
    repo   = os.environ.get("GITHUB_REPOSITORY", "unknown")
    run_id = os.environ.get("GITHUB_RUN_ID", "")
    run_url = (
        f"https://github.com/{repo}/actions/runs/{run_id}" if run_id else "#"
    )

    cov_display = (
        f"{args.coverage_pct}%" if args.coverage_pct != "unknown" else "n/a"
    )

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Pipeline report — {repo}</title>
<style>
  *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    font-size: 14px; line-height: 1.6;
    background: #f8f7f4; color: #2c2c2a;
    padding: 32px 24px;
  }}
  .card {{
    background: #fff; border: 1px solid #e0ddd6;
    border-radius: 12px; padding: 24px;
    margin-bottom: 20px; max-width: 760px; margin-left: auto; margin-right: auto;
  }}
  h1 {{ font-size: 20px; font-weight: 500; margin-bottom: 4px; }}
  h2 {{ font-size: 15px; font-weight: 500; margin-bottom: 16px; color: #444; }}
  .meta {{ font-size: 12px; color: #888; margin-bottom: 20px; }}
  .meta a {{ color: #3B6D11; text-decoration: none; }}
  .overall {{
    display: inline-block; padding: 6px 20px; border-radius: 20px;
    font-size: 15px; font-weight: 500;
    background: {overall_bg}; color: {overall_color};
    border: 1.5px solid {overall_color}44;
    margin-bottom: 20px;
  }}
  table {{ width: 100%; border-collapse: collapse; margin-top: 8px; }}
  th {{ text-align: left; font-size: 11px; font-weight: 500;
        text-transform: uppercase; letter-spacing: .05em;
        color: #888; padding: 6px 12px; border-bottom: 1px solid #eee; }}
  td {{ padding: 10px 12px; border-bottom: 1px solid #f0ede8; font-size: 13px; }}
  tr:last-child td {{ border-bottom: none; }}
  .section-title {{ font-size: 13px; font-weight: 500; color: #555;
                    margin-bottom: 10px; margin-top: 4px; }}
  .tip {{
    background: #F1EFE8; border-left: 3px solid #B4B2A9;
    padding: 10px 14px; border-radius: 0 8px 8px 0;
    font-size: 12px; color: #5F5E5A; margin-top: 16px;
  }}
</style>
</head>
<body>

<div class="card">
  <h1>Pipeline report</h1>
  <div class="meta">
    <b>{repo}</b> &nbsp;·&nbsp; commit <code>{commit}</code>
    &nbsp;·&nbsp; {now}
    &nbsp;·&nbsp; <a href="{run_url}" target="_blank">view run ↗</a>
  </div>
  <div class="overall">{overall_label}</div>
</div>

<div class="card">
  <h2>Test results</h2>
  <table>
    <thead><tr><th>Check</th><th>Status</th><th>Notes</th></tr></thead>
    <tbody>
      <tr>
        <td>Unit tests</td>
        <td>{badge("unit", args.unit_outcome or "skipped", unit_st)}</td>
        <td></td>
      </tr>
      <tr>
        <td>Integration tests</td>
        <td>{badge("integration", args.integration_outcome or "skipped", integ_st)}</td>
        <td>{"Skipped — no integration_command set" if not args.integration_outcome else ""}</td>
      </tr>
      <tr>
        <td>Coverage</td>
        <td>{badge("coverage", cov_display, cov_st)}</td>
        <td>Threshold: {args.threshold}%</td>
      </tr>
    </tbody>
  </table>
</div>

<div class="card">
  <h2>Coverage</h2>
  <div style="display:flex;align-items:center;gap:16px;margin-bottom:12px">
    <div style="flex:1;background:#f0ede8;border-radius:8px;height:14px;overflow:hidden">
      <div style="
        height:100%;
        width:{min(float(args.coverage_pct), 100) if args.coverage_pct != 'unknown' else 0}%;
        background:{'#1D9E75' if cov_st == 'pass' else '#D85A30'};
        border-radius:8px;
        transition:width .4s ease">
      </div>
    </div>
    <span style="font-size:18px;font-weight:500;color:{'#1D9E75' if cov_st == 'pass' else '#D85A30'}">
      {cov_display}
    </span>
  </div>
  <div style="font-size:12px;color:#888">
    Language: <b>{args.language}</b> &nbsp;·&nbsp;
    Report path: <code>{args.coverage_path}</code> &nbsp;·&nbsp;
    Required: <b>{args.threshold}%</b>
  </div>
  {"" if cov_st != "fail" else
    '<div class="tip">Coverage is below threshold. Add tests to untested code paths, or lower <code>coverage_threshold</code> in <code>pipeline.config.yml</code> if the threshold is too strict for this project stage.</div>'}
</div>

<div class="card">
  <h2>Code quality</h2>
  <div class="section-title">Check the pipeline run logs for detailed lint and analysis findings.</div>
  <div style="font-size:12px;color:#888">
    Tools run for <b>{args.language}</b>:
    {get_tools_description(args.language)}
  </div>
  <div class="tip">
    Findings are annotated inline on your pull request. Set
    <code>lint_strictness: strict</code> in <code>pipeline.config.yml</code>
    to make quality issues block merging.
  </div>
</div>

<div class="card" style="font-size:12px;color:#aaa;text-align:center;border:none;background:none;padding:8px">
  Generated by lightweight-devops-pipeline &nbsp;·&nbsp; {now}
</div>

</body>
</html>"""

    return html


def get_tools_description(language):
    tools = {
        "node":   "ESLint (lint)",
        "python": "Flake8 (lint) + Pylint (analysis)",
        "java":   "Checkstyle (lint) + SpotBugs (analysis)",
        "go":     "golangci-lint (lint) + go vet (analysis)",
        "csharp": "dotnet-format (lint) + Roslyn analyzers (analysis)",
        "php":    "PHP_CodeSniffer (lint) + PHPStan (analysis)",
    }
    return tools.get(language, "see pipeline logs")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--language",             default="unknown")
    parser.add_argument("--coverage-path",        default="coverage/")
    parser.add_argument("--coverage-pct",         default="unknown")
    parser.add_argument("--threshold",            default="70")
    parser.add_argument("--unit-outcome",         default="")
    parser.add_argument("--integration-outcome",  default="")
    parser.add_argument("--output",               default="pipeline-report.html")
    args = parser.parse_args()

    html = generate_html(args)
    with open(args.output, "w") as f:
        f.write(html)

    print(f"HTML report written to: {args.output}")


if __name__ == "__main__":
    main()


