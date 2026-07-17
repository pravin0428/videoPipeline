"""Simple structured logging for the video engine."""
import sys
from datetime import datetime


class Logger:
    """Pipeline logger with module-level tagging."""

    def __init__(self, name: str = ""):
        self.name = name

    def _prefix(self) -> str:
        ts = datetime.now().strftime("%H:%M:%S")
        tag = f"[{self.name}]" if self.name else ""
        return f"{ts} {tag}"

    def info(self, message: str):
        print(f"{self._prefix()} {message}", flush=True)

    def done(self, message: str):
        print(f"{self._prefix()} ✓ {message}", flush=True)

    def warn(self, message: str):
        print(f"{self._prefix()} ⚠ {message}", flush=True)

    def fail(self, message: str):
        print(f"{self._prefix()} ✗ {message}", flush=True)

    def step(self, step_num: int, total: int, label: str):
        print(f"", flush=True)
        print(f"{'─'*50}", flush=True)
        print(f"  Step {step_num}/{total}: {label}", flush=True)
        print(f"{'─'*50}", flush=True)


LOG = Logger()
