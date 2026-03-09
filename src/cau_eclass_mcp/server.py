"""
CAU e-class MCP Server (CAU-ON API Version)
Provides tools to read e-class dashboard, announcements, and assignments
"""

import os
from typing import Optional
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

from .auth import CauAuthenticator
from .cau_on_client import CAUOnClient
from .utils.credentials import get_credentials
from .utils.cache import get_cached, set_cached


# Create MCP server instance
app = Server("cau-eclass")

# Global client instances
_authenticator: Optional[CauAuthenticator] = None
_cau_on_client: Optional[CAUOnClient] = None


def get_cau_on_client() -> CAUOnClient:
    """Get or initialize CAU-ON API client with SSO authentication"""
    global _authenticator, _cau_on_client

    if _cau_on_client is None:
        # Get credentials from keyring, environment variables, or prompt
        creds = get_credentials()

        # Initialize authenticator
        _authenticator = CauAuthenticator(creds['username'], creds['password'])

        # Perform SSO login
        if not _authenticator.login():
            raise RuntimeError("Failed to authenticate with CAU SSO. Please check your credentials.")

        # Create CAU-ON client with authenticated session
        _cau_on_client = CAUOnClient(_authenticator.session)

    return _cau_on_client


@app.list_tools()
async def list_tools() -> list[Tool]:
    """List available MCP tools"""
    return [
        Tool(
            name="get_dashboard",
            description="Get overview of all active courses with metadata (course names, IDs, terms)",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        ),
        Tool(
            name="list_course_announcements",
            description="List announcements for a specific course",
            inputSchema={
                "type": "object",
                "properties": {
                    "course_id": {
                        "type": "string",
                        "description": "Course ID (get from dashboard first)"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of announcements to return (default: 20)",
                        "default": 20
                    }
                },
                "required": ["course_id"]
            }
        ),
        Tool(
            name="list_assignments",
            description="List assignments and submission status for a specific course",
            inputSchema={
                "type": "object",
                "properties": {
                    "course_id": {
                        "type": "string",
                        "description": "Course ID to get assignments from"
                    }
                },
                "required": ["course_id"]
            }
        ),
        Tool(
            name="get_lecture_modules",
            description="Get weekly lecture modules (주차별 강의 목록) with attendance status for online courses",
            inputSchema={
                "type": "object",
                "properties": {
                    "course_id": {
                        "type": "string",
                        "description": "Course ID to get modules from"
                    },
                    "include_attendance": {
                        "type": "boolean",
                        "description": "Include detailed attendance/lecture status (slower, default: false)",
                        "default": False
                    }
                },
                "required": ["course_id"]
            }
        ),
        Tool(
            name="download_file",
            description="Download a file from e-class announcements or course materials",
            inputSchema={
                "type": "object",
                "properties": {
                    "course_id": {
                        "type": "string",
                        "description": "Course ID (from dashboard or announcement)"
                    },
                    "file_id": {
                        "type": "string",
                        "description": "File ID (from announcement attachments)"
                    },
                    "save_path": {
                        "type": "string",
                        "description": "Local file path to save (e.g., './downloads/lecture.pdf')"
                    }
                },
                "required": ["course_id", "file_id", "save_path"]
            }
        )
    ]


@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    """Handle tool calls"""

    try:
        client = get_cau_on_client()

        if name == "get_dashboard":
            return await handle_get_dashboard(client)

        elif name == "list_course_announcements":
            course_id = arguments.get("course_id")
            limit = arguments.get("limit", 20)
            return await handle_list_announcements(client, course_id, limit)

        elif name == "list_assignments":
            course_id = arguments.get("course_id")
            return await handle_list_assignments(client, course_id)

        elif name == "get_lecture_modules":
            course_id = arguments.get("course_id")
            include_attendance = arguments.get("include_attendance", False)
            return await handle_get_lecture_modules(client, course_id, include_attendance)

        elif name == "download_file":
            course_id = arguments.get("course_id")
            file_id = arguments.get("file_id")
            save_path = arguments.get("save_path")
            return await handle_download_file(client, course_id, file_id, save_path)

        else:
            return [TextContent(type="text", text=f"Unknown tool: {name}")]

    except Exception as e:
        return [TextContent(type="text", text=f"Error: {str(e)}")]


async def handle_get_dashboard(client: CAUOnClient) -> list[TextContent]:
    """Handle get_dashboard tool call"""

    # Check cache (5 min)
    cache_key = "dashboard"
    cached = get_cached(cache_key, max_age_seconds=300)

    if cached:
        courses = cached
    else:
        # Fetch courses via CAU-ON API
        courses = client.get_courses()

        if not courses:
            return [TextContent(type="text", text="No active courses found.")]

        # Cache response
        set_cached(cache_key, courses)

    # Format output
    output = "# CAU e-class Dashboard (CAU-ON)\n\n"
    output += f"Total active courses: {len(courses)}\n\n"

    for course in courses:
        output += f"## {course.get('name', 'Unknown Course')}\n"
        output += f"- **Course ID**: {course.get('id')}\n"

        if course.get('course_code'):
            output += f"- **Course Code**: {course['course_code']}\n"

        # Handle term information
        term = course.get('term')
        if term:
            if isinstance(term, dict):
                output += f"- **Term**: {term.get('name', 'Unknown')}\n"
            else:
                output += f"- **Term**: {term}\n"

        if course.get('workflow_state'):
            output += f"- **Status**: {course['workflow_state']}\n"

        output += "\n"

    return [TextContent(type="text", text=output)]


async def handle_list_announcements(client: CAUOnClient, course_id: str, limit: int) -> list[TextContent]:
    """Handle list_course_announcements tool call"""

    # Check cache (2 min)
    cache_key = f"announcements_{course_id}"
    cached = get_cached(cache_key, max_age_seconds=120)

    if cached:
        announcements = cached
    else:
        # Fetch announcements via CAU-ON API
        announcements = client.get_course_announcements(course_id, limit)

        if not announcements:
            return [TextContent(type="text", text=f"No announcements found for course {course_id}")]

        set_cached(cache_key, announcements)

    # Format output
    output = f"# Course Announcements (Course ID: {course_id})\n\n"
    output += f"Total: {len(announcements)} announcements\n\n"

    for ann in announcements:
        title = ann.get('title', 'Untitled')
        output += f"## {title}\n"

        if ann.get('id'):
            output += f"- **ID**: {ann['id']}\n"

        if ann.get('posted_at'):
            output += f"- **Posted**: {ann['posted_at']}\n"

        if ann.get('author'):
            # Handle author as dict or string
            author = ann['author']
            if isinstance(author, dict):
                author_name = author.get('display_name', author.get('name', 'Unknown'))
            else:
                author_name = str(author)
            output += f"- **Author**: {author_name}\n"

        # Extract and show file attachments
        html_message = ann.get('message', '')
        if html_message:
            from .cau_on_client import CAUOnClient
            attachments = CAUOnClient.extract_attachments_from_html(html_message)
            if attachments:
                output += f"- **Attachments**: {len(attachments)} file(s)\n"
                for att in attachments:
                    filename = att.get('filename', 'Unknown')
                    file_id = att.get('file_id', 'N/A')
                    output += f"  - 📎 `{filename}` (file_id: {file_id})\n"

        # Show full message content
        if ann.get('message'):
            message = ann['message'].strip()
            # Remove HTML tags
            import re
            message = re.sub(r'<[^>]+>', '', message)
            if message:
                output += f"- **Content**: {message}\n"

        output += "\n"

    return [TextContent(type="text", text=output)]


async def handle_list_assignments(client: CAUOnClient, course_id: str) -> list[TextContent]:
    """Handle list_assignments tool call"""

    # Check cache (2 min)
    cache_key = f"assignments_{course_id}"
    cached = get_cached(cache_key, max_age_seconds=120)

    if cached:
        submissions = cached
    else:
        # Fetch assignment submissions via CAU-ON API
        # Note: This endpoint returns submission status, not full assignment metadata
        submissions = client.get_course_assignments(course_id)

        if not submissions:
            return [TextContent(type="text", text=f"No assignments found for course {course_id}")]

        set_cached(cache_key, submissions)

    # Format output
    output = f"# Assignments (Course ID: {course_id})\n\n"
    output += f"Total: {len(submissions)} assignments\n\n"

    for sub in submissions:
        # Determine status emoji
        workflow_state = sub.get('workflow_state', 'unsubmitted')

        status_emoji = {
            'submitted': '✅',
            'graded': '📊',
            'pending_review': '⏳',
            'unsubmitted': '❌'
        }.get(workflow_state, '❓')

        # Use assignment_id as the title (since we don't have assignment name yet)
        assignment_id = sub.get('assignment_id', 'Unknown')
        output += f"## {status_emoji} Assignment ID: {assignment_id}\n"

        output += f"- **Submission ID**: {sub.get('id')}\n"
        output += f"- **Status**: {workflow_state}\n"

        if sub.get('submitted_at'):
            output += f"- **Submitted**: {sub['submitted_at']}\n"

        if sub.get('score') is not None:
            output += f"- **Score**: {sub['score']}\n"

        if sub.get('grade'):
            output += f"- **Grade**: {sub['grade']}\n"

        # Show flags
        flags = []
        if sub.get('late'):
            flags.append('⚠️ Late')
        if sub.get('missing'):
            flags.append('❌ Missing')

        if flags:
            output += f"- **Flags**: {', '.join(flags)}\n"

        output += "\n"

    # Add note about limited metadata
    output += "\n---\n"
    output += "_Note: This shows submission status. For full assignment details (title, due date), "
    output += "we may need to discover an additional API endpoint._\n"

    return [TextContent(type="text", text=output)]


async def handle_get_lecture_modules(client: CAUOnClient, course_id: str, include_attendance: bool) -> list[TextContent]:
    """Handle get_lecture_modules tool call"""
    import re

    # Check cache (5 min)
    cache_key = f"modules_{course_id}"
    cached = get_cached(cache_key, max_age_seconds=300)

    if cached:
        modules = cached
    else:
        # Fetch modules via CAU-ON API
        modules = client.get_modules(course_id)

        if not modules:
            return [TextContent(type="text", text=f"No modules found for course {course_id}")]

        set_cached(cache_key, modules)

    # Format output
    output = f"# Weekly Lecture Modules (주차별 강의 목록)\n\n"
    output += f"**Course ID**: {course_id}\n"
    output += f"**Total Modules**: {len(modules)}\n\n"

    for module in modules:
        module_name = module.get('name', 'Unnamed Module')
        output += f"## {module_name}\n"

        if module.get('unlock_at'):
            output += f"- **Unlock At**: {module['unlock_at']}\n"

        items = module.get('items', [])
        if not items:
            output += "- _No items in this module_\n\n"
            continue

        output += f"- **Items**: {len(items)}\n\n"

        for item in items:
            title = item.get('title', 'Untitled')
            item_type = item.get('type', 'Unknown')

            output += f"### {title}\n"
            output += f"- **Type**: {item_type}\n"
            output += f"- **ID**: {item.get('id')}\n"

            # Extract attendance item ID from external_url if available
            attendance_id = None
            external_url = item.get('external_url', '')
            if 'lecture_attendance/items/view/' in external_url:
                match = re.search(r'/lecture_attendance/items/view/(\d+)', external_url)
                if match:
                    attendance_id = match.group(1)

            # Fetch detailed attendance info if requested
            if include_attendance and attendance_id:
                attendance_data = client.get_attendance_item(course_id, attendance_id)
                if attendance_data:
                    output += f"- **Week**: {attendance_data.get('week_position')}\n"
                    output += f"- **Lesson**: {attendance_data.get('lesson_position')}\n"
                    output += f"- **Status**: {attendance_data.get('lecture_period_status')}\n"

                    # Show attendance/completion status
                    att_info = attendance_data.get('attendance_data', {})
                    if att_info:
                        completed = att_info.get('completed', False)
                        status_icon = "✅" if completed else "❌"
                        output += f"- **Completion**: {status_icon} {att_info.get('attendance_status', 'N/A')}\n"

                        if att_info.get('progress'):
                            progress_sec = att_info['progress']
                            duration_sec = attendance_data.get('item_content_data', {}).get('duration', progress_sec)
                            progress_pct = (progress_sec / duration_sec * 100) if duration_sec > 0 else 0
                            output += f"- **Progress**: {int(progress_pct)}% ({int(progress_sec/60)}m / {int(duration_sec/60)}m)\n"

                    if attendance_data.get('unlock_at'):
                        output += f"- **Unlock**: {attendance_data['unlock_at']}\n"
                    if attendance_data.get('due_at'):
                        output += f"- **Due**: {attendance_data['due_at']}\n"
                    if attendance_data.get('lock_at'):
                        output += f"- **Lock**: {attendance_data['lock_at']}\n"

            # Show completion requirement if present
            completion = item.get('completion_requirement')
            if completion:
                req_type = completion.get('type', 'unknown')
                completed = completion.get('completed', False)
                status = "✅" if completed else "❌"
                output += f"- **Completion**: {status} ({req_type})\n"

            output += "\n"

        output += "\n"

    if not include_attendance:
        output += "\n---\n"
        output += "_Tip: Use `include_attendance: true` to see detailed lecture status and due dates_\n"

    return [TextContent(type="text", text=output)]


async def handle_download_file(client: CAUOnClient, course_id: str, file_id: str, save_path: str) -> list[TextContent]:
    """Handle download_file tool call"""
    import os

    # Get file metadata first
    file_info = client.get_file_info(course_id, file_id)

    if not file_info:
        return [TextContent(type="text", text=f"Failed to get file info for file_id={file_id}")]

    filename = file_info.get('display_name', file_info.get('filename', 'unknown'))
    filesize = file_info.get('size', 0)

    # Download file
    success = client.download_file(course_id, file_id, save_path)

    if success:
        # Verify file was saved
        if os.path.exists(save_path):
            actual_size = os.path.getsize(save_path)
            output = f"# File Download Successful\n\n"
            output += f"- **Filename**: {filename}\n"
            output += f"- **File ID**: {file_id}\n"
            output += f"- **Course ID**: {course_id}\n"
            output += f"- **Expected Size**: {filesize:,} bytes\n"
            output += f"- **Downloaded Size**: {actual_size:,} bytes\n"
            output += f"- **Saved to**: `{save_path}`\n"

            if actual_size == filesize:
                output += f"\n✅ **File size matches - download verified**"
            else:
                output += f"\n⚠️ **Warning: File size mismatch**"

            return [TextContent(type="text", text=output)]
        else:
            return [TextContent(type="text", text=f"Download reported success but file not found at {save_path}")]
    else:
        return [TextContent(type="text", text=f"Failed to download file: {filename} (file_id={file_id})")]


async def main():
    """Main entry point for MCP server"""
    async with stdio_server() as (read_stream, write_stream):
        await app.run(
            read_stream,
            write_stream,
            app.create_initialization_options()
        )


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
