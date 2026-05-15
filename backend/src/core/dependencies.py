"""Shared FastAPI dependencies."""

from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_db

# Type alias for injecting database sessions into route handlers
DbSession = Annotated[AsyncSession, Depends(get_db)]
