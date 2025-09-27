#!/usr/bin/env python3
import asyncio
import sys
import os

# Add svc-currency to path
sys.path.insert(0, './svc-currency')

from app.core.database import engine
from sqlalchemy import text

async def test_currency_db():
    """Test currency service database connection."""
    try:
        async with engine.begin() as conn:
            await conn.execute(text('SELECT 1'))
        print('Currency service database connection: True')
        return True
    except Exception as e:
        print(f'Currency service database connection: False - {e}')
        return False

if __name__ == '__main__':
    asyncio.run(test_currency_db())