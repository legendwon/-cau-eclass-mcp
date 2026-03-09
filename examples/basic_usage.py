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

    # Get dashboard (list of courses)
    print("Step 4: Fetching dashboard...")
    dashboard = client.get_dashboard()
    print(f"  ✅ Found {len(dashboard.get('courses', []))} courses")
    print()

    # Display courses
    print("Your Courses:")
    print("-" * 60)
    for course in dashboard.get('courses', []):
        course_id = course.get('id')
        course_name = course.get('name', 'Unknown')
        course_code = course.get('course_code', 'N/A')
        enrollment_term = course.get('enrollment_term_name', 'N/A')

        print(f"  [{course_id}] {course_name}")
        print(f"      Code: {course_code}")
        print(f"      Term: {enrollment_term}")
        print()

    # Example: Get announcements for first course
    if dashboard.get('courses'):
        first_course = dashboard['courses'][0]
        course_id = first_course['id']
        course_name = first_course['name']

        print(f"Announcements for: {course_name}")
        print("-" * 60)

        announcements = client.get_course_announcements(course_id, limit=5)

        for i, announcement in enumerate(announcements, 1):
            title = announcement.get('title', 'No title')
            author = announcement.get('author', {}).get('display_name', 'Unknown')
            posted_at = announcement.get('posted_at', 'Unknown date')

            print(f"{i}. {title}")
            print(f"   By: {author}")
            print(f"   Posted: {posted_at}")
            print()

    # Example: Get assignments for first course
    if dashboard.get('courses'):
        first_course = dashboard['courses'][0]
        course_id = first_course['id']
        course_name = first_course['name']

        print(f"Assignments for: {course_name}")
        print("-" * 60)

        assignments = client.get_assignments(course_id)

        for i, assignment in enumerate(assignments, 1):
            name = assignment.get('name', 'No name')
            due_at = assignment.get('due_at', 'No due date')
            submitted = assignment.get('has_submitted_submissions', False)

            status = "✅ Submitted" if submitted else "⏳ Not submitted"

            print(f"{i}. {name}")
            print(f"   Due: {due_at}")
            print(f"   Status: {status}")
            print()

    print("="*60)
    print("Example completed successfully!")
    print("="*60)


if __name__ == "__main__":
    main()
