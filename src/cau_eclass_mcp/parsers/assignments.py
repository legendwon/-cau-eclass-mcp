"""
Assignments parser - extracts assignment list with deadlines
"""

from typing import List, Dict, Optional
from bs4 import BeautifulSoup
import re


def parse_assignments(html: str) -> List[Dict[str, any]]:
    """
    Parse assignments page HTML

    Args:
        html: Assignments page HTML

    Returns:
        List of assignment dictionaries with:
        - id: Assignment ID
        - title: Assignment title
        - course_name: Course name (if available)
        - due_date: Due date string
        - submit_date: Submission date (if submitted)
        - status: Status (pending, submitted, graded, etc.)
        - score: Score (if graded)
    """
    soup = BeautifulSoup(html, 'lxml')
    assignments = []

    # Look for assignment tables
    tables = soup.find_all('table')

    for table in tables:
        rows = table.find_all('tr')

        if len(rows) < 2:
            continue

        for row in rows[1:]:  # Skip header
            cells = row.find_all(['td', 'th'])

            if len(cells) < 2:
                continue

            assignment = {}

            # Find title link
            title_link = row.find('a')
            if title_link:
                assignment['title'] = title_link.get_text(strip=True)

                # Extract ID
                href = title_link.get('href', '')
                if 'assignment_id=' in href or 'id=' in href:
                    id_part = href.split('assignment_id=')[-1].split('id=')[-1]
                    assignment['id'] = id_part.split('&')[0]
                else:
                    assignment['id'] = ''
            else:
                assignment['title'] = cells[0].get_text(strip=True) if cells else ''
                assignment['id'] = ''

            # Extract other fields from cells
            assignment['course_name'] = ''
            assignment['due_date'] = ''
            assignment['submit_date'] = ''
            assignment['status'] = 'pending'
            assignment['score'] = ''

            for cell in cells:
                text = cell.get_text(strip=True)

                # Skip empty cells
                if not text:
                    continue

                # Check for date patterns (due date or submit date)
                # Formats: YYYY-MM-DD, YYYY.MM.DD, YYYY/MM/DD, MM-DD, etc.
                date_pattern = r'\d{2,4}[-./]\d{1,2}[-./]\d{1,2}'
                if re.search(date_pattern, text):
                    # Determine if it's due date or submit date
                    if '제출' in str(cell) or 'submit' in str(cell).lower():
                        assignment['submit_date'] = text
                    elif '마감' in str(cell) or 'due' in str(cell).lower() or 'deadline' in str(cell).lower():
                        assignment['due_date'] = text
                    elif not assignment['due_date']:
                        # Default to due date
                        assignment['due_date'] = text

                # Check for status indicators
                if any(word in text for word in ['제출완료', '제출됨', 'submitted']):
                    assignment['status'] = 'submitted'
                elif any(word in text for word in ['채점완료', 'graded']):
                    assignment['status'] = 'graded'
                elif any(word in text for word in ['미제출', 'not submitted', 'pending']):
                    assignment['status'] = 'pending'
                elif any(word in text for word in ['마감', 'closed']):
                    assignment['status'] = 'closed'

                # Check for score (number with "점" or just number in certain contexts)
                score_match = re.search(r'(\d+(?:\.\d+)?)\s*(?:점|점수|점\/|/)', text)
                if score_match:
                    assignment['score'] = score_match.group(1)

            if assignment['title']:
                assignments.append(assignment)

    # Pattern 2: List-based assignments
    if not assignments:
        list_items = soup.find_all('li', class_=lambda c: c and 'assignment' in c.lower() if c else False)

        for item in list_items:
            assignment = {
                'id': '',
                'title': '',
                'course_name': '',
                'due_date': '',
                'submit_date': '',
                'status': 'pending',
                'score': ''
            }

            # Find title
            title_elem = item.find(['a', 'span'], class_=lambda c: c and 'title' in c.lower() if c else False)
            if title_elem:
                assignment['title'] = title_elem.get_text(strip=True)
                if title_elem.name == 'a':
                    href = title_elem.get('href', '')
                    if 'id=' in href:
                        assignment['id'] = href.split('id=')[-1].split('&')[0]

            # Find due date
            date_elem = item.find(['span', 'div'], class_=lambda c: c and 'date' in c.lower() if c else False)
            if date_elem:
                assignment['due_date'] = date_elem.get_text(strip=True)

            # Find status
            status_elem = item.find(['span', 'div'], class_=lambda c: c and 'status' in c.lower() if c else False)
            if status_elem:
                status_text = status_elem.get_text(strip=True)
                if '제출' in status_text or 'submit' in status_text.lower():
                    assignment['status'] = 'submitted'

            if assignment['title']:
                assignments.append(assignment)

    return assignments
