from fastapi import APIRouter, HTTPException
from app.supabase_client import supabase

router = APIRouter()


# ─────────────────────────────────────────────
# 👥 Get Students
# ─────────────────────────────────────────────

@router.get("/students/{teacher_id}")
def get_students(teacher_id: str):
    try:
        mapping = supabase.table("teacher_students") \
            .select("student_id") \
            .eq("teacher_id", teacher_id) \
            .execute()

        if not mapping.data:
            return []

        student_ids = [m["student_id"] for m in mapping.data]

        students = supabase.table("users") \
            .select("id, name, email") \
            .in_("id", student_ids) \
            .execute()

        return students.data

    except Exception:
        raise HTTPException(status_code=500, detail="Failed to fetch students")


# ─────────────────────────────────────────────
# 🏆 Leaderboard (WITH NAMES)
# ─────────────────────────────────────────────

@router.get("/leaderboard/{teacher_id}")
def leaderboard(teacher_id: str):
    try:
        mapping = supabase.table("teacher_students") \
            .select("student_id") \
            .eq("teacher_id", teacher_id) \
            .execute()

        if not mapping.data:
            return []

        student_ids = [m["student_id"] for m in mapping.data]

        attempts = supabase.table("attempts") \
            .select("*") \
            .in_("student_id", student_ids) \
            .execute()

        scores = {}

        for a in attempts.data:
            sid = a["student_id"]

            if sid not in scores:
                scores[sid] = {"correct": 0, "total": 0}

            scores[sid]["total"] += 1
            if a["is_correct"]:
                scores[sid]["correct"] += 1

        # fetch names
        users = supabase.table("users") \
            .select("id, name") \
            .in_("id", list(scores.keys())) \
            .execute()

        name_map = {u["id"]: u["name"] for u in users.data}

        leaderboard = []

        for sid, data in scores.items():
            accuracy = (data["correct"] / data["total"] * 100) if data["total"] else 0

            leaderboard.append({
                "student_id": sid,
                "name": name_map.get(sid, "Unknown"),
                "accuracy": round(accuracy, 2),
                "attempts": data["total"]
            })

        leaderboard.sort(key=lambda x: x["accuracy"], reverse=True)

        return leaderboard

    except Exception:
        raise HTTPException(status_code=500, detail="Failed to generate leaderboard")


# ─────────────────────────────────────────────
# 📊 Individual Student Stats (WITH NAME)
# ─────────────────────────────────────────────

@router.get("/student/{student_id}")
def student_stats(student_id: str):
    try:
        attempts = supabase.table("attempts") \
            .select("*") \
            .eq("student_id", student_id) \
            .execute()

        data = attempts.data

        total = len(data)
        correct = sum(1 for a in data if a["is_correct"])
        accuracy = (correct / total * 100) if total else 0

        user = supabase.table("users") \
            .select("name") \
            .eq("id", student_id) \
            .execute()

        name = user.data[0]["name"] if user.data else "Unknown"

        return {
            "student_id": student_id,
            "name": name,
            "total_attempts": total,
            "correct_answers": correct,
            "accuracy": round(accuracy, 2)
        }

    except Exception:
        raise HTTPException(status_code=500, detail="Failed to fetch student stats")


# ─────────────────────────────────────────────
# 📚 Topic Stats (optimized)
# ─────────────────────────────────────────────

@router.get("/topic-stats/{teacher_id}")
def topic_stats(teacher_id: str):
    try:
        mapping = supabase.table("teacher_students") \
            .select("student_id") \
            .eq("teacher_id", teacher_id) \
            .execute()

        if not mapping.data:
            return {}

        student_ids = [m["student_id"] for m in mapping.data]

        attempts = supabase.table("attempts") \
            .select("is_correct, question_id") \
            .in_("student_id", student_ids) \
            .execute()

        if not attempts.data:
            return {}

        question_ids = list({a["question_id"] for a in attempts.data})

        questions = supabase.table("questions") \
            .select("id, topic") \
            .in_("id", question_ids) \
            .execute()

        topic_map = {q["id"]: q["topic"] for q in questions.data}

        topic_scores = {}

        for a in attempts.data:
            topic = topic_map.get(a["question_id"])
            if not topic:
                continue

            if topic not in topic_scores:
                topic_scores[topic] = {"correct": 0, "total": 0}

            topic_scores[topic]["total"] += 1
            if a["is_correct"]:
                topic_scores[topic]["correct"] += 1

        result = {}

        for topic, val in topic_scores.items():
            acc = (val["correct"] / val["total"] * 100) if val["total"] else 0
            result[topic] = round(acc, 2)

        return result

    except Exception:
        raise HTTPException(status_code=500, detail="Failed to compute topic stats")
    
@router.get("/feedback")
def get_feedback():
    try:
        res = supabase.table("feedback").select("*").order("created_at", desc=True).execute()
        return res.data
    except Exception:
        raise HTTPException(status_code=500, detail="Failed to fetch feedback")