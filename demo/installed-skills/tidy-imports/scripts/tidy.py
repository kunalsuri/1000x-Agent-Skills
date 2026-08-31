#!/usr/bin/env python3
"""Print a sorted, de-duplicated import block for one Python file."""

import ast
import sys


def imports_of(source: str) -> list:
    lines = set()
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            lines.update(f"import {alias.name}" for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            lines.update(f"from {node.module} import {alias.name}"
                         for alias in node.names)
    return sorted(lines)


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: tidy.py FILE.py", file=sys.stderr)
        return 2
    with open(sys.argv[1], "r", encoding="utf-8") as handle:
        for line in imports_of(handle.read()):
            print(line)
    return 0


if __name__ == "__main__":
    sys.exit(main())
