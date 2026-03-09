"""
Dashboard parser - extracts course list and notification counts
"""

from typing import List, Dict, Optional
from bs4 import BeautifulSoup


def parse_dashboard(html: str) -> List[Dict[str, any]]:
    """
    Parse dashboard HTML to extract course information

    Args:
        html: Dashboard page HTML

    Returns:
        List of course dictionaries with:
        - course_id: Course ID (from URL)
        - course_name: Course name
        - professor: Professor name
        - new_announcements: Count of new announcements
        - new_assignments: Count of new assignments
        - new_materials: Count of new course materials
    """
    soup = BeautifulSoup(html, 'lxml')
    courses = []

    # Find course list container
    # CAU e-class typically uses a list or grid of course cards
    # We'll look for common patterns

    # Pattern 1: Look for course links
    course_links = soup.find_all('a', href=lambda h: h and 'course_id=' in h)

    for link in course_links:
        try:
            # Extract course ID from URL
            href = link.get('href', '')
            course_id_match = href.split('course_id=')
            if len(course_id_match) < 2:
                continue

            course_id = course_id_match[1].split('&')[0]

            # Get course name (usually in link text or child element)
            course_name = link.get_text(strip=True)

            # Try to find parent container for additional info
            parent = link.find_parent(['li', 'div', 'tr'])

            # Initialize course data
            course_data = {
                'course_id': course_id,
                'course_name': course_name,
                'professor': '',
                'new_announcements': 0,
                'new_assignments': 0,
                'new_materials': 0
            }

            if parent:
                # Look for notification badges/counts
                # Common patterns: <span class="badge">5</span>, <em>3</em>, etc.
                badges = parent.find_all(['span', 'em', 'strong'], class_=lambda c: c and 'badge' in c.lower() if c else False)

                for badge in badges:
                    count_text = badge.get_text(strip=True)
                    if count_text.isdigit():
                        count = int(count_text)

                        # Try to determine what type of notification
                        # Look at surrounding text or parent class
                        context = str(parent).lower()

                        if 'notice' in context or 'announcement' in context or '공지' in context:
                            course_data['new_announcements'] = count
                        elif 'assignment' in context or 'task' in context or '과제' in context:
                            course_data['new_assignments'] = count
                        elif 'material' in context or 'file' in context or '자료' in context:
                            course_data['new_materials'] = count

                # Look for professor name
                # Common patterns: <span class="prof">Name</span>, text after "교수:"
                prof_elem = parent.find(['span', 'div', 'p'], class_=lambda c: c and 'prof' in c.lower() if c else False)
                if prof_elem:
                    course_data['professor'] = prof_elem.get_text(strip=True)
                else:
                    # Try regex pattern
                    import re
                    prof_match = re.search(r'(?:교수|Prof)[:\s]*([^\s<]+)', str(parent))
                    if prof_match:
                        course_data['professor'] = prof_match.group(1)

            # Only add if we have meaningful course info
            if course_data['course_name']:
                courses.append(course_data)

        except Exception as e:
            print(f"Error parsing course: {e}")
            continue

    # Remove duplicates (same course_id)
    seen_ids = set()
    unique_courses = []
    for course in courses:
        if course['course_id'] not in seen_ids:
            seen_ids.add(course['course_id'])
            unique_courses.append(course)

    return unique_courses


def parse_my_courses(html: str) -> List[Dict[str, any]]:
    """
    Alternative parser for "My Courses" page format

    Args:
        html: My courses page HTML

    Returns:
        List of course dictionaries (same format as parse_dashboard)
    """
    soup = BeautifulSoup(html, 'lxml')
    courses = []

    # Look for table-based course list
    tables = soup.find_all('table')

    for table in tables:
        rows = table.find_all('tr')

        for row in rows[1:]:  # Skip header row
            cells = row.find_all(['td', 'th'])

            if len(cells) < 2:
                continue

            # Try to extract course info from cells
            course_link = row.find('a', href=lambda h: h and 'course_id=' in h)

            if course_link:
                href = course_link.get('href', '')
                course_id_match = href.split('course_id=')

                if len(course_id_match) >= 2:
                    course_id = course_id_match[1].split('&')[0]
                    course_name = course_link.get_text(strip=True)

                    course_data = {
                        'course_id': course_id,
                        'course_name': course_name,
                        'professor': '',
                        'new_announcements': 0,
                        'new_assignments': 0,
                        'new_materials': 0
                    }

                    # Try to extract counts from other cells
                    for cell in cells:
                        text = cell.get_text(strip=True)
                        if text.isdigit():
                            count = int(text)
                            # Simple heuristic: first number is announcements, second is assignments
                            if course_data['new_announcements'] == 0:
                                course_data['new_announcements'] = count
                            elif course_data['new_assignments'] == 0:
                                course_data['new_assignments'] = count
                            elif course_data['new_materials'] == 0:
                                course_data['new_materials'] = count

                    courses.append(course_data)

    return courses
