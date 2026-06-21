#!/usr/bin/env python3
"""
check_coverage.py
Parses the coverage report produced by each language's coverage tool,
extracts the overall percentage, and fails the step if below threshold.
Outputs: coverage percentage as a GitHub Actions step output.
"""

import argparse
import os
import sys
import glob
import json
import xml.etree.ElementTree as ET


def set_output(name, value):
    output_file = os.environ.get("GITHUB_OUTPUT", "")
    if output_file:
        with open(output_file, "a") as f:
            f.write(f"{name}={value}\n")
    print(f"  {name} = {value}")


def parse_lcov(report_path):
    """Parse lcov.info — used by Node (istanbul/c8) and Go."""
    pattern = os.path.join(report_path, "**", "lcov.info")
    files = glob.glob(pattern, recursive=True)
    if not files:
        # Also try direct lcov.info at root
        if os.path.exists("coverage.out"):
            return parse_go_cover("coverage.out")
        return None

    hit, total = 0, 0
    with open(files[0]) as f:
        for line in f:
            if line.startswith("DA:"):
                parts = line.strip().split(",")
                if len(parts) >= 2:
                    total += 1
                    if int(parts[1]) > 0:
                        hit += 1
    return round((hit / total * 100), 1) if total > 0 else None


def parse_go_cover(path="coverage.out"):
    """Parse Go coverage.out format."""
    if not os.path.exists(path):
        return None
    hit, total = 0, 0
    with open(path) as f:
        for line in f:
            if line.startswith("mode:"):
                continue
            parts = line.strip().split()
            if len(parts) >= 3:
                count = int(parts[2])
                stmts = int(parts[1].split(",")[0].split(":")[1])
                total += stmts
                if count > 0:
                    hit += stmts
    return round((hit / total * 100), 1) if total > 0 else None


def parse_cobertura(report_path):
    """Parse Cobertura XML — used by Python (pytest-cov), Java (JaCoCo), C#."""
    patterns = [
        os.path.join(report_path, "**", "coverage.xml"),
        os.path.join(report_path, "**", "cobertura.xml"),
        os.path.join(report_path, "**", "coverage-cobertura.xml"),
        "coverage.xml",
    ]
    xml_file = None
    for pattern in patterns:
        files = glob.glob(pattern, recursive=True)
        if files:
            xml_file = files[0]
            break

    if not xml_file:
        return None

    try:
        tree = ET.parse(xml_file)
        root = tree.getroot()
        line_rate = root.get("line-rate")
        if line_rate:
            return round(float(line_rate) * 100, 1)
    except ET.ParseError:
        pass
    return None


def parse_clover(report_path):
    """Parse Clover XML — used by PHP (phpunit --coverage-clover)."""
    patterns = [
        os.path.join(report_path, "**", "clover.xml"),
        os.path.join(report_path, "**", "coverage.xml"),
        "coverage.xml",
    ]
    for pattern in patterns:
        files = glob.glob(pattern, recursive=True)
        if files:
            try:
                tree = ET.parse(files[0])
                root = tree.getroot()
                metrics = root.find(".//project/metrics")
                if metrics is not None:
                    elements = int(metrics.get("elements", 0))
                    covered = int(metrics.get("coveredelements", 0))
                    if elements > 0:
                        return round((covered / elements * 100), 1)
            except ET.ParseError:
                pass
    return None


def parse_dotnet(report_path):
    """Parse .NET coverage — tries Cobertura XML produced by coverlet."""
    pct = parse_cobertura(report_path)
    if pct is not None:
        return pct
    # Fallback: look for coverage.json (coverlet JSON format)
    json_files = glob.glob(
        os.path.join(report_path, "**", "coverage.json"), recursive=True
    )
    if json_files:
        try:
            with open(json_files[0]) as f:
                data = json.load(f)
            summary = data.get("summary", {})
            if "linecoverage" in summary:
                return round(summary["linecoverage"], 1)
        except (json.JSONDecodeError, KeyError):
            pass
    return None


PARSERS = {
    "node":   parse_lcov,
    "python": parse_cobertura,
    "java":   parse_cobertura,
    "go":     parse_go_cover,
    "csharp": parse_dotnet,
    "php":    parse_clover,
}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--report-path", default="coverage/")
    parser.add_argument("--threshold", type=float, default=70)
    parser.add_argument("--language", required=True)
    args = parser.parse_args()

    parse_fn = PARSERS.get(args.language)
    if not parse_fn:
        print(f"::warning::No coverage parser for language '{args.language}'. Skipping gate.")
        set_output("pct", "unknown")
        sys.exit(0)

    # Go uses a flat file, others take a path
    if args.language == "go":
        pct = parse_fn()
    else:
        pct = parse_fn(args.report_path)

    if pct is None:
        print(f"::warning::Could not parse coverage report at '{args.report_path}'. "
              "Check that your coverage_command is generating a report.")
        set_output("pct", "unknown")
        # Don't hard-fail if report is missing — warn only
        sys.exit(0)

    set_output("pct", str(pct))
    print(f"Coverage: {pct}%  |  Threshold: {args.threshold}%")

    if args.threshold == 0:
        print("Coverage gate disabled (threshold = 0).")
        sys.exit(0)

    if pct < args.threshold:
        print(f"::error::Coverage {pct}% is below the required threshold of {args.threshold}%. "
              "Add more tests or lower coverage_threshold in pipeline.config.yml.")
        sys.exit(1)

    print(f"Coverage gate passed ({pct}% >= {args.threshold}%).")


if __name__ == "__main__":
    main()
