from typing import Literal
import random

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.supabase_client import supabase

router = APIRouter()


# ─────────────────────────────────────────────
# 📥 Request Models
# ─────────────────────────────────────────────

class QuestionRequest(BaseModel):
    user_id: str
    topic: str


class SubmitRequest(BaseModel):
    user_id: str
    question_id: str
    selected_answer: Literal["A", "B", "C", "D"]


class FeedbackRequest(BaseModel):
    user_id: str
    topic: str
    feedback: str


class JoinClassRequest(BaseModel):
    user_id: str
    class_code: str


# ─────────────────────────────────────────────
# 🧠 Get Question
# ─────────────────────────────────────────────

@router.post("/question")
def get_question(req: QuestionRequest):
    try:
        # 1. Fetch questions from DB (NO LLM)
        res = supabase.table("questions") \
            .select("*") \
            .ilike("topic", f"%{req.topic.lower()}%") \
            .execute()

        if not res.data:
            raise HTTPException(status_code=404, detail="No questions found for this topic")

        # 2. Get attempted questions (NO REPEAT)
        attempted = supabase.table("attempts") \
            .select("question_id") \
            .eq("student_id", req.user_id) \
            .execute()

        attempted_ids = [a["question_id"] for a in attempted.data]

        # 3. Filter unseen questions
        available = [q for q in res.data if q["id"] not in attempted_ids]

        if not available:
            raise HTTPException(status_code=404, detail="No new questions left")

        q = random.choice(available)

        return {
            "question_id": q["id"],
            "question": q["question"],
            "options": q["options"]
        }

    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=500, detail="Failed to fetch question")


# ─────────────────────────────────────────────
# 📤 Submit Answer
# ─────────────────────────────────────────────

@router.post("/submit")
def submit_answer(req: SubmitRequest):
    try:
        q = supabase.table("questions") \
            .select("*") \
            .eq("id", req.question_id) \
            .execute()
    except Exception:
        raise HTTPException(status_code=500, detail="Failed to fetch question")

    if not q.data:
        raise HTTPException(status_code=404, detail="Question not found")

    question = q.data[0]
    correct_answer = question["correct_answer"]
    is_correct = req.selected_answer == correct_answer

    try:
        supabase.table("attempts").insert({
            "student_id": req.user_id,
            "question_id": req.question_id,
            "selected_answer": req.selected_answer,
            "is_correct": is_correct
        }).execute()

    except Exception:
        raise HTTPException(status_code=500, detail="Failed to store attempt")

    return {
        "correct": is_correct,
        "correct_answer": correct_answer,
        "explanation": question["explanation"]
    }


# ─────────────────────────────────────────────
# 🚨 Feedback
# ─────────────────────────────────────────────

@router.post("/feedback")
def give_feedback(req: FeedbackRequest):
    try:
        supabase.table("feedback").insert({
            "student_id": req.user_id,
            "topic": req.topic.lower(),
            "feedback": req.feedback
        }).execute()

        return {"message": "Feedback stored successfully"}

    except Exception:
        raise HTTPException(status_code=500, detail="Failed to store feedback")


# ─────────────────────────────────────────────
# 🔗 Join Class via Code
# ─────────────────────────────────────────────

@router.post("/join-class")
def join_class(req: JoinClassRequest):
    try:
        teacher = supabase.table("users") \
            .select("id") \
            .eq("class_code", req.class_code) \
            .execute()

        if not teacher.data:
            raise HTTPException(status_code=404, detail="Invalid class code")

        teacher_id = teacher.data[0]["id"]

        existing = supabase.table("teacher_students") \
            .select("*") \
            .eq("teacher_id", teacher_id) \
            .eq("student_id", req.user_id) \
            .execute()

        if existing.data:
            return {"message": "Already joined"}

        supabase.table("teacher_students").insert({
            "teacher_id": teacher_id,
            "student_id": req.user_id
        }).execute()

        return {"message": "Joined class successfully", "teacher_id": teacher_id}

    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=500, detail="Join failed")


# ─────────────────────────────────────────────
# 📊 Student Stats (WITH NAME)
# ─────────────────────────────────────────────

@router.get("/stats/{user_id}")
def get_stats(user_id: str):
    try:
        attempts = supabase.table("attempts") \
            .select("*") \
            .eq("student_id", user_id) \
            .execute()

        data = attempts.data

        total = len(data)
        correct = sum(1 for a in data if a["is_correct"])
        accuracy = (correct / total * 100) if total else 0

        user = supabase.table("users") \
            .select("name") \
            .eq("id", user_id) \
            .execute()

        name = user.data[0]["name"] if user.data else "Unknown"

        return {
            "student_id": user_id,
            "name": name,
            "total_attempts": total,
            "correct_answers": correct,
            "accuracy": round(accuracy, 2)
        }

    except Exception:
        raise HTTPException(status_code=500, detail="Failed to fetch stats")