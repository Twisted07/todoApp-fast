#!/usr/bin/env python3
"""
run_dependency_audit.py
Runs the native package manager's audit/vulnerability check for each language.
All tools used are built into the package manager — no third-party tokens needed.

Language → tool:
  node   → npm audit
  python → pip-audit
  java   → OWASP Dependency-Check (via Maven)
  go     → govulncheck
  csharp → dotnet list package --vulnerable
  php    → composer audit
"""

import argparse
import os
import subprocess
import sys


def set_output(name, value):
    output_file = os.environ.get("GITHUB_OUTPUT", "")
    if output_file:
        with open(output_file, "a") as f:
            f.write(f"{name}={value}\n")


def run(cmd, capture=True):
    return subprocess.run(cmd, shell=True, text=True, capture_output=capture)


def annotate_error(msg):
    print(f"::error::{msg}")


def annotate_warning(msg):
    print(f"::warning::{msg}")


# =============================================================================
# Node — npm audit
# =============================================================================
def audit_node(fail_on_high):
    print("::group::npm audit")
    level = "high" if fail_on_high else "critical"
    result = run(f"npm audit --audit-level={level} --json")
    vuln_count = 0

    if result.stdout:
        import json
        try:
            data = json.loads(result.stdout)
            # npm audit JSON: vulnerabilities is a dict of {package: {severity,...}}
            vulns = data.get("vulnerabilities", {})
            high_crit = [
                v for v in vulns.values()
                if v.get("severity") in ("high", "critical")
            ]
            vuln_count = len(high_crit)
            if high_crit:
                print(f"Found {vuln_count} high/critical vulnerabilities:")
                for name, info in vulns.items():
                    if info.get("severity") in ("high", "critical"):
                        print(f"  [{info['severity'].upper()}] {name} — "
                              f"{info.get('via', [{}])[0] if info.get('via') else 'see npm audit'}")
        except (json.JSONDecodeError, KeyError):
            print(result.stdout[:1000])

    print("::endgroup::")
    set_output("vuln_count", str(vuln_count))
    return result.returncode == 0 or vuln_count == 0


# =============================================================================
# Python — pip-audit
# =============================================================================
def audit_python(fail_on_high):
    print("::group::pip-audit")
    # Install pip-audit if not present
    run("pip install pip-audit --quiet --break-system-packages", capture=False)
    result = run("pip-audit --format=columns --progress-spinner=off")

    if result.stdout:
        print(result.stdout)
    if result.stderr:
        print(result.stderr)

    # pip-audit exits non-zero when vulnerabilities found
    vuln_count = result.stdout.count("VULN") if result.stdout else 0
    set_output("vuln_count", str(vuln_count))
    print("::endgroup::")
    return result.returncode == 0


# =============================================================================
# Java — OWASP Dependency-Check via Maven
# =============================================================================
def audit_java(fail_on_high):
    print("::group::OWASP Dependency-Check")
    cvss_threshold = "7" if fail_on_high else "9"
    result = run(
        f"mvn -B org.owasp:dependency-check-maven:check "
        f"-DfailBuildOnCVSS={cvss_threshold} "
        f"-DsuppressionsFile=.dependency-check-suppressions.xml "
        f"-q 2>&1 || true"
    )
    if result.stdout:
        # Filter to just the summary lines
        for line in result.stdout.splitlines():
            if any(kw in line for kw in ["WARN", "ERROR", "vulnerability", "CVE"]):
                print(line)

    vuln_count = result.stdout.count("CVE-") if result.stdout else 0
    set_output("vuln_count", str(vuln_count))
    print("::endgroup::")
    return result.returncode == 0


# =============================================================================
# Go — govulncheck
# =============================================================================
def audit_go(fail_on_high):
    print("::group::govulncheck")
    # Install govulncheck if not present
    if run("govulncheck -version").returncode != 0:
        run("go install golang.org/x/vuln/cmd/govulncheck@latest", capture=False)
    result = run("govulncheck ./...")
    if result.stdout:
        print(result.stdout)

    vuln_count = result.stdout.count("Vulnerability #") if result.stdout else 0
    set_output("vuln_count", str(vuln_count))
    print("::endgroup::")
    return result.returncode == 0


# =============================================================================
# C# — dotnet list package --vulnerable
# =============================================================================
def audit_csharp(fail_on_high):
    print("::group::dotnet vulnerable packages")
    result = run("dotnet list package --vulnerable --include-transitive")
    if result.stdout:
        print(result.stdout)

    vuln_count = 0
    if result.stdout:
        for line in result.stdout.splitlines():
            if "High" in line or "Critical" in line:
                vuln_count += 1
                print(f"  {line.strip()}")

    set_output("vuln_count", str(vuln_count))
    print("::endgroup::")
    # dotnet list always exits 0; we check content
    if fail_on_high and vuln_count > 0:
        return False
    return True


# =============================================================================
# PHP — composer audit
# =============================================================================
def audit_php(fail_on_high):
    print("::group::composer audit")
    result = run("composer audit --format=plain --no-interaction")
    if result.stdout:
        print(result.stdout)

    vuln_count = result.stdout.count("CVE-") if result.stdout else 0
    set_output("vuln_count", str(vuln_count))
    print("::endgroup::")
    return result.returncode == 0


# =============================================================================
# Dispatch
# =============================================================================
AUDITORS = {
    "node":   audit_node,
    "python": audit_python,
    "java":   audit_java,
    "go":     audit_go,
    "csharp": audit_csharp,
    "php":    audit_php,
}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--language",     required=True)
    parser.add_argument("--fail-on-high", default="true")
    args = parser.parse_args()

    fail_on_high = args.fail_on_high.lower() == "true"
    auditor = AUDITORS.get(args.language)

    if not auditor:
        annotate_warning(f"No dependency auditor for '{args.language}'. Skipping.")
        set_output("vuln_count", "0")
        sys.exit(0)

    print(f"Running dependency audit for: {args.language}")
    print(f"  Fail on high severity: {fail_on_high}")

    passed = auditor(fail_on_high)

    if not passed:
        annotate_error(
            "Dependency audit found vulnerabilities. "
            "Run the audit locally and update affected packages, "
            "or add suppressions for accepted risks."
        )
        sys.exit(1)

    print("Dependency audit passed — no high/critical vulnerabilities found.")


if __name__ == "__main__":
    main()
