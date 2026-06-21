#!/usr/bin/env python3
"""
validate_config.py
Validates pipeline.config.yml before any pipeline stage runs.
Called automatically at the start of every workflow.
Exits with code 1 and a clear error message if validation fails.
"""

import sys
import os

try:
    import yaml
except ImportError:
    print("::error::PyYAML not found. Run: pip install pyyaml")
    sys.exit(1)


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

SUPPORTED_LANGUAGES = {"node", "python", "java", "go", "csharp", "php"}

# Suggested current stable versions per language — used in validator hints
VERSION_HINTS = {
    "node":   "e.g. '24', '20', '18'",
    "python": "e.g. '3.12', '3.11'",
    "java":   "e.g. '21', '17'",
    "go":     "e.g. '1.22', '1.21'",
    "csharp": "e.g. '8.0', '7.0'  (dotnet SDK version)",
    "php":    "e.g. '8.3', '8.2'",
}
SUPPORTED_TARGETS   = {"vercel", "railway", "heroku", "render", "custom"}

REQUIRED_SECRETS = {
    "vercel":   ["VERCEL_TOKEN", "VERCEL_ORG_ID", "VERCEL_PROJECT_ID"],
    "railway":  ["RAILWAY_TOKEN"],
    "heroku":   ["HEROKU_API_KEY"],
    "render":   ["RENDER_API_KEY"],
    "custom":   [],
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def error(msg: str):
    """Print a GitHub Actions error annotation and record the failure."""
    print(f"::error::{msg}")
    error.count += 1

error.count = 0


def warn(msg: str):
    print(f"::warning::{msg}")


def load_config(path: str) -> dict:
    if not os.path.exists(path):
        print(f"::error::pipeline.config.yml not found at: {path}")
        sys.exit(1)
    with open(path) as f:
        try:
            return yaml.safe_load(f) or {}
        except yaml.YAMLError as e:
            print(f"::error::pipeline.config.yml is not valid YAML: {e}")
            sys.exit(1)


def get(cfg: dict, *keys, default=None):
    """Safely traverse nested dict."""
    for key in keys:
        if not isinstance(cfg, dict):
            return default
        cfg = cfg.get(key, default)
        if cfg is None:
            return default
    return cfg


# ---------------------------------------------------------------------------
# Validation rules
# ---------------------------------------------------------------------------

def validate_project(cfg):
    name = get(cfg, "project", "name", default="")
    if not name or name == "my-project":
        warn("project.name is still the default 'my-project'. Consider giving it a real name.")


def validate_runtime(cfg):
    lang    = get(cfg, "runtime", "language", default="")
    version = get(cfg, "runtime", "version", default="")

    if not lang:
        error(
            "runtime.language is required. "
            f"Supported values: {' | '.join(sorted(SUPPORTED_LANGUAGES))}"
        )
    elif lang not in SUPPORTED_LANGUAGES:
        error(
            f"runtime.language '{lang}' is not supported. "
            f"Choose from: {', '.join(sorted(SUPPORTED_LANGUAGES))}"
        )

    if not str(version):
        hint = VERSION_HINTS.get(lang, "check docs for supported versions")
        error(f"runtime.version is required for '{lang}'. {hint}")


def validate_build(cfg):
    install = get(cfg, "build", "install_command", default="")
    if not install:
        error("build.install_command is required. e.g. 'npm ci' or 'pip install -r requirements.txt'")


def validate_test(cfg):
    unit_cmd = get(cfg, "test", "unit_command", default="")
    if not unit_cmd:
        error("test.unit_command is required. e.g. 'npm test' or 'pytest'")

    threshold = get(cfg, "test", "coverage_threshold", default=70)
    if not isinstance(threshold, (int, float)) or not (0 <= threshold <= 100):
        error(f"test.coverage_threshold must be a number between 0 and 100. Got: {threshold!r}")

    if threshold == 0:
        warn("test.coverage_threshold is 0 — coverage gate is disabled. Recommended minimum: 70")


def validate_quality(cfg):
    quality = cfg.get("quality", {})
    if not isinstance(quality, dict):
        error("quality section must be a mapping (key: value pairs)")
        return

    lint = quality.get("lint_strictness", "warn")
    analysis = quality.get("analysis_strictness", "strict")

    if lint not in {"strict", "warn"}:
        error(f"quality.lint_strictness must be 'strict' or 'warn'. Got: {lint!r}")
    if analysis not in {"strict", "warn"}:
        error(f"quality.analysis_strictness must be 'strict' or 'warn'. Got: {analysis!r}")

    exclude = quality.get("exclude_paths", [])
    if not isinstance(exclude, list):
        error("quality.exclude_paths must be a list of path strings")


def validate_deploy(cfg):
    target = get(cfg, "deploy", "target", default="")

    if not target:
        error("deploy.target is required. Supported values: vercel | railway | heroku | custom")
        return

    if target not in SUPPORTED_TARGETS:
        error(f"deploy.target '{target}' is not supported. Choose from: {', '.join(sorted(SUPPORTED_TARGETS))}")
        return

    # Check that the matching section has required fields filled in
    if target == "vercel":
        project_id = get(cfg, "deploy", "vercel", "project_id", default="")
        org_id     = get(cfg, "deploy", "vercel", "org_id", default="")
        if not project_id:
            error("deploy.vercel.project_id is required when target is 'vercel'")
        if not org_id:
            error("deploy.vercel.org_id is required when target is 'vercel'")

    elif target == "railway":
        service_id = get(cfg, "deploy", "railway", "service_id", default="")
        if not service_id:
            error("deploy.railway.service_id is required when target is 'railway'")

    elif target == "render":
        service_id = get(cfg, "deploy", "render", "service_id", default="")
        if not service_id:
            error("deploy.render.service_id is required when target is 'render'. "
                  "Find it in your Render dashboard → service → Settings → Service ID (starts with 'srv-')")

    elif target == "heroku":
        app_name = get(cfg, "deploy", "heroku", "app_name", default="")
        if not app_name:
            error("deploy.heroku.app_name is required when target is 'heroku'")

    elif target == "custom":
        staging_cmd = get(cfg, "deploy", "custom", "staging_command", default="")
        prod_cmd    = get(cfg, "deploy", "custom", "production_command", default="")
        if not staging_cmd and not prod_cmd:
            error("deploy.custom: at least one of staging_command or production_command must be set")

    # Warn about missing required secrets (can't check actual values, just remind)
    required = REQUIRED_SECRETS.get(target, [])
    if required:
        warn(
            f"Make sure these GitHub secrets are set for '{target}' deployments: "
            + ", ".join(required)
        )

    # Production approval
    manual = get(cfg, "deploy", "production", "manual_approval", default=True)
    if manual is False:
        warn("deploy.production.manual_approval is disabled — production will deploy automatically. "
             "This is not recommended for most projects.")


def validate_quality(cfg):
    if not get(cfg, "quality", "enabled", default=True):
        warn("quality.enabled is false — code quality checks are disabled.")
        return

    for field in ("lint_strictness", "analysis_strictness"):
        value = get(cfg, "quality", field, default="")
        if value not in ("strict", "warn"):
            error(
                f"quality.{field} must be 'strict' or 'warn'. Got: {value!r}"
            )

    level = get(cfg, "quality", "analysis_level", default=5)
    if not isinstance(level, int) or not (0 <= level <= 10):
        error("quality.analysis_level must be an integer between 0 and 10.")


def validate_security(cfg):
    fail_on_high = get(cfg, "security", "fail_on_high", default=True)
    if not isinstance(fail_on_high, bool):
        error("security.fail_on_high must be true or false.")

    dep_scan = get(cfg, "security", "dependency_scan", default=True)
    secret   = get(cfg, "security", "secret_detection", default=True)

    if not dep_scan and not secret:
        warn("Both security.dependency_scan and security.secret_detection are disabled. "
             "It is strongly recommended to keep at least one enabled.")


def validate_advanced(cfg):
    timeout = get(cfg, "advanced", "timeout_minutes", default=30)
    if not isinstance(timeout, int) or timeout < 5:
        error(f"advanced.timeout_minutes must be an integer >= 5. Got: {timeout!r}")
    if timeout > 60:
        warn(f"advanced.timeout_minutes is {timeout} — this is high for a lightweight pipeline. "
             "Consider keeping it under 30.")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    config_path = os.environ.get("CONFIG_PATH", "pipeline.config.yml")
    cfg = load_config(config_path)

    print("Validating pipeline.config.yml...")
    print("-" * 50)

    validate_project(cfg)
    validate_runtime(cfg)
    validate_build(cfg)
    validate_test(cfg)
    validate_quality(cfg)
    validate_deploy(cfg)
    validate_advanced(cfg)

    print("-" * 50)

    if error.count > 0:
        print(f"Validation failed with {error.count} error(s). Fix the issues above and re-run.")
        sys.exit(1)
    else:
        print("Validation passed. Pipeline config is valid.")
        # Export key values as GitHub Actions outputs for other steps to consume
        target    = get(cfg, "deploy", "target", default="")
        language  = get(cfg, "runtime", "language", default="")
        version   = get(cfg, "runtime", "version", default="")
        threshold = get(cfg, "test", "coverage_threshold", default=70)
        lint_s    = get(cfg, "quality", "lint_strictness", default="warn")
        analysis_s= get(cfg, "quality", "analysis_strictness", default="strict")
        q_enabled = get(cfg, "quality", "enabled", default=True)

        output_file = os.environ.get("GITHUB_OUTPUT", "")
        if output_file:
            with open(output_file, "a") as f:
                f.write(f"language={language}\n")
                f.write(f"version={version}\n")
                f.write(f"deploy_target={target}\n")
                f.write(f"coverage_threshold={threshold}\n")
                f.write(f"quality_enabled={str(q_enabled).lower()}\n")
                f.write(f"lint_strictness={lint_s}\n")
                f.write(f"analysis_strictness={analysis_s}\n")

        print(f"  language           = {language}")
        print(f"  runtime version    = {version}")
        print(f"  deploy target      = {target}")
        print(f"  coverage gate      = {threshold}%")
        print(f"  quality checks     = {'on' if q_enabled else 'off'}")
        print(f"  lint strictness    = {lint_s}")
        print(f"  analysis strictness= {analysis_s}")


if __name__ == "__main__":
    main()
