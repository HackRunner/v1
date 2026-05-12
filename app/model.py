import requests
MODEL_NAME = "qwen2.5:7b"

OLLAMA_URL = "http://localhost:11434/api/generate"

def generate_mcq(topic: str):

    prompt = f"""
You are an AI system that generates high-quality beginner cybersecurity assessment questions.

TASK:
Generate EXACTLY 1 beginner-level multiple-choice cybersecurity question on the topic: "{topic}"

QUESTION REQUIREMENTS:
- Educational and beginner friendly
- Clear and concise wording
- Real-world cybersecurity relevance
- No trick questions
- No ambiguous wording
- No partially correct options
- Only ONE correct answer

OPTION REQUIREMENTS:
- EXACTLY 4 options
- Labels must be A, B, C, D
- Incorrect answers must be clearly incorrect
- Avoid overlapping meanings between options
- Avoid "All of the above"
- Avoid "None of the above"

SAFETY REQUIREMENTS:
- No destructive commands
- No malware instructions
- No illegal hacking guidance
- No dangerous operational details

EXPLANATION REQUIREMENTS:
- Short and factual
- Must directly justify the correct answer
- Must NOT support incorrect options

OUTPUT REQUIREMENTS:
- Return ONLY valid JSON
- Do NOT include markdown
- Do NOT include comments
- Do NOT include extra text

Return JSON in this EXACT format:

{{
  "type": "mcq",
  "difficulty": "beginner",
  "topic": "{topic}",
  "question": "Question text",
  "options": [
    "A. Option",
    "B. Option",
    "C. Option",
    "D. Option"
  ],
  "correct_answer": "A",
  "explanation": "Brief explanation"
}}
"""

    response = requests.post(
        OLLAMA_URL,
        json={
            "model": MODEL_NAME,
            "prompt": prompt,
            "stream": False,
            "temperature": 0.3,
            "options":{
                "num_predict": 300
            }
        }
    )

    data = response.json()
    return data["response"]

def generate_short_answer(topic: str):

    prompt = f"""
You are an AI system that generates high-quality beginner cybersecurity assessment questions.

TASK:
Generate EXACTLY 1 beginner-level short-answer cybersecurity question on the topic: "{topic}"

QUESTION REQUIREMENTS:
- Educational and beginner friendly
- Clear and concise wording
- Real-world cybersecurity relevance
- No ambiguity
- No trick questions

ANSWER REQUIREMENTS:
- Maximum 8 words
- Must be factually correct
- Must be concise
- Must directly answer the question

SAFETY REQUIREMENTS:
- No destructive commands
- No malware instructions
- No illegal hacking guidance

EXPLANATION REQUIREMENTS:
- Short and factual
- Must support the correct answer

OUTPUT REQUIREMENTS:
- Return ONLY valid JSON
- Do NOT include markdown
- Do NOT include comments
- Do NOT include extra text

Return JSON in this EXACT format:

{{
  "type": "short_answer",
  "difficulty": "beginner",
  "topic": "{topic}",
  "question": "Question text",
  "answer": "Correct answer",
  "explanation": "Brief explanation"
}}
"""
    response = requests.post(
        OLLAMA_URL,
        json={
            "model": MODEL_NAME,
            "prompt": prompt,
            "stream": False,
            "temperature": 0.3,
            "options": {
                "num_predict": 200
            }
        }
    )

    data = response.json()


    if "response" not in data:
        raise Exception(f"Ollama error: {data}")

    return data["response"]