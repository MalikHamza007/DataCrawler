from __future__ import annotations


def signal(code: str, label: str, score: int, evidence_ids: list[int] | None = None, **details: object) -> dict:
    return {"code": code, "label": label, "score": score, "direction": "positive" if score > 0 else "negative" if score < 0 else "neutral", "source_evidence_ids": evidence_ids or [], "details": details}


def confidence(score: int, signals: list[dict], high: int = 80, medium: int = 60) -> str:
    if not signals:
        return "insufficient_evidence"
    if score >= high:
        return "high"
    if score >= medium:
        return "medium"
    return "low"


def explanation(signals: list[dict]) -> str:
    if not signals:
        return "No official ownership, portfolio, broker or marketing evidence is available."
    ordered = sorted(signals, key=lambda item: abs(item["score"]), reverse=True)
    return "; ".join(f"{item['label']} ({item['score']:+d})" for item in ordered) + "."
