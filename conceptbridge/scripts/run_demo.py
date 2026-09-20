"""Runs discovery and prints a candidate pool; continue with Swagger to approve/reject."""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from demo.conceptbridge.config import get_settings
from demo.conceptbridge.db import Store
from demo.conceptbridge.orchestrator import Orchestrator
from demo.conceptbridge.seed import seed_demo

settings=get_settings(); store=Store(settings); seed_demo(store,reset=True)
result=Orchestrator(store,settings).run_matching("demo")
print(f"{result['candidate_count']} valid candidates; state={result['current_state']}")
print(f"All combinations considered: {result['generation']['combinations_considered']}")
for candidate in result['candidates'][:5]: print(candidate['id'],candidate['participant_ids'],candidate['score'])
