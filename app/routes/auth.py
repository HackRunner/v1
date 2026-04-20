from typing import Literal

from fastapi import APIRouter, HTTPException
from gotrue.errors import AuthApiError
from pydantic import BaseModel

from app.supabase_client import supabase

router = APIRouter()


class SignupRequest(BaseModel):
    email: str
    password: str
    role: Literal["student", "teacher", "developer"]  # rejects any other value with 422
    name: str

class LoginRequest(BaseModel):
    email: str
    password: str


@router.post("/signup")
def signup(req: SignupRequest):
    # Step 1: Create user in Supabase Auth
    try:
        auth_res = supabase.auth.sign_up({
            "email": req.email,
            "password": req.password
        })
    except AuthApiError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    user = auth_res.user
    if not user:
        raise HTTPException(status_code=400, detail="Signup failed — no user returned")

    # Step 2: Insert role into users table
    # Kept separate so a DB failure doesn't get confused with an auth failure.
    # Note: if this fails, an orphaned auth user may exist — monitor 500s here.
    try:
        supabase.table("users").insert({
            "id": user.id,
            "email": req.email,
            "role": req.role,
            "name": req.name
        }).execute()
    except Exception as e:
        # Auth user was created but profile insert failed — log clearly
        raise HTTPException(
            status_code=500,
            detail=f"User auth created but profile insert failed: {str(e)}"
        )

    return {
        "message": "User created",
        "user_id": user.id,
        "role": req.role
    }


@router.post("/login")
def login(req: LoginRequest):
    # Step 1: Authenticate credentials
    try:
        res = supabase.auth.sign_in_with_password({
            "email": req.email,
            "password": req.password
        })
    except AuthApiError as e:
        # Credential failure — correct to return 401
        raise HTTPException(status_code=401, detail="Invalid credentials")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))  # temporarily

    user = res.user
    session = res.session

    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    # Step 2: Check session (e.g. email confirmation may be required)
    if not session:
        raise HTTPException(status_code=403, detail="Email confirmation required")

    # Step 3: Fetch role from users table
    try:
        user_data = supabase.table("users") \
            .select("*") \
            .eq("id", user.id) \
            .execute()
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to fetch user profile")

    # Guard against missing profile row
    if not user_data.data:
        raise HTTPException(status_code=404, detail="User profile not found")

    role = user_data.data[0]["role"]

    return {
        "user_id": user.id,
        "email": user.email,
        "role": role,
        "access_token": session.access_token
    }