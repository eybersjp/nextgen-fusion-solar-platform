#!/usr/bin/env python3
import asyncio
import sys
import os

# Add svc-project to path
sys.path.insert(0, './svc-project')

from app.core.database import engine
from sqlalchemy import text

async def test_project_db():
    """Test project service database connection."""
    try:
        async with engine.begin() as conn:
            result = await conn.execute(text("SELECT 1"))
            row = result.fetchone()
        print("Project service database connection: True")
        return True
    except Exception as e:
        print(f"Project service database connection: False - {e}")
        return False

if __name__ == "__main__":
    asyncio.run(test_project_db())