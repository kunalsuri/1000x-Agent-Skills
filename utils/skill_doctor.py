#!/usr/bin/env python3
"""
Skill Doctor CLI Entrypoint.
Wraps scripts/validate_skills.py for convenient execution from utils/.
"""

import sys
from pathlib import Path

# Add scripts directory to path and execute main
scripts_dir = Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(scripts_dir))

from validate_skills import main

if __name__ == "__main__":
    main()
