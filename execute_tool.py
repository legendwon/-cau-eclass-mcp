import asyncio
import os
import sys

# Add src to sys.path
sys.path.append(os.path.abspath("src"))

from cau_eclass_mcp.server import handle_get_daily_briefing, get_cau_on_client

async def main():
    try:
        print("Initializing CAU-ON client...")
        client = get_cau_on_client()
        print("CAU-ON client initialized. Fetching daily briefing...")
        result = await handle_get_daily_briefing(client)
        print("Daily briefing fetched successfully:")
        for content in result:
            print(content.text)
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(main())
