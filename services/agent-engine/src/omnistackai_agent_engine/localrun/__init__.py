"""Local run: boot a generated app repo on this machine with one command.

Brick 4 of the front door. The deterministic ``build_run_plan`` is offline-testable; the
opt-in executor lives in ``localrun.run``.
"""

from .plan import RunPlan, RunStep, build_run_plan
from .run import LocalAppRunError, LocalAppSession, start_app

__all__ = [
    "LocalAppRunError",
    "LocalAppSession",
    "RunPlan",
    "RunStep",
    "build_run_plan",
    "start_app",
]
