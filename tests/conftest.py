import sys
from pathlib import Path

# The app is flat modules at the repo root, not an installed package.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
