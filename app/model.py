import requests

OLLAMA_URL = "http://localhost:11434/api/generate"

def generate_mcq(topic: str):
    prompt = f"""
You are a cybersecurity MCQ generator.

Generate 1 beginner-level MCQ on: {topic}

RULES:
- Exactly 4 options labeled A, B, C, D
- Only ONE correct answer
- Other options should be clearly incorrect (avoid tricky or partially correct answers)
- Keep the question simple and clear (beginner level)
- Avoid harmful or destructive commands
- Do NOT use placeholders like "..."
- All other options must be clearly incorrect
- All other options must be obviously false in all real-world scenarios

Return ONLY valid JSON:

{{
  "question": "Full question",
  "options": [
    "A. ...",
    "B. ...",
    "C. ...",
    "D. ..."
  ],
  "correct_answer": "A",
  "explanation": "Brief explanation why A is correct"
}}
"""

    response = requests.post(
        OLLAMA_URL,
        json={
            "model": "qwen2.5:3b",
            "prompt": prompt,
            "stream": False
        }
    )

    data = response.json()
    return data["response"]