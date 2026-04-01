"""
Basic usage example for CAU e-class MCP client

This demonstrates how to use the MCP client programmatically
(not through Claude Code, but directly in Python).
"""

from cau_eclass_mcp.auth import CauAuthenticator
from cau_eclass_mcp.cau_on_client import CAUOnClient
from cau_eclass_mcp.utils.credentials import get_credentials


def main():
    print("="*60)
    print("CAU e-class MCP - Basic Usage Example")
    print("="*60)
    print()

    # Get credentials (from keyring, environment, or prompt)
    print("Step 1: Loading credentials...")
    creds = get_credentials()
    print(f"  Loaded credentials for: {creds['username']}")
    print()

    # Authenticate with CAU SSO
    print("Step 2: Authenticating with CAU SSO...")
    auth = CauAuthenticator(creds['username'], creds['password'])

    if not auth.login():
        print("  ❌ Authentication failed!")
        return

    print("  ✅ Authentication successful!")
    print()

    # Create CAU-ON API client
    print("Step 3: Creating CAU-ON API client...")
    client = CAUOnClient(auth.session)
    print("  ✅ Client initialized")
    print()

    # 1. Dashboard
    print("Step 4: Fetching dashboard...")
    courses = client.get_courses()
    print(f"  ✅ Found {len(courses)} active courses")
    print()

    # 2. Daily Briefing Data (Todo)
    print("Step 5: Fetching Daily Briefing data (Todo items)...")
    todo = client.get_todo_items()
    print(f"  ✅ Found {len(todo)} upcoming items")
    for item in todo[:3]:
        print(f"     - [{item.get('context_name')}] {item.get('title')}")
    print()

    # 3. Weekly Learning View (LearningX)
    if courses:
        first_course = courses[0]
        course_id = str(first_course['id'])
        course_name = first_course['name']

        print(f"Step 6: Fetching Weekly View for: {course_name}")
        modules = client.get_learningx_modules(course_id)
        
        for mod in modules[:2]:  # Show first 2 weeks
            print(f"     Module: {mod.get('title')}")
            for item in mod.get('module_items', [])[:2]:
                title = item.get('title')
                item_type = item.get('type')
                status = ""
                if item_type == 'lecture':
                    att = item.get('attendance_status', {})
                    status = "✅" if att.get('attendance_status') == 'attendance' else "❌"
                print(f"        {status} [{item_type}] {title}")
    
    print()
    print("="*60)
    print("Example completed successfully!")
    print("="*60)


if __name__ == "__main__":
    main()
