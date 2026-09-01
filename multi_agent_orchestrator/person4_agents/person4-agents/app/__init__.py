"""
Person 4 — Multi-agent reasoning, risk and synthesis module.

Public surface:

    from app import analyze, analyze_sync
    from app.schemas.models import AnalysisResult, AgentOutput
"""

from app.api import analyze, analyze_sync

__all__ = ["analyze", "analyze_sync"]
__version__ = "1.0.0"
