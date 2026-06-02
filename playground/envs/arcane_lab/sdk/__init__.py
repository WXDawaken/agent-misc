from .result import StepResult
from .server_sdk import ArcaneLabServerSDK

__all__ = ["ArcaneLabSDK", "ArcaneLabServerSDK", "StepResult"]


def __getattr__(name: str):
    if name == "ArcaneLabSDK":
        from .arcane_lab_sdk import ArcaneLabSDK

        return ArcaneLabSDK
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
