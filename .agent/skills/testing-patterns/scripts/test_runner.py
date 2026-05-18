#!/usr/bin/env python3
"""
Test Runner - Unified test execution and coverage reporting
Runs tests and generates coverage report based on project type.

Usage:
    python test_runner.py <project_path> [--coverage]

Supports:
    - Node.js: npm test, jest, vitest
    - Python: pytest, unittest
"""

import subprocess
import sys
import json
from pathlib import Path
from datetime import datetime

# Fix Windows console encoding
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except:
    pass


def detect_test_framework(project_path: Path) -> dict:
    """Detect test framework and commands."""
    result = {"type": "unknown", "framework": None, "cmd": None, "coverage_cmd": None}

    # Node.js project
    package_json = project_path / "package.json"
    if package_json.exists():
        result["type"] = "node"
        try:
            pkg = json.loads(package_json.read_text(encoding="utf-8"))
            scripts = pkg.get("scripts", {})
            deps = {**pkg.get("dependencies", {}), **pkg.get("devDependencies", {})}

            # Check for test script
            if "test" in scripts:
                result["framework"] = "npm test"
                result["cmd"] = ["npm", "test"]

                # Try to detect specific framework for coverage
                if "vitest" in deps:
                    result["framework"] = "vitest"
                    result["coverage_cmd"] = ["npx", "vitest", "run", "--coverage"]
                elif "jest" in deps:
                    result["framework"] = "jest"
                    result["coverage_cmd"] = ["npx", "jest", "--coverage"]
            elif "vitest" in deps:
                result["framework"] = "vitest"
                result["cmd"] = ["npx", "vitest", "run"]
                result["coverage_cmd"] = ["npx", "vitest", "run", "--coverage"]
            elif "jest" in deps:
                result["framework"] = "jest"
                result["cmd"] = ["npx", "jest"]
                result["coverage_cmd"] = ["npx", "jest", "--coverage"]

        except:
            pass

    # Python project
    if (project_path / "pyproject.toml").exists() or (
        project_path / "requirements.txt"
    ).exists():
        result["type"] = "python"
        result["framework"] = "pytest"
        
        py_cmd = "python"
        venv_python = project_path / "venv" / "Scripts" / "python.exe"
        if venv_python.exists():
            py_cmd = str(venv_python)

        result["cmd"] = [py_cmd, "-m", "pytest", "-v"]
        result["coverage_cmd"] = [
            py_cmd,
            "-m",
            "pytest",
            "--cov",
            "--cov-report=term-missing",
        ]

    return result


def run_tests(cmd: list, cwd: Path) -> dict:
    """Run tests and return results."""
    result = {
        "passed": False,
        "output": "",
        "error": "",
        "tests_run": 0,
        "tests_passed": 0,
        "tests_failed": 0,
    }

    try:
        proc = subprocess.run(
            cmd,
            cwd=str(cwd),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=300,  # 5 min timeout for tests
        )

        output = proc.stdout or ""
        stderr = proc.stderr or ""

        # Fallback inteligente para unittest caso pytest não esteja instalado ou não encontre testes
        if proc.returncode != 0 and ("No module named pytest" in stderr or "No module named pytest" in output or "no tests ran" in output or proc.returncode == 5):
            print("\n⚠️  Pytest não encontrou testes ou não está disponível. Usando fallback para o módulo standard 'unittest'...")
            fallback_cmd = [cmd[0], "-m", "unittest", "discover", "tests"]
            proc = subprocess.run(
                fallback_cmd,
                cwd=str(cwd),
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=300,
            )
            output = proc.stdout or ""
            stderr = proc.stderr or ""
            result["passed"] = proc.returncode == 0
            
            # Conta testes executados pelo unittest (ex: "Ran 36 tests in X.XXs")
            import re
            match = re.search(r"Ran\s+(\d+)\s+test", stderr)
            if match:
                result["tests_run"] = int(match.group(1))
                if "OK" in stderr:
                    result["tests_passed"] = result["tests_run"]
                else:
                    # Encontra quantidade de falhas/erros
                    failures = 0
                    match_fail = re.search(r"FAILED\s+\((?:failures=(\d+))?,?\s*(?:errors=(\d+))?\)", stderr)
                    if match_fail:
                        f_count = match_fail.group(1)
                        e_count = match_fail.group(2)
                        failures = (int(f_count) if f_count else 0) + (int(e_count) if e_count else 0)
                    result["tests_failed"] = failures
                    result["tests_passed"] = result["tests_run"] - failures

        else:
            result["passed"] = proc.returncode == 0

        result["output"] = output[:3000]
        result["error"] = stderr[:500]

        # Try to parse test counts from output (Se usou pytest)
        if "pytest" in str(cmd) and not result["tests_run"]:
            import re
            match = re.search(r"(\d+)\s+passed", output)
            if match:
                result["tests_passed"] = int(match.group(1))
            match = re.search(r"(\d+)\s+failed", output)
            if match:
                result["tests_failed"] = int(match.group(1))
            result["tests_run"] = result["tests_passed"] + result["tests_failed"]

    except FileNotFoundError:
        result["error"] = f"Command not found: {cmd[0]}"
    except subprocess.TimeoutExpired:
        result["error"] = "Timeout after 300s"
    except Exception as e:
        result["error"] = str(e)

    return result


def main():
    project_path = Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()
    with_coverage = "--coverage" in sys.argv

    print(f"\n{'='*60}")
    print("[TEST RUNNER] Unified Test Execution")
    print(f"{'='*60}")
    print(f"Project: {project_path}")
    print(f"Coverage: {'enabled' if with_coverage else 'disabled'}")
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # Detect test framework
    test_info = detect_test_framework(project_path)
    print(f"Type: {test_info['type']}")
    print(f"Framework: {test_info['framework']}")
    print("-" * 60)

    if not test_info["cmd"]:
        print("No test framework found for this project.")
        output = {
            "script": "test_runner",
            "project": str(project_path),
            "type": test_info["type"],
            "framework": None,
            "passed": True,
            "message": "No tests configured",
        }
        print(json.dumps(output, indent=2))
        sys.exit(0)

    # Choose command
    cmd = (
        test_info["coverage_cmd"]
        if with_coverage and test_info["coverage_cmd"]
        else test_info["cmd"]
    )

    print(f"Running: {' '.join(cmd)}")
    print("-" * 60)

    # Run tests
    result = run_tests(cmd, project_path)

    # Print output (truncated)
    if result["output"]:
        lines = result["output"].split("\n")
        for line in lines[:30]:
            print(line)
        if len(lines) > 30:
            print(f"... ({len(lines) - 30} more lines)")

    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)

    if result["passed"]:
        print("[PASS] All tests passed")
    else:
        print("[FAIL] Some tests failed")
        if result["error"]:
            print(f"Error: {result['error'][:200]}")

    if result["tests_run"] > 0:
        print(
            f"Tests: {result['tests_run']} total, {result['tests_passed']} passed, {result['tests_failed']} failed"
        )

    output = {
        "script": "test_runner",
        "project": str(project_path),
        "type": test_info["type"],
        "framework": test_info["framework"],
        "tests_run": result["tests_run"],
        "tests_passed": result["tests_passed"],
        "tests_failed": result["tests_failed"],
        "passed": result["passed"],
    }

    print("\n" + json.dumps(output, indent=2))

    sys.exit(0 if result["passed"] else 1)


if __name__ == "__main__":
    main()
