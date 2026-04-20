from pydantic import BaseModel
from typing import List

class TopicRequest(BaseModel):
    topic: str

class MCQResponse(BaseModel):
    question: str
    options: List[str]
    correct_answer: str
    explanation: str