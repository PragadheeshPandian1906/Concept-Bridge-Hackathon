from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from demo.conceptbridge.db import Store
from demo.conceptbridge.seed import seed_demo

seed_demo(Store(), reset=True)
print("Seeded ConceptBridge demo data.")
