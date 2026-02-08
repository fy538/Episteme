"""
URL content fetcher for evidence ingestion.

Fetches a web page, extracts readable text, and returns structured
content for ingestion through the universal pipeline.
"""
import logging
import re
from dataclasses import dataclass
from typing import Optional
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

MAX_CONTENT_LENGTH = 100_000  # 100KB text limit
FETCH_TIMEOUT = 30  # seconds


@dataclass
class FetchedContent:
    """Result of fetching a URL."""
    url: str
    title: str
    domain: str
    text: str
    published_date: Optional[str] = None  # ISO date string (YYYY-MM-DD)
    author: Optional[str] = None
    error: Optional[str] = None


def fetch_url_content(url: str, timeout: int = FETCH_TIMEOUT) -> FetchedContent:
    """
    Fetch and extract readable text from a URL.

    Strips navigation, scripts, and other non-content elements.
    Extracts title, author, and published date from meta tags.

    Args:
        url: URL to fetch
        timeout: Request timeout in seconds

    Returns:
        FetchedContent with extracted text or error
    """
    parsed = urlparse(url)
    domain = parsed.netloc

    try:
        response = requests.get(
            url,
            timeout=timeout,
            headers={
                'User-Agent': 'Episteme/1.0 (Research Tool)',
                'Accept': 'text/html,application/xhtml+xml',
            },
            allow_redirects=True,
        )
        response.raise_for_status()

        soup = BeautifulSoup(response.text, 'html.parser')

        # Extract title
        title = ''
        if soup.title and soup.title.string:
            title = soup.title.string.strip()

        # Remove non-content elements
        for element in soup(['script', 'style', 'nav', 'footer', 'header',
                            'aside', 'noscript', 'iframe']):
            element.decompose()

        # Extract text
        text = soup.get_text(separator='\n', strip=True)
        text = re.sub(r'\n{3,}', '\n\n', text)  # Collapse excessive whitespace
        text = text[:MAX_CONTENT_LENGTH]

        # Extract published date from meta tags
        pub_date = _extract_meta(soup, [
            'article:published_time',
            'datePublished',
            'date',
            'DC.date.issued',
            'publication_date',
        ])
        if pub_date:
            pub_date = pub_date[:10]  # Keep just YYYY-MM-DD

        # Extract author from meta tags
        author = _extract_meta(soup, [
            'author',
            'article:author',
            'DC.creator',
        ])

        return FetchedContent(
            url=url,
            title=title,
            domain=domain,
            text=text,
            published_date=pub_date,
            author=author,
        )

    except requests.exceptions.Timeout:
        logger.warning(f"URL fetch timeout: {url}")
        return FetchedContent(
            url=url, title='', domain=domain, text='',
            error=f'Request timed out after {timeout}s',
        )
    except requests.exceptions.HTTPError as e:
        logger.warning(f"URL fetch HTTP error: {url}: {e}")
        return FetchedContent(
            url=url, title='', domain=domain, text='',
            error=f'HTTP {e.response.status_code}',
        )
    except Exception as e:
        logger.warning(f"URL fetch failed: {url}: {e}")
        return FetchedContent(
            url=url, title='', domain=domain, text='',
            error=str(e),
        )


def _extract_meta(soup: BeautifulSoup, property_names: list) -> Optional[str]:
    """Extract content from meta tags by property/name attribute."""
    for meta in soup.find_all('meta'):
        prop = meta.get('property', '') or meta.get('name', '')
        if prop in property_names:
            content = meta.get('content', '').strip()
            if content:
                return content
    return None
