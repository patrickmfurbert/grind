from fastapi import APIRouter
from pydantic import BaseModel

from ..services.code_executor import execute

router = APIRouter(prefix="/code", tags=["code"])


class CodeRequest(BaseModel):
    language: str
    code: str


@router.post("/execute")
def run_code(payload: CodeRequest):
    return execute(payload.language, payload.code)
