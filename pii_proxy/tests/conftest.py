import sys
from pathlib import Path

# Add the pii_proxy directory to path so tests can import `app`
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
