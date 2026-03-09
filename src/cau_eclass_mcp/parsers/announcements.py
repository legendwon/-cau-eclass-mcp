"""
Announcements parser - extracts course announcements
"""

from typing import List, Dict
from bs4 import BeautifulSoup
from datetime import datetime


def parse_announcements(html: str) -> List[Dict[str, any]]:
    """
    Parse announcements page HTML

    Args:
        html: Announcements page HTML

    Returns:
        List of announcement dictionaries with:
        - id: Announcement ID
        - title: Announcement title
        - author: Author name
        - date: Posted date
        - is_new: Whether it's a new announcement
        - content_preview: First 100 chars of content (if available)
    """
    soup = BeautifulSoup(html, 'lxml')
    announcements = []

    # Look for announcement list (table or list format)
    # Common patterns in LMS systems

    # Pattern 1: Table-based list
    tables = soup.find_all('table')

    for table in tables:
        # Check if this looks like an announcement table
        # (has columns like title, author, date)
        rows = table.find_all('tr')

        if len(rows) < 2:
            continue

        for row in rows[1:]:  # Skip header
            cells = row.find_all(['td', 'th'])

            if len(cells) < 2:
                continue

            announcement = {}

            # Try to find title link
            title_link = row.find('a')
            if title_link:
                announcement['title'] = title_link.get_text(strip=True)

                # Extract ID from link
                href = title_link.get('href', '')
                if 'article_id=' in href or 'id=' in href:
                    id_part = href.split('article_id=')[-1].split('id=')[-1]
                    announcement['id'] = id_part.split('&')[0]
                else:
                    announcement['id'] = ''
            else:
                # No link, try first cell
                announcement['title'] = cells[0].get_text(strip=True) if cells else ''
                announcement['id'] = ''

            # Check for "new" badge
            new_badge = row.find(['span', 'img'], class_=lambda c: c and 'new' in c.lower() if c else False)
            announcement['is_new'] = new_badge is not None

            # Try to extract author and date from cells
            # Common order: [title, author, date] or [number, title, author, date]
            announcement['author'] = ''
            announcement['date'] = ''

            for i, cell in enumerate(cells):
                text = cell.get_text(strip=True)

                # Skip title cell
                if i == 0 or (title_link and cell == title_link.find_parent('td')):
                    continue

                # Check if it looks like a date
                if any(sep in text for sep in ['-', '/', '.']):
                    # Likely a date
                    announcement['date'] = text
                elif len(text) < 30 and text and not text.isdigit():
                    # Likely author name
                    if not announcement['author']:
                        announcement['author'] = text

            announcement['content_preview'] = ''

            if announcement['title']:
                announcements.append(announcement)

    # Pattern 2: List-based format
    if not announcements:
        list_items = soup.find_all('li', class_=lambda c: c and 'notice' in c.lower() if c else False)

        for item in list_items:
            announcement = {}

            title_elem = item.find(['a', 'span', 'div'], class_=lambda c: c and 'title' in c.lower() if c else False)
            if title_elem:
                announcement['title'] = title_elem.get_text(strip=True)
                if title_elem.name == 'a':
                    href = title_elem.get('href', '')
                    if 'id=' in href:
                        announcement['id'] = href.split('id=')[-1].split('&')[0]
            else:
                announcement['title'] = item.get_text(strip=True)[:100]

            announcement['id'] = announcement.get('id', '')
            announcement['author'] = ''
            announcement['date'] = ''
            announcement['is_new'] = item.find(['span', 'img'], class_=lambda c: c and 'new' in c.lower() if c else False) is not None
            announcement['content_preview'] = ''

            if announcement['title']:
                announcements.append(announcement)

    return announcements
