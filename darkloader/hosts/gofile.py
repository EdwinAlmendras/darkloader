import requests
import hashlib
import os
from typing import Optional, Tuple, Any

class GoFileError(Exception):
    """Base exception for GoFile operations"""

class TokenError(GoFileError):
    """Failed to obtain or use API token"""

class APIError(GoFileError):
    """API response validation failed"""

class AuthenticationError(GoFileError):
    """Password required or incorrect"""

class ContentError(GoFileError):
    """Invalid content structure or missing data"""

class Client:
    def __init__(self):
        self.user_agent = os.getenv("GF_USERAGENT") or "Mozilla/5.0"
        self._token = os.getenv("GF_TOKEN") or self._get_token()

    def _get_token(self) -> str:
        """Fetch a new API token from GoFile"""
        try:
            response = requests.post(
                "https://api.gofile.io/accounts",
                headers={"User-Agent": self.user_agent},
                timeout=10
            )
            response.raise_for_status()
            data = response.json()
            
            if data.get("status") != "ok":
                raise TokenError("Failed to create anonymous account")
                
            return data["data"]["token"]
            
        except Exception as e:
            raise TokenError(f"Token acquisition failed: {str(e)}") from e
    def get_filename(self, url, password = None):
        content_id = self._extract_content_id(url)
        api_url = self._build_api_url(content_id, password)
        response = self._make_api_request(api_url)
        # is tuple the filename are in 1 position
        filename = self._parse_response(response, content_id)[1]
        return filename
    def get_direct_link(self, url: str, password: Optional[str] = None) -> Tuple[str, str, any, None]:
        try:
            content_id = self._extract_content_id(url)
            api_url = self._build_api_url(content_id, password)
            response = self._make_api_request(api_url)
            return *self._parse_response(response, content_id), None
            
        except GoFileError:
            raise
        except Exception as e:
            raise GoFileError(f"Operation failed: {str(e)}") from e

    def _extract_content_id(self, url: str) -> str:
        """Validate URL format and extract content ID"""
        parts = url.strip().split("/")
        if len(parts) < 3 or parts[-2] != "d":
            raise ValueError("Invalid GoFile URL format")
        return parts[-1]

    def _build_api_url(self, content_id: str, password: Optional[str]) -> str:
        """Construct API endpoint URL with parameters"""
        base_url = f"https://api.gofile.io/contents/{content_id}"
        params = "wt=4fd6sg89d7s6&cache=true&sortField=createTime&sortDirection=1"
        
        if password:
            hashed_pw = hashlib.sha256(password.encode()).hexdigest()
            params += f"&password={hashed_pw}"
            
        return f"{base_url}?{params}"

    def _make_api_request(self, api_url: str) -> dict:
        """Execute authenticated API request"""
        headers = {
            "User-Agent": self.user_agent,
            "Authorization": f"Bearer {self._token}"
        }
        self.headers = headers
        response = requests.get(api_url, headers=headers, timeout=15)
        response.raise_for_status()
        return response.json()

    def _parse_response(self, data: dict, content_id: str) -> Tuple[str, str, any]:
        """Validate and extract download link and filename from API response"""
        if data.get("status") != "ok":
            raise APIError(f"API Error: {data.get('message', 'Unknown error')}")
            
        content = data.get("data", {})
        
        if content.get("passwordStatus") == "passwordRequired":
            raise AuthenticationError("Password required")
        if content.get("passwordStatus") == "passwordIncorrect":
            raise AuthenticationError("Incorrect password")
            
        if content.get("type") == "file":
            return (content["link"], content["name"])
            
        if content.get("type") == "folder":
            for child in content.get("children", {}).values():
                if child.get("type") == "file":
                    return (child["link"], child["name"], self.headers)
            raise ContentError(f"No files found in folder {content_id}")
            
        raise ContentError("Unknown content type in response")