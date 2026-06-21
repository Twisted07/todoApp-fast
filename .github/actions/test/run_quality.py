#!/usr/bin/env python3
"""
run_quality.py
Installs and runs the appropriate lint and static analysis tools
for each supported language. Respects strictness settings from config.
Outputs GitHub Actions annotations for every finding.
"""

import argparse
import os
import subprocess
import sys


def run(cmd, capture=False, check=False):
    """Run a shell command, optionally capturing output."""
    result = subprocess.run(
        cmd, shell=True, text=True,
        capture_output=capture
    )
    if check and result.returncode != 0:
        sys.exit(result.returncode)
    return result


def annotate_warning(msg):
    print(f"::warning::{msg}")


def annotate_error(msg):
    print(f"::error::{msg}")


def handle_outcome(result, tool_name, strictness):
    """Fail or warn based on strictness setting."""
    if result.returncode != 0:
        output = (result.stdout or "") + (result.stderr or "")
        if strictness == "strict":
            annotate_error(f"{tool_name} found issues (strict mode). Fix before merging.\n{output[:500]}")
            sys.exit(1)
        else:
            annotate_warning(f"{tool_name} found issues (warn mode — not blocking).\n{output[:500]}")


# =============================================================================
# Node — ESLint
# =============================================================================
def run_node(lint_strictness, analysis_strictness, lint_config, **_):
    print("::group::ESLint")
    config_flag = f"--config {lint_config}" if lint_config else ""

    # Install ESLint if not present
    if run("npx eslint --version", capture=True).returncode != 0:
        run("npm install --save-dev eslint", check=True)

    result = run(f"npx eslint . {config_flag} --format=compact", capture=True)
    if result.stdout:
        print(result.stdout)
    handle_outcome(result, "ESLint", lint_strictness)
    print("::endgroup::")


# =============================================================================
# Python — Flake8 + Pylint
# =============================================================================
def run_python(lint_strictness, analysis_strictness, lint_config, analysis_level, **_):
    # Lint: Flake8
    print("::group::Flake8")
    run("pip install flake8 --quiet --break-system-packages")
    config_flag = f"--config {lint_config}" if lint_config else ""
    result = run(f"flake8 . {config_flag} --format=default", capture=True)
    if result.stdout:
        print(result.stdout)
    handle_outcome(result, "Flake8", lint_strictness)
    print("::endgroup::")

    # Analysis: Pylint
    print("::group::Pylint")
    run("pip install pylint --quiet --break-system-packages")
    fail_under = max(0, 10 - int(analysis_level))  # level 5 → fail-under=5
    result = run(
        f"pylint **/*.py --fail-under={fail_under} --output-format=text",
        capture=True
    )
    if result.stdout:
        print(result.stdout)
    handle_outcome(result, "Pylint", analysis_strictness)
    print("::endgroup::")


# =============================================================================
# Java — Checkstyle + SpotBugs (via Maven)
# =============================================================================
def run_java(lint_strictness, analysis_strictness, lint_config, **_):
    # Lint: Checkstyle via Maven
    print("::group::Checkstyle")
    config_flag = (
        f"-Dcheckstyle.config.location={lint_config}" if lint_config
        else "-Dcheckstyle.config.location=google_checks.xml"
    )
    result = run(f"mvn -B checkstyle:check {config_flag} -q", capture=True)
    if result.stdout:
        print(result.stdout)
    handle_outcome(result, "Checkstyle", lint_strictness)
    print("::endgroup::")

    # Analysis: SpotBugs via Maven
    print("::group::SpotBugs")
    result = run("mvn -B spotbugs:check -q", capture=True)
    if result.stdout:
        print(result.stdout)
    handle_outcome(result, "SpotBugs", analysis_strictness)
    print("::endgroup::")


# =============================================================================
# Go — golangci-lint + go vet
# =============================================================================
def run_go(lint_strictness, analysis_strictness, lint_config, **_):
    # Lint: golangci-lint
    print("::group::golangci-lint")
    # Install golangci-lint if not present
    if run("golangci-lint version", capture=True).returncode != 0:
        run(
            "curl -sSfL https://raw.githubusercontent.com/golangci/golangci-lint/"
            "master/install.sh | sh -s -- -b $(go env GOPATH)/bin",
            check=True
        )
    config_flag = f"--config {lint_config}" if lint_config else ""
    result = run(f"golangci-lint run {config_flag}", capture=True)
    if result.stdout:
        print(result.stdout)
    handle_outcome(result, "golangci-lint", lint_strictness)
    print("::endgroup::")

    # Analysis: go vet
    print("::group::go vet")
    result = run("go vet ./...", capture=True)
    if result.stderr:
        print(result.stderr)
    handle_outcome(result, "go vet", analysis_strictness)
    print("::endgroup::")


# =============================================================================
# C# — dotnet format + Roslyn analyzers
# =============================================================================
def run_csharp(lint_strictness, analysis_strictness, lint_config, **_):
    # Lint: dotnet format (verify only — does not modify files)
    print("::group::dotnet format")
    result = run("dotnet format --verify-no-changes --verbosity normal", capture=True)
    if result.stdout:
        print(result.stdout)
    handle_outcome(result, "dotnet format", lint_strictness)
    print("::endgroup::")

    # Analysis: Roslyn analyzers run as part of dotnet build --no-restore
    print("::group::Roslyn analyzers")
    result = run(
        "dotnet build --no-restore --configuration Release "
        "/p:TreatWarningsAsErrors=false /p:RunAnalyzers=true",
        capture=True
    )
    if result.stdout:
        print(result.stdout)
    handle_outcome(result, "Roslyn analyzers", analysis_strictness)
    print("::endgroup::")


# =============================================================================
# PHP — PHP_CodeSniffer + PHPStan
# =============================================================================
def run_php(lint_strictness, analysis_strictness, lint_config, analysis_level, **_):
    # Lint: PHP_CodeSniffer
    print("::group::PHP_CodeSniffer")
    if run("vendor/bin/phpcs --version", capture=True).returncode != 0:
        run("composer require --dev squizlabs/php_codesniffer --no-interaction -q", check=True)
    standard = lint_config if lint_config else "PSR12"
    result = run(f"vendor/bin/phpcs --standard={standard} src/", capture=True)
    if result.stdout:
        print(result.stdout)
    handle_outcome(result, "PHP_CodeSniffer", lint_strictness)
    print("::endgroup::")

    # Analysis: PHPStan
    print("::group::PHPStan")
    if run("vendor/bin/phpstan --version", capture=True).returncode != 0:
        run("composer require --dev phpstan/phpstan --no-interaction -q", check=True)
    result = run(
        f"vendor/bin/phpstan analyse src/ --level={analysis_level} --no-progress",
        capture=True
    )
    if result.stdout:
        print(result.stdout)
    handle_outcome(result, "PHPStan", analysis_strictness)
    print("::endgroup::")


# =============================================================================
# Dispatch
# =============================================================================
RUNNERS = {
    "node":   run_node,
    "python": run_python,
    "java":   run_java,
    "go":     run_go,
    "csharp": run_csharp,
    "php":    run_php,
}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--language",             required=True)
    parser.add_argument("--lint-strictness",      default="warn")
    parser.add_argument("--analysis-strictness",  default="warn")
    parser.add_argument("--lint-config",          default="")
    parser.add_argument("--analysis-level",       default="5")
    args = parser.parse_args()

    runner = RUNNERS.get(args.language)
    if not runner:
        print(f"::warning::No quality runner for '{args.language}'. Skipping.")
        sys.exit(0)

    print(f"Running code quality checks for: {args.language}")
    print(f"  Lint strictness:     {args.lint_strictness}")
    print(f"  Analysis strictness: {args.analysis_strictness}")
    runner(
        lint_strictness=args.lint_strictness,
        analysis_strictness=args.analysis_strictness,
        lint_config=args.lint_config,
        analysis_level=args.analysis_level,
    )
    print("Code quality checks complete.")


if __name__ == "__main__":
    main()
