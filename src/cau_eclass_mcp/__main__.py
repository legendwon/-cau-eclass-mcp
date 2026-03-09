"""
Entry point for running MCP server as a module
Usage: python -m cau_eclass_mcp
"""

import asyncio
from .server import main

if __name__ == "__main__":
    asyncio.run(main())
