import requests
import re
from urllib.parse import unquote

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                    'AppleWebKit/537.36 (KHTML, like Gecko) '
                    'Chrome/120.0.0.0 Safari/537.36'
}


class DirectLinkError(Exception):
    """Custom exception for download link errors"""

def sanitize_filename(filename):
    """Clean invalid characters from filenames"""
    return re.sub(r'[\\/*?:"<>|]', '', filename).strip()


def _handle_errors(response, password):
    if "deleted for inactivity" in response.text:
        raise DirectLinkError("File removed due to inactivity")
    if "does not exist" in response.text:
        raise DirectLinkError("File not found")
    if "id=\"pass\"" in response.text and not password:
        raise DirectLinkError("Password required")


def get_direct_link(url, password=None):
    with requests.Session() as session:
        try:
            # Initial request to get security parameters and filename
            response = session.get(url, headers=headers, timeout=10)
            response.raise_for_status()

            _handle_errors(response, password)
            # Extract filename from HTML
            filename_match = re.search(
                r'<td class="normal">([^<]+)</td>',
                response.text
            )
            filename = sanitize_filename(filename_match.group(1)) if filename_match else None
            
            # Fallback filename extraction from URL if needed
            if not filename:
                filename = unquote(url.split('/')[-1].split('?')[0]) or "unknown_file"

            # Get security parameter
            adz_match = re.search(r'name="adz" value="([\d\.]+)"', response.text)
            if not adz_match:
                raise DirectLinkError("Missing security parameter")

            # Submit download form
            post_data = {
                'submit': 'Download',
                'pass': password or '',
                'adz': adz_match.group(1)
            }
            post_response = session.post(
                url,
                data=post_data,
                headers=headers,
                allow_redirects=False,
                timeout=10
            )
            post_response.raise_for_status()

            if "Incorrect password" in post_response.text:
                raise DirectLinkError("Invalid password")

            # Extract direct download link
            #print(post_response.text)
            link_match = re.search(
                r'<a href="(https://[^"]+)"[^>]*>Click here to download the file</a>',
                post_response.text
            )
            if not link_match:
                raise DirectLinkError("Direct link not found")

            return link_match.group(1), filename, headers, None

        except requests.exceptions.RequestException as e:
            raise DirectLinkError(f"Network error: {str(e)}") from e
        
        
def get_filename(url):
    response = requests.get(url, headers=headers, timeout=10)
    response.raise_for_status()

    _handle_errors(response)
    # Extract filename from HTML
    filename_match = re.search(
        r'<td class="normal">([^<]+)</td>',
        response.text
    )
    filename = sanitize_filename(filename_match.group(1)) if filename_match else None
    
    # Fallback filename extraction from URL if needed
    if not filename:
        filename = unquote(url.split('/')[-1].split('?')[0]) or "unknown_file"
    return filename