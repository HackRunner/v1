from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from app.routes import dev, student, teacher, auth
from dotenv import load_dotenv
load_dotenv()

app = FastAPI(title="HackRunner API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:8000",
        "http://localhost:8000"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(dev.router, prefix="/dev", tags=["Developer"])
app.include_router(auth.router, prefix="/auth", tags=["Auth"])
app.include_router(student.router, prefix="/student", tags=["Student"])
app.include_router(teacher.router, prefix="/teacher", tags=["Teacher"])

@app.get("/")
def serve_ui():
    return FileResponse("templates/index.html")
