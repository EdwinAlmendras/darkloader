
import re
from urllib.parse import quote, urlparse
from bs4 import BeautifulSoup
from darkloader.host import Host, DirectLinkResult, FileNotFoundError
from typing import Optional

class Ranoz(Host):
    def __init__(self, url: Optional[str], proxies: Optional[dict] = None):
        super().__init__("Ranoz", "ranoz.gg", r"https?://ranoz\.gg/d/\w+")
        self.proxies = proxies
        self.url = url
        self.session.allow_redirects = True
    def get_direct_link(self, url) -> DirectLinkResult:
        target_url = self._get_target_url(url)
        response = self.session.get(url, proxies=self.proxies)
        response.raise_for_status()
        html = response.text
        self._check_is_alive(html)
        filename = self._get_name_from_html(html)
        download_url = self._match_direct_link(html)
        if not filename:
            filename = self._get_filename_from_direct_link(download_url)
        return {
            "url": download_url,
            "filename": filename,
            "headers": self.session.headers,
    }
    def _check_is_alive(self, html) -> bool:
        if re.search(r"There is no such file|UNAVAILABLE_FOR_LEGAL_REASONS|File was deleted because", html, re.I):
            raise FileNotFoundError("file dont exist or deleted.")
    def _match_direct_link(self, html) -> str:
        url_match = re.search(r'\\"props\\":\{\}\},\\"href\\":\\"(.*?)\\"', html)
        if url_match:
            download_url = url_match.group(1)
            if self._is_already_download_url(download_url):
                parts = download_url.split('/')
                filename_part = parts[-1].split('?')[0]
                encoded_filename = quote(filename_part, safe='').replace('.', '%2E')
                parts[-1] = encoded_filename + '?' + parts[-1].split('?')[1]
                download_url = '/'.join(parts)
        if not download_url:
            raise ValueError("Cant get download url.")
        return download_url
    def _is_already_download_url(self, url: str) -> bool:
        parsed = urlparse(url)
        has_query = bool(parsed.query)
        is_file = '.' in parsed.path.split('/')[-1]
        return has_query and is_file
    def get_filename(self, url):
        target_url = self._get_target_url(url)
        response = self.session.get(target_url)
        response.raise_for_status()
        return self._get_name_from_html(response.text)
                
    def _get_name_from_html(self, html):
        soup = BeautifulSoup(html, "html.parser")
        for div in soup.find_all("div"):
            if div.text.strip() == "Name":
                name_value_div = div.find_next_sibling("div")
                if name_value_div:
                    filename = name_value_div.text.strip()
                    break
        return filename
        
