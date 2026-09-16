"""Preserve missing evidence at the JSON tool boundary."""
from typing import Any


def result_dict(result, evaluator=None) -> dict[str, Any]:
    metadata = dict(result.metadata or {})
    status = ("error" if metadata.get("error_kind") else "skipped" if metadata.get("skipped")
              else "passed" if result.passed else "failed")
    measured = status in {"passed", "failed"}
    return {"score": result.score if measured else None,
            "passed": result.passed if measured else None,
            "status": status, "measured": measured,
            "reason": result.reason, "metadata": metadata,
            "threshold": getattr(evaluator, "threshold", None),
            "evaluator": result.evaluator}
