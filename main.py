import sys
import asyncio
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.main import main as async_main

if __name__ == "__main__":
    asyncio.run(async_main())
