from typing import Any, Optional, Dict
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, field_validator


class CaseCreateSchema(BaseModel):
    title: str = Field(..., min_length=3, max_length=150)
    description: Optional[str] = Field(default="", max_length=2000)
    investigator: str = Field(..., min_length=2, max_length=100)
    status: Optional[str] = Field(default="Open")

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str) -> str:
        valid_statuses = {"Open", "Under Analysis", "Review", "Closed"}
        if v not in valid_statuses:
            raise ValueError(f"Status must be one of {valid_statuses}")
        return v


class CaseUpdateSchema(BaseModel):
    title: Optional[str] = Field(None, min_length=3, max_length=150)
    description: Optional[str] = None
    investigator: Optional[str] = Field(None, min_length=2, max_length=100)
    status: Optional[str] = None

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            valid_statuses = {"Open", "Under Analysis", "Review", "Closed"}
            if v not in valid_statuses:
                raise ValueError(f"Status must be one of {valid_statuses}")
        return v


class ChatQuerySchema(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000)


def api_response(
    success: bool = True,
    data: Any = None,
    error: Optional[Dict[str, str]] = None,
    status_code: int = 200,
) -> JSONResponse:
    """Standardized API response constructor for CrimeVision AI."""
    payload = {
        "success": success,
        "data": data,
        "error": error,
    }
    return JSONResponse(content=payload, status_code=status_code)
