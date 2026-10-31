#!/usr/bin/env python3
"""
README scaffolder.

Writes the shortest README that still answers a reader's four questions:
what is this, how do I run it, where is the rest, and what may I do with it.
Everything else is left out on purpose -- a template that ships a hero
banner, a badge wall and a diagram placeholder gets filled in rather than
deleted, and the result is a 700-line README nobody reads to the end.

The output is meant to be edited down, not up. It is scored by
audit_readme.py, the rubric this skill grades against.
"""

import sys
import argparse
from pathlib import Path


def generate_readme_content(name: str, tagline: str, description: str,
                            author: str, license_name: str) -> str:
    slug_name = name.lower().replace(" ", "-")
    return f"""# {name}

{tagline}. {description}

## Install

```bash
npm install {slug_name}
```

Replace this with the one command a reader needs. If installing takes more
than one command, the extra steps belong under a `## Setup` heading below --
not in front of this one.

## Usage

```bash
{slug_name} --help
```

Show what it prints. Real output is the cheapest proof the thing works:

```text
usage: {slug_name} [--help]
```

## How it works

Two or three paragraphs, at most. Anything longer belongs in `docs/` with a
link from here -- a README is the doorway, not the manual.

## Contributing

```bash
# run the tests
make test
```

Say how a change gets tested and sent. Link a CONTRIBUTING file once one
exists.

## License

{license_name}. Maintained by {author}.
"""


def main():
    if sys.stdout.encoding != 'utf-8':
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')

    parser = argparse.ArgumentParser(
        description="Scaffold a short, readable README.md.")
    parser.add_argument("--name", default="My Awesome Project", help="Project name.")
    parser.add_argument("--tagline", default="A tool that does one thing well", help="One-line description of what it is.")
    parser.add_argument("--description", default="Replace this sentence with what the project does and who it is for.", help="Project description.")
    parser.add_argument("--author", default="Project Author", help="Author name.")
    parser.add_argument("--license", default="Apache 2.0", help="License name (e.g. Apache 2.0, MIT).")
    parser.add_argument("--output", default="README.md", help="Output file path.")
    parser.add_argument("--overwrite", action="store_true", help="Overwrite existing output file if it exists.")
    args = parser.parse_args()

    out_path = Path(args.output).resolve()
    if out_path.exists() and not args.overwrite:
        print(f"[ERROR] Target file '{out_path}' already exists. Pass --overwrite to replace it.")
        sys.exit(1)

    content = generate_readme_content(
        name=args.name,
        tagline=args.tagline,
        description=args.description,
        author=args.author,
        license_name=args.license
    )

    out_path.write_text(content, encoding="utf-8")
    print(f"[SUCCESS] Wrote {len(content.splitlines())} lines to {out_path}. "
          f"Edit it down, not up.")

if __name__ == "__main__":
    main()
