import re
import requests

DEFAULT_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept-Language': 'en-US,en;q=0.5',
}

from typing import TypedDict, Optional


class FileNotFoundError(Exception):
    """Exception raised when a file is not found on the host."""
    pass

class DirectLinkResult(TypedDict):
    """Type definition for the direct link response structure."""
    url: str
    filename: str
    headers: dict
    payload: Optional[dict] 
    
class Host:
    def __init__(self, name, domain, url_pattern):
        self.name = name
        self.domain = domain
        self.url_pattern = url_pattern
        self.session = requests.Session()
        self.session.headers.update(DEFAULT_HEADERS)
    def get_direct_link(self, url: str) -> DirectLinkResult:
        """
        Retrieves a direct download link and associated metadata from a source URL.

        Args:
            url: The source URL where the content is hosted (e.g., API endpoint or webpage URL).

        Returns:
            A typed dictionary containing:
                - url (str): Direct download URL (e.g., 'https://cdn.example.com/file.ext').
                - filename (str): Suggested filename with extension (e.g., 'report.pdf').
                - headers (dict): Required HTTP headers (e.g., {'Authorization': 'Bearer token'}).
                - payload (dict, optional): Additional request parameters if needed by the API. 
                Defaults to None if no payload is required.

        Raises:
            ValueError: If the input URL is empty or malformed.
            requests.HTTPError: If the API responds with a non-200 status code.
            TimeoutError: If the request exceeds the allowed timeout duration.

        Examples:
            >>> result = get_direct_link("https://api.service.com/v1/content/123")
            >>> print(result["url"])  # Output: 'https://cdn.service.com/abc123.pdf'
            >>> print(result["payload"])  # Output: None (or {'expires_in': 3600} if present)
        """
        pass
    def _get_target_url(self, url: str) -> str:
        target_url = url if url is not None else self.url
        if not target_url:
            raise ValueError("Input URL is empty")
    def _get_filename_from_direct_link(self, direct_link) -> str:
        head_response = self.session.head(direct_link)
        content_disposition = head_response.headers.get('Content-Disposition', '')
        if content_disposition:
            filename = re.search(r'filename=(.*?);', content_disposition)
            if filename:
                return filename.group(1)
        if not filename and direct_link:
            filename = direct_link.split('/')[-1].split('?')[0]
        return None

