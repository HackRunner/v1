from pydantic import BaseModel
from fastapi import APIRouter, HTTPException
from app.supabase_client import supabase
from app.logger import LOG_FILE, read_logs
from app.model import generate_mcq
from app.utils import extract_json, validate_mcq
from app.logger import LOG_FILE, read_logs, log_entry  # add log_entry here
router = APIRouter()

BULK_GENERATE_MAX = 20


# ── Request body models ───────────────────────────────────────────────────────

class RegenerateRequest(BaseModel):
    topic: str


class BulkGenerateRequest(BaseModel):
    topic: str
    count: int = 5


# ── Log endpoints ─────────────────────────────────────────────────────────────

@router.get("/logs")
def get_logs():
    return read_logs()


@router.get("/rejected")
def get_rejected():
    return [log for log in read_logs() if log["status"] == "rejected"]


@router.get("/accepted")
def get_accepted():
    """Returns both cleanly accepted and soft-fallback accepted_with_warnings entries."""
    return [
        log for log in read_logs()
        if log["status"] in ("accepted", "accepted_with_warnings")
    ]


@router.get("/warnings")
def get_warnings():
    """Returns only soft-fallback questions that passed with warnings."""
    return [log for log in read_logs() if log["status"] == "accepted_with_warnings"]


@router.get("/stats")
def get_stats():
    logs = read_logs()
    total = len(logs)
    accepted = sum(1 for log in logs if log["status"] == "accepted")
    rejected = sum(1 for log in logs if log["status"] == "rejected")
    warnings = sum(1 for log in logs if log["status"] == "accepted_with_warnings")

    # Count failure reasons
    reason_counts = {}
    for log in logs:
        reason = log.get("reason")
        if reason:
            reason_counts[reason] = reason_counts.get(reason, 0) + 1

    # Sort by frequency descending
    top_reasons = dict(sorted(reason_counts.items(), key=lambda x: x[1], reverse=True))

    # Includes warnings in acceptance rate — consistent with /accepted endpoint
    acceptance_rate = ((accepted + warnings) / total * 100) if total > 0 else 0

    return {
        "total_logs": total,
        "accepted": accepted,
        "rejected": rejected,
        "warnings": warnings,
        "acceptance_rate": round(acceptance_rate, 2),
        "top_failure_reasons": top_reasons
    }


# ── Generation endpoints ──────────────────────────────────────────────────────

@router.post("/regenerate")
def regenerate(req: RegenerateRequest):
    """
    Generate a single raw MCQ and return it alongside its validation result.
    Bypasses the retry loop intentionally — useful for inspecting raw model output.
    """
    raw = generate_mcq(req.topic)
    parsed = extract_json(raw)
    is_valid, reason = validate_mcq(parsed)

    return {
        **parsed,
        "validation": {
            "passed": is_valid,
            "failed_check": reason
        }
    }


@router.post("/bulk-generate")
def bulk_generate(req: BulkGenerateRequest):
    count = min(req.count, BULK_GENERATE_MAX)
    results = []
    from app.supabase_client import supabase  # add this

    for _ in range(count):
        raw = generate_mcq(req.topic)
        parsed = extract_json(raw)
        is_valid, reason = validate_mcq(parsed)

        db_status = "not_saved"

        if is_valid:
            try:
                supabase.table("questions").insert({
                    "topic": req.topic.lower(),
                    "question": parsed.get("question"),
                    "options": parsed.get("options"),
                    "correct_answer": parsed.get("correct_answer"),
                    "explanation": parsed.get("explanation")
                }).execute()
                db_status = "saved"
                log_entry("accepted", req.topic, parsed)         # add this
            except Exception as e:
                db_status = f"db_error: {str(e)}"
                log_entry("rejected", req.topic, parsed, reason="db_error")  # add this
        else:
            log_entry("rejected", req.topic, parsed, reason=reason)  # add this

        results.append({
            **parsed,
            "validation": {"passed": is_valid, "failed_check": reason},
            "db_status": db_status  # add this to response too
        })

    return results

@router.post("/generate-and-store")
def generate_and_store(req: BulkGenerateRequest):
    """
    Generate MCQs and store ONLY valid ones in DB.
    """
    count = min(req.count, BULK_GENERATE_MAX)
    results = []

    from app.supabase_client import supabase

    for _ in range(count):
        raw = generate_mcq(req.topic)
        parsed = extract_json(raw)
        is_valid, reason = validate_mcq(parsed)

        db_status = "not_saved"

        if is_valid:
            try:
                supabase.table("questions").insert({
                    "topic": req.topic.lower(),
                    "question": parsed.get("question"),
                    "options": parsed.get("options"),
                    "correct_answer": parsed.get("correct_answer"),
                    "explanation": parsed.get("explanation")
                }).execute()
                db_status = "saved"
            except Exception as e:
                db_status = f"db_error: {str(e)}"

        results.append({
            **parsed,
            "validation": {
                "passed": is_valid,
                "failed_check": reason
            },
            "db_status": db_status
        })

    return results

@router.get("/feedback")
def get_feedback():
    try:
        res = supabase.table("feedback").select("*").order("created_at", desc=True).execute()
        return res.data
    except Exception:
        raise HTTPException(status_code=500, detail="Failed to fetch feedback")