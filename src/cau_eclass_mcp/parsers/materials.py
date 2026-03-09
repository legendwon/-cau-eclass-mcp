"""
Course materials parser - extracts recently uploaded materials
"""

from typing import List, Dict
from bs4 import BeautifulSoup
import re


def parse_materials(html: str) -> List[Dict[str, any]]:
    """
    Parse course materials page HTML

    Args:
        html: Materials page HTML

    Returns:
        List of material dictionaries with:
        - id: Material ID
        - title: Material title/filename
        - category: Category or folder name
        - upload_date: Upload date
        - file_size: File size (if available)
        - download_count: Download count (if available)
        - is_new: Whether it's newly uploaded
    """
    soup = BeautifulSoup(html, 'lxml')
    materials = []

    # Look for material lists (tables or file lists)
    tables = soup.find_all('table')

    for table in tables:
        rows = table.find_all('tr')

        if len(rows) < 2:
            continue

        for row in rows[1:]:  # Skip header
            cells = row.find_all(['td', 'th'])

            if len(cells) < 2:
                continue

            material = {}

            # Find title/filename link
            title_link = row.find('a', href=lambda h: h and ('file' in h.lower() or 'download' in h.lower() or 'material' in h.lower()))
            if not title_link:
                title_link = row.find('a')

            if title_link:
                material['title'] = title_link.get_text(strip=True)

                # Extract ID
                href = title_link.get('href', '')
                if 'file_id=' in href or 'id=' in href:
                    id_part = href.split('file_id=')[-1].split('id=')[-1]
                    material['id'] = id_part.split('&')[0]
                else:
                    material['id'] = ''
            else:
                material['title'] = cells[0].get_text(strip=True) if cells else ''
                material['id'] = ''

            # Initialize fields
            material['category'] = ''
            material['upload_date'] = ''
            material['file_size'] = ''
            material['download_count'] = 0
            material['is_new'] = False

            # Check for "new" badge
            new_badge = row.find(['span', 'img'], class_=lambda c: c and 'new' in c.lower() if c else False)
            material['is_new'] = new_badge is not None

            # Extract other info from cells
            for cell in cells:
                text = cell.get_text(strip=True)

                if not text:
                    continue

                # Date pattern
                date_pattern = r'\d{2,4}[-./]\d{1,2}[-./]\d{1,2}'
                if re.search(date_pattern, text):
                    material['upload_date'] = text

                # File size pattern (e.g., "1.5MB", "256KB")
                size_pattern = r'(\d+(?:\.\d+)?)\s*(KB|MB|GB|bytes)'
                size_match = re.search(size_pattern, text, re.IGNORECASE)
                if size_match:
                    material['file_size'] = size_match.group(0)

                # Download count pattern (e.g., "다운로드: 15", "Downloads: 15")
                download_pattern = r'(?:다운로드|download)[:\s]*(\d+)'
                download_match = re.search(download_pattern, text, re.IGNORECASE)
                if download_match:
                    material['download_count'] = int(download_match.group(1))

                # Category (usually in first or second cell, not a date or size)
                if (not material['category'] and
                    len(text) < 50 and
                    not re.search(date_pattern, text) and
                    not re.search(size_pattern, text, re.IGNORECASE) and
                    text != material['title']):
                    material['category'] = text

            if material['title']:
                materials.append(material)

    # Pattern 2: List-based materials
    if not materials:
        list_items = soup.find_all('li', class_=lambda c: c and ('file' in c.lower() or 'material' in c.lower()) if c else False)

        for item in list_items:
            material = {
                'id': '',
                'title': '',
                'category': '',
                'upload_date': '',
                'file_size': '',
                'download_count': 0,
                'is_new': False
            }

            # Find title
            title_elem = item.find(['a', 'span'], class_=lambda c: c and 'title' in c.lower() if c else False)
            if not title_elem:
                title_elem = item.find('a')

            if title_elem:
                material['title'] = title_elem.get_text(strip=True)
                if title_elem.name == 'a':
                    href = title_elem.get('href', '')
                    if 'id=' in href:
                        material['id'] = href.split('id=')[-1].split('&')[0]

            # Check for new badge
            material['is_new'] = item.find(['span', 'img'], class_=lambda c: c and 'new' in c.lower() if c else False) is not None

            # Find date
            date_elem = item.find(['span', 'div'], class_=lambda c: c and 'date' in c.lower() if c else False)
            if date_elem:
                material['upload_date'] = date_elem.get_text(strip=True)

            # Find file size
            size_elem = item.find(['span', 'div'], class_=lambda c: c and 'size' in c.lower() if c else False)
            if size_elem:
                material['file_size'] = size_elem.get_text(strip=True)

            if material['title']:
                materials.append(material)

    return materials
