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
            name="get_course_details",
            description="Get detailed course content: weekly lectures, assignments, or files",
            inputSchema={
                "type": "object",
                "properties": {
                    "course_id": {
                        "type": "string",
                        "description": "Course ID"
                    },
                    "content_type": {
                        "type": "string",
                        "enum": ["weekly", "assignments", "files"],
                        "description": "Type of content to retrieve (default: 'weekly')"
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
        ),
        Tool(
            name="get_vod_info",
            description="Get direct streaming URLs and metadata for a VOD content ID",
            inputSchema={
                "type": "object",
                "properties": {
                    "content_id": {
                        "type": "string",
                        "description": "VOD Content ID (from module items or weekly view)"
                    }
                },
                "required": ["content_id"]
            }
        ),
        Tool(
            name="get_daily_briefing",
            description="Get a unified summary of upcoming deadlines, new messages, and recent course updates",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
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

        elif name == "get_course_details":
            course_id = arguments.get("course_id")
            content_type = arguments.get("content_type", "weekly")
            return await handle_get_course_details(client, course_id, content_type)

        elif name == "download_file":
            course_id = arguments.get("course_id")
            file_id = arguments.get("file_id")
            save_path = arguments.get("save_path")
            return await handle_download_file(client, course_id, file_id, save_path)

        elif name == "get_vod_info":
            content_id = arguments.get("content_id")
            return await handle_get_vod_info(client, content_id)

        elif name == "get_daily_briefing":
            return await handle_get_daily_briefing(client)

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

    return [TextContent(type="text", text=output)]


async def handle_get_course_details(client: CAUOnClient, course_id: str, content_type: str) -> list[TextContent]:
    """Handle get_course_details tool call by routing to specific content handlers"""
    if content_type == "assignments":
        return await handle_list_assignments(client, course_id)
    elif content_type == "files":
        return await handle_list_course_files(client, course_id)
    else:  # default "weekly"
        return await handle_get_weekly_view(client, course_id)


async def handle_list_assignments(client: CAUOnClient, course_id: str) -> list[TextContent]:
    """Handle list_assignments logic (internal)"""

    # Check cache (2 min)
    cache_key = f"assignments_{course_id}"
    cached = get_cached(cache_key, max_age_seconds=120)

    if cached:
        assignments = cached
    else:
        # Fetch assignments via CAU-ON API (now includes submissions)
        assignments = client.get_course_assignments(course_id)

        if not assignments:
            return [TextContent(type="text", text=f"No assignments found for course {course_id}")]

        set_cached(cache_key, assignments)

    # Format output
    output = f"# Assignments (Course ID: {course_id})\n\n"
    output += f"Total: {len(assignments)} assignments\n\n"

    for assign in assignments:
        # Get submission info if available
        sub = assign.get('submission', {})
        workflow_state = sub.get('workflow_state', 'unsubmitted')

        status_emoji = {
            'submitted': '✅',
            'graded': '📊',
            'pending_review': '⏳',
            'unsubmitted': '❌'
        }.get(workflow_state, '❓')

        # Use actual assignment name
        name = assign.get('name', f"Assignment ID: {assign.get('id')}")
        output += f"## {status_emoji} {name}\n"

        output += f"- **Assignment ID**: {assign.get('id')}\n"
        output += f"- **Status**: {workflow_state}\n"
        
        if assign.get('due_at'):
            output += f"- **Due At**: {assign['due_at']}\n"
        
        if assign.get('points_possible') is not None:
            output += f"- **Points Possible**: {assign['points_possible']}\n"

        if sub.get('submitted_at'):
            output += f"- **Submitted At**: {sub['submitted_at']}\n"

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


async def handle_list_course_files(client: CAUOnClient, course_id: str) -> list[TextContent]:
    """Handle list_course_files tool call"""
    # Check cache (5 min)
    cache_key = f"files_{course_id}"
    cached = get_cached(cache_key, max_age_seconds=300)

    if cached:
        files = cached
    else:
        files = client.get_course_files(course_id)
        
        if not files:
            return [TextContent(type="text", text=f"No files found for course {course_id}")]

        set_cached(cache_key, files)

    output = f"# Course Files (자료실)\n\n"
    output += f"**Course ID**: {course_id}\n"
    output += f"**Total Files**: {len(files)}\n\n"

    for f in files:
        output += f"### {f.get('display_name', f.get('filename', 'Unknown'))}\n"
        output += f"- **File ID**: {f.get('id')}\n"
        output += f"- **Size**: {f.get('size', 0):,} bytes\n"
        if f.get('created_at'):
            output += f"- **Created At**: {f['created_at']}\n"
        output += "\n"

    return [TextContent(type="text", text=output)]


async def handle_get_weekly_view(client: CAUOnClient, course_id: str) -> list[TextContent]:
    """Handle get_weekly_view tool call"""
    # Check cache (5 min)
    cache_key = f"weekly_{course_id}"
    cached = get_cached(cache_key, max_age_seconds=300)

    if cached:
        modules = cached
    else:
        modules = client.get_learningx_modules(course_id)
        if not modules:
            return [TextContent(type="text", text=f"No LearningX modules found for course {course_id}")]
        set_cached(cache_key, modules)

    output = f"# Weekly Study View (주차별 학습)\n\n"
    output += f"**Course ID**: {course_id}\n\n"

    for mod in modules:
        output += f"## {mod.get('title', 'Unnamed Module')}\n"
        items = mod.get('module_items', [])
        
        if not items:
            output += "- _No items in this week_\n\n"
            continue

        for item in items:
            title = item.get('title', 'Untitled')
            item_type = item.get('type', 'Unknown')
            output += f"### {title}\n"
            output += f"- **Type**: {item_type}\n"
            
            # Show attendance/progress for video content
            if item_type == 'lecture':
                att = item.get('attendance_status', {})
                status = "✅ Completed" if att.get('attendance_status') == 'attendance' else "❌ Unwatched"
                output += f"- **Attendance**: {status}\n"
                if att.get('progress'):
                    output += f"- **Progress**: {att['progress']}%\n"
                if item.get('content_id'):
                    output += f"- **Content ID (for VOD info)**: {item['content_id']}\n"
            
            elif item_type == 'assignment':
                sub = item.get('submission_status', {})
                status = "✅ Submitted" if sub.get('workflow_state') in ['submitted', 'graded'] else "❌ Not Submitted"
                output += f"- **Status**: {status}\n"
                if item.get('due_at'):
                    output += f"- **Due**: {item['due_at']}\n"
            
            output += "\n"

    return [TextContent(type="text", text=output)]


async def handle_get_vod_info(client: CAUOnClient, content_id: str) -> list[TextContent]:
    """Handle get_vod_info tool call"""
    info = client.get_ocs_content_info(content_id)
    
    if not info:
        return [TextContent(type="text", text=f"Failed to fetch VOD info for content_id={content_id}")]

    output = f"# VOD Content Information\n\n"
    output += f"**Title**: {info.get('title', 'Unknown')}\n"
    output += f"**Content ID**: {content_id}\n"
    output += f"**Content Type**: {info.get('content_type', 'Unknown')}\n\n"

    output += "## Streaming URLs (Media URIs)\n"
    media_uris = info.get('media_uris', [])
    if not media_uris:
        output += "_No streaming links found._\n"
    else:
        for uri in media_uris:
            output += f"### {uri.get('target', 'Default')} ({uri.get('method', 'N/A')})\n"
            output += f"- **URL**: {uri.get('url')}\n\n"

    return [TextContent(type="text", text=output)]


async def handle_get_daily_briefing(client: CAUOnClient) -> list[TextContent]:
    """Handle get_daily_briefing tool call"""
    # Fetch data from multiple endpoints
    todo_items = client.get_todo_items()
    conversations = client.get_conversations(limit=5)
    activity_stream = client.get_activity_stream()

    output = "# 📅 Daily Briefing (중앙대 e-class 요약)\n\n"

    # 1. Deadlines (Todo)
    output += "## 🚨 마감 임박 (Upcoming Deadlines)\n"
    if not todo_items:
        output += "_현재 예정된 할 일이 없습니다._\n"
    else:
        for item in todo_items[:10]:  # Show top 10
            course_name = item.get('context_name', 'Unknown Course')
            title = item.get('title', 'Untitled')
            due_at = item.get('assignment', {}).get('due_at') or item.get('quiz', {}).get('due_at')
            
            status = ""
            if item.get('needs_grading_count'):
                status = " (채점 대기 중)"
            
            output += f"- **[{course_name}]** {title}\n"
            if due_at:
                output += f"  - 마감: {client._convert_utc_to_kst(due_at)}\n"
    output += "\n"

    # 2. Messages (Inbox)
    output += "## 📩 새로운 쪽지 (Recent Messages)\n"
    unread_messages = [c for c in conversations if c.get('workflow_state') == 'unread']
    display_messages = unread_messages if unread_messages else conversations[:3]
    
    if not display_messages:
        output += "_최근 받은 쪽지가 없습니다._\n"
    else:
        for conv in display_messages:
            author = conv.get('participants', [{}])[0].get('name', 'Unknown')
            subject = conv.get('subject', 'No Subject')
            last_msg = conv.get('last_message', '...')
            unread_tag = "🔴 [미읽음] " if conv.get('workflow_state') == 'unread' else ""
            
            output += f"- {unread_tag}**{author}**: {subject}\n"
            output += f"  - _{last_msg[:50]}..._\n"
    output += "\n"

    # 3. Activity Stream
    output += "## 🆕 최근 업데이트 (Activity Stream)\n"
    if not activity_stream:
        output += "_최근 업데이트 소식이 없습니다._\n"
    else:
        # Categorize by type
        for activity in activity_stream[:7]:
            act_type = activity.get('type', 'Message')
            title = activity.get('title', 'Notification')
            course = activity.get('course_name', '')
            
            emoji = {
                'Announcement': '📢',
                'Conversation': '✉️',
                'Assignment': '📝',
                'Submission': '📤',
                'GradeChange': '📊'
            }.get(act_type, '🔔')
            
            output += f"- {emoji} **{title}**"
            if course:
                output += f" ({course})"
            output += "\n"

    return [TextContent(type="text", text=output)]


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
