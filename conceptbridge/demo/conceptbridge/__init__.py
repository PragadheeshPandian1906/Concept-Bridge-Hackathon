"""ConceptBridge - one-quiz reciprocal peer-match agent.

Deterministic Python owns every number and every transition.
The LLM only explains a match and writes the peer-session plan.

    from demo.conceptbridge.main import run, RunOptions
    ctx = run(RunOptions(stub=True, scenario="success"))
"""

from .schema import State  # noqa: F401

__all__ = ["State"]
__version__ = "0.1.0"
