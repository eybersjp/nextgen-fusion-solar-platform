#!/usr/bin/env python3
import asyncio
import sys
import os

# Add svc-compliance to path
sys.path.insert(0, './svc-compliance')

from app.core.database import engine
from sqlalchemy import text

async def test_compliance_db():
    """Test compliance service database connection."""
    try:
        async with engine.begin() as conn:
            result = await conn.execute(text("SELECT 1"))
            row = result.fetchone()
        print("Compliance service database connection: True")
        return True
    except Exception as e:
        print(f"Compliance service database connection: False - {e}")
        return False

if __name__ == "__main__":
    asyncio.run(test_compliance_db())