#!/usr/bin/env python3
"""
Pre-Flight Codebase Analyzer CLI.
Scans Python and TypeScript/JavaScript/React codebases using AST and pattern analysis
to detect stack, exported symbols, component definitions, and testing gaps before execution.
"""

import sys
import os
import ast
import re
import json
import argparse
from pathlib import Path
from typing import Dict, List, Any, Optional

IGNORED_DIRS = {
    ".git", ".venv", "venv", "env", "__pycache__", "node_modules",
    "dist", "build", ".next", ".turbo", ".cache", ".pytest_cache",
    ".ruff_cache", ".mypy_cache", ".agents", "coverage", ".coverage"
}

def detect_stack(root: Path) -> Dict[str, Any]:
    """Detects languages, package managers, and frameworks in the target project."""
    stack = {
        "is_python": False,
        "is_typescript": False,
        "is_javascript": False,
        "is_react": False,
        "is_nextjs": False,
        "is_fastapi": False,
        "is_flask": False,
        "is_django": False,
        "is_node_backend": False,
        "python_frameworks": [],
        "js_frameworks": [],
        "suggested_runner": "unknown",
        "existing_test_runner": None,
        "has_tests_dir": False,
    }

    # Check files
    pyproject = root / "pyproject.toml"
    setup_py = root / "setup.py"
    reqs = root / "requirements.txt"
    pkg_json = root / "package.json"
    tsconfig = root / "tsconfig.json"
    tests_dir = root / "tests"
    test_dir_alt = root / "test"

    if tests_dir.exists() or test_dir_alt.exists():
        stack["has_tests_dir"] = True

    # Python stack check
    has_py = pyproject.exists() or setup_py.exists() or reqs.exists() or any(root.glob("*.py")) or any(p.suffix == ".py" for p in root.rglob("*.py") if not any(d in p.parts for d in IGNORED_DIRS))
    if has_py:
        stack["is_python"] = True
        stack["suggested_runner"] = "pytest"

        # Check existing runner configs
        if (root / "pytest.ini").exists() or (root / "conftest.py").exists() or (root / "tox.ini").exists():
            stack["existing_test_runner"] = "pytest"
        elif pyproject.exists():
            content = pyproject.read_text(encoding="utf-8", errors="ignore")
            if "[tool.pytest" in content:
                stack["existing_test_runner"] = "pytest"

        # Check framework hints
        combined_text = ""
        for p in [pyproject, reqs, setup_py]:
            if p.exists():
                combined_text += p.read_text(encoding="utf-8", errors="ignore") + "\n"

        if "fastapi" in combined_text.lower():
            stack["is_fastapi"] = True
            stack["python_frameworks"].append("FastAPI")
        if "flask" in combined_text.lower():
            stack["is_flask"] = True
            stack["python_frameworks"].append("Flask")
        if "django" in combined_text.lower():
            stack["is_django"] = True
            stack["python_frameworks"].append("Django")

    # JS/TS stack check
    has_ts = tsconfig.exists() or any(root.glob("*.ts")) or any(root.glob("*.tsx")) or any(p.suffix in {".ts", ".tsx"} for p in root.rglob("*.ts*") if not any(d in p.parts for d in IGNORED_DIRS))
    has_js = pkg_json.exists() or any(root.glob("*.js")) or any(root.glob("*.jsx")) or any(p.suffix in {".js", ".jsx"} for p in root.rglob("*.js*") if not any(d in p.parts for d in IGNORED_DIRS))
    
    if has_ts or has_js:
        if has_ts:
            stack["is_typescript"] = True
        else:
            stack["is_javascript"] = True

        if pkg_json.exists():
            try:
                pkg_data = json.loads(pkg_json.read_text(encoding="utf-8", errors="ignore"))
                deps = {**pkg_data.get("dependencies", {}), **pkg_data.get("devDependencies", {})}
                
                if "react" in deps:
                    stack["is_react"] = True
                    stack["js_frameworks"].append("React")
                if "next" in deps:
                    stack["is_nextjs"] = True
                    stack["is_react"] = True
                    stack["js_frameworks"].append("Next.js")
                if "express" in deps or "fastify" in deps or "koa" in deps:
                    stack["is_node_backend"] = True
                    stack["js_frameworks"].append("Express/Node")
                
                if "vitest" in deps:
                    stack["existing_test_runner"] = "vitest"
                    stack["suggested_runner"] = "vitest"
                elif "jest" in deps:
                    stack["existing_test_runner"] = "jest"
                    stack["suggested_runner"] = "jest"
                else:
                    stack["suggested_runner"] = "vitest" if (stack["is_typescript"] or stack["is_react"]) else "jest"
            except Exception:
                stack["suggested_runner"] = "vitest" if stack["is_typescript"] else "jest"

    return stack

def analyze_python_file(file_path: Path) -> Dict[str, Any]:
    """Analyzes a Python file via AST to extract classes, functions, and async methods."""
    result = {
        "file": str(file_path),
        "classes": [],
        "functions": [],
        "async_functions": [],
        "endpoints": [],
        "has_main": False
    }

    try:
        content = file_path.read_text(encoding="utf-8", errors="ignore")
        tree = ast.parse(content, filename=str(file_path))

        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                methods = [m.name for m in node.body if isinstance(m, (ast.FunctionDef, ast.AsyncFunctionDef)) and not m.name.startswith("_")]
                result["classes"].append({"name": node.name, "methods": methods, "line": node.lineno})
            elif isinstance(node, ast.AsyncFunctionDef):
                if not any(isinstance(parent, ast.ClassDef) for parent in ast.walk(tree) if node in getattr(parent, 'body', [])):
                    result["async_functions"].append({"name": node.name, "line": node.lineno})
            elif isinstance(node, ast.FunctionDef):
                # Check decorators for API endpoints (FastAPI/Flask)
                decorators = []
                for dec in node.decorator_list:
                    if isinstance(dec, ast.Call) and isinstance(dec.func, ast.Attribute):
                        decorators.append(dec.func.attr)
                    elif isinstance(dec, ast.Attribute):
                        decorators.append(dec.attr)
                
                if any(d in {"get", "post", "put", "delete", "patch", "route"} for d in decorators):
                    result["endpoints"].append({"name": node.name, "methods": decorators, "line": node.lineno})
                elif not node.name.startswith("_"):
                    result["functions"].append({"name": node.name, "line": node.lineno})

            elif isinstance(node, ast.If):
                # Check for if __name__ == '__main__':
                if isinstance(node.test, ast.Compare):
                    left = getattr(node.test.left, "id", None)
                    if left == "__name__":
                        result["has_main"] = True
    except Exception:
        pass

    return result

def analyze_ts_js_file(file_path: Path) -> Dict[str, Any]:
    """Analyzes TypeScript/JavaScript/React file using regex scanning for exports and components."""
    result = {
        "file": str(file_path),
        "components": [],
        "functions": [],
        "hooks": [],
        "classes": [],
        "routes": []
    }

    try:
        content = file_path.read_text(encoding="utf-8", errors="ignore")
        
        # Detect React Components (PascalCase exported functions/consts)
        component_matches = re.findall(
            r'export\s+(?:default\s+)?(?:function|const)\s+([A-Z][A-Za-z0-9_]*)\s*(?:=|:|\()', 
            content
        )
        for comp in set(component_matches):
            result["components"].append(comp)

        # Detect Custom Hooks (useSomething)
        hook_matches = re.findall(
            r'export\s+(?:function|const)\s+(use[A-Z][A-Za-z0-9_]*)\s*(?:=|:|\()', 
            content
        )
        for hook in set(hook_matches):
            result["hooks"].append(hook)

        # Detect Regular Exported Functions (camelCase)
        func_matches = re.findall(
            r'export\s+(?:async\s+)?function\s+([a-z][A-Za-z0-9_]*)\s*\(', 
            content
        )
        const_func_matches = re.findall(
            r'export\s+const\s+([a-z][A-Za-z0-9_]*)\s*=\s*(?:async\s*)?\([^)]*\)\s*=>', 
            content
        )
        for fn in set(func_matches + const_func_matches):
            if not fn.startswith("use"):
                result["functions"].append(fn)

        # Detect API routes (express / next.js)
        route_matches = re.findall(
            r'(?:app|router)\.(get|post|put|delete|patch)\s*\(\s*[\'"`]([^\'"`]+)', 
            content
        )
        for method, path in route_matches:
            result["routes"].append(f"{method.upper()} {path}")
            
    except Exception:
        pass

    return result

def find_existing_tests(root: Path) -> List[Path]:
    """Finds all existing test files in the codebase."""
    test_files = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in IGNORED_DIRS]
        for f in filenames:
            if (f.startswith("test_") and f.endswith(".py")) or \
               (f.endswith("_test.py")) or \
               (f.endswith(".test.ts") or f.endswith(".spec.ts")) or \
               (f.endswith(".test.tsx") or f.endswith(".spec.tsx")) or \
               (f.endswith(".test.js") or f.endswith(".spec.js")) or \
               (f.endswith(".test.jsx") or f.endswith(".spec.jsx")):
                test_files.append(Path(dirpath) / f)
    return test_files

def run_analysis(target_dir: Path) -> Dict[str, Any]:
    """Runs a complete static scan and test mapping of the target project."""
    stack = detect_stack(target_dir)
    source_analysis = {
        "python_modules": [],
        "ts_js_modules": [],
    }
    
    existing_tests = find_existing_tests(target_dir)
    existing_test_names = {t.name for t in existing_tests}

    # Scan source files
    for dirpath, dirnames, filenames in os.walk(target_dir):
        dirnames[:] = [d for d in dirnames if d not in IGNORED_DIRS and not d.startswith("test")]
        for f in filenames:
            p = Path(dirpath) / f
            rel = p.relative_to(target_dir)
            if f.endswith(".py") and not f.startswith("test_") and not f.endswith("_test.py"):
                res = analyze_python_file(p)
                res["rel_path"] = str(rel).replace("\\", "/")
                expected_test_name = f"test_{p.stem}.py"
                res["has_test"] = expected_test_name in existing_test_names
                res["suggested_test_path"] = f"tests/unit/test_{p.stem}.py"
                source_analysis["python_modules"].append(res)
                
            elif (f.endswith(".ts") or f.endswith(".tsx") or f.endswith(".js") or f.endswith(".jsx")) and \
                 not (".test." in f or ".spec." in f):
                res = analyze_ts_js_file(p)
                res["rel_path"] = str(rel).replace("\\", "/")
                ext = p.suffix
                expected_test_ts = f"{p.stem}.test{ext}"
                expected_spec_ts = f"{p.stem}.spec{ext}"
                res["has_test"] = (expected_test_ts in existing_test_names or expected_spec_ts in existing_test_names)
                category = "components" if res["components"] else "unit"
                res["suggested_test_path"] = f"tests/{category}/{p.stem}.test{ext}"
                source_analysis["ts_js_modules"].append(res)

    # Compute test gap summary
    total_py = len(source_analysis["python_modules"])
    covered_py = sum(1 for m in source_analysis["python_modules"] if m["has_test"])
    total_ts = len(source_analysis["ts_js_modules"])
    covered_ts = sum(1 for m in source_analysis["ts_js_modules"] if m["has_test"])

    recommendations = []
    if stack["is_python"]:
        if not (target_dir / "tests" / "conftest.py").exists():
            recommendations.append("Generate tests/conftest.py with hermetic fixtures and mock helpers.")
        if not (target_dir / "pytest.ini").exists() and not (target_dir / "pyproject.toml").exists():
            recommendations.append("Configure pytest runner settings (testpaths = ['tests']).")
        if total_py > covered_py:
            recommendations.append(f"Scaffold missing unit tests for {total_py - covered_py} Python modules.")

    if stack["is_typescript"] or stack["is_javascript"]:
        if stack["is_react"]:
            recommendations.append("Scaffold tests/components/ with React Testing Library and user-event harness.")
        if not (target_dir / "tests" / "setup.ts").exists():
            recommendations.append("Generate tests/setup.ts for global mock isolation and DOM cleanup.")
        if total_ts > covered_ts:
            recommendations.append(f"Scaffold missing tests for {total_ts - covered_ts} TS/JS modules.")

    recommendations.append("Generate tests/smoke/ pre-flight sanity test for import graph validation.")

    return {
        "target_dir": str(target_dir.resolve()).replace("\\", "/"),
        "stack": stack,
        "metrics": {
            "total_python_modules": total_py,
            "tested_python_modules": covered_py,
            "python_test_coverage_ratio": f"{covered_py}/{total_py}",
            "total_ts_js_modules": total_ts,
            "tested_ts_js_modules": covered_ts,
            "ts_js_test_coverage_ratio": f"{covered_ts}/{total_ts}",
            "existing_test_files_count": len(existing_tests)
        },
        "existing_tests": [str(t.relative_to(target_dir)).replace("\\", "/") for t in existing_tests],
        "source_analysis": source_analysis,
        "recommendations": recommendations
    }

def print_report(data: Dict[str, Any]):
    stack = data["stack"]
    metrics = data["metrics"]
    
    print("=" * 72)
    print(" 🔍 [PRE-FLIGHT ANALYZER] Codebase Architecture & Test Audit")
    print("=" * 72)
    print(f" Target: {data['target_dir']}")
    
    # Stack display
    detected = []
    if stack["is_python"]:
        detected.append(f"Python ({', '.join(stack['python_frameworks']) if stack['python_frameworks'] else 'Core'})")
    if stack["is_typescript"]:
        detected.append(f"TypeScript ({', '.join(stack['js_frameworks']) if stack['js_frameworks'] else 'Node/Core'})")
    elif stack["is_javascript"]:
        detected.append(f"JavaScript ({', '.join(stack['js_frameworks']) if stack['js_frameworks'] else 'Node/Core'})")
    
    print(f" Detected Stack : {', '.join(detected) if detected else 'Unknown'}")
    print(f" Test Runner    : Suggested '{stack['suggested_runner']}' (Configured: {stack['existing_test_runner'] or 'None'})")
    print(f" Existing Tests : {metrics['existing_test_files_count']} test files found")
    
    if stack["is_python"]:
        print(f" Python Coverage: {metrics['python_test_coverage_ratio']} modules mapped to tests")
    if stack["is_typescript"] or stack["is_javascript"]:
        print(f" TS/JS Coverage : {metrics['ts_js_test_coverage_ratio']} modules mapped to tests")

    print("-" * 72)
    print(" 📋 [UNTESTED MODULES & TEST MAPPING]")
    
    untested_count = 0
    for mod in data["source_analysis"]["python_modules"]:
        if not mod["has_test"]:
            untested_count += 1
            funcs = len(mod["functions"]) + len(mod["async_functions"])
            classes = len(mod["classes"])
            print(f"  [PY] {mod['rel_path']} ({classes} classes, {funcs} functions) -> {mod['suggested_test_path']}")

    for mod in data["source_analysis"]["ts_js_modules"]:
        if not mod["has_test"]:
            untested_count += 1
            comps = len(mod["components"])
            funcs = len(mod["functions"])
            print(f"  [TS] {mod['rel_path']} ({comps} components, {funcs} functions) -> {mod['suggested_test_path']}")

    if untested_count == 0:
        print("  ✨ All discovered source modules have matching test files!")

    print("-" * 72)
    print(" 🚀 [RECOMMENDED ACTIONS]")
    for rec in data["recommendations"]:
        print(f"  • {rec}")
    print("=" * 72)

def main():
    if sys.stdout.encoding != 'utf-8':
        try:
            sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        except Exception:
            pass

    parser = argparse.ArgumentParser(description="Analyze codebase structure and test gaps before running.")
    parser.add_argument("--target-dir", type=str, default=".", help="Target repository directory (default: current dir).")
    parser.add_argument("--json", action="store_true", help="Output analysis in JSON format.")
    args = parser.parse_args()

    target = Path(args.target_dir).resolve()
    if not target.exists():
        print(f"[ERROR] Target directory '{target}' does not exist.", file=sys.stderr)
        sys.exit(1)

    analysis = run_analysis(target)

    if args.json:
        print(json.dumps(analysis, indent=2))
    else:
        print_report(analysis)

if __name__ == "__main__":
    main()
