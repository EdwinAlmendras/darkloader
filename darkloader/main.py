import aiohttp
import os
from pathlib import Path
from typing import Optional, Tuple, Callable, Any
import asyncio
from darkloader.hosts import downloadgg, gofile, onefichier, pixeldrain, ranoz
from darkloader.hosts import desiupload
from darkloader.hosts import uploadscloud
from aiohttp import ClientResponseError
import requests
import re
import os
from urllib.parse import unquote, urlparse
from typing import Union
from darkloader.debrid.mega_debrid import MegaDebrid
from darkloader.logger import setup_logger
from dotenv import load_dotenv
load_dotenv()
def sanitaze_name(filename):
    # Caso 1: Renombrar archivos con '--7_' al final
    if re.search(r'--7_\.', filename):
        base_name, ext = os.path.splitext(filename)
        base_name = re.sub(r'--7_$', '', base_name)
        new_filename = f"{base_name}.7z"
        return new_filename

    # Caso 2: Renombrar archivos con '.7z_7--XXX_'
    match = re.search(r'\.7z_7--(\d+)_\.', filename)
    if match:
        part_number = int(match.group(1))
        part_suffix = f".{part_number:03d}"
        new_filename = re.sub(r'\.7z_7--\d+_\.', f'.7z{part_suffix}.', filename)
        return str(new_filename)

    # Caso 3: Renombrar archivos con '_-7--XXX_'
    match = re.search(r'(.+)_-7--(\d+)_\..+', filename)
    if match:
        base_name = match.group(1)  # Nombre base del archivo
        part_number = int(match.group(2))  # Número de parte
        return f"{base_name}.7z.{part_number:03d}"

    return filename 


def get_filename_from_url(url):
    try:
        response = requests.head(url, allow_redirects=True)
        if 'Content-Disposition' in response.headers:
            content_disposition = response.headers['Content-Disposition']
            filename_match = re.search(r'filename="?([^"]+)"?', content_disposition)
            if filename_match:
                return unquote(filename_match.group(1))
        path = urlparse(url).path
        filename = os.path.basename(path)
        if '?' in filename:
            filename = filename.split('?')[0]
            
        if filename and '.' in filename:
            return unquote(filename)

        url_filename_match = re.search(r'/([^/]+\.[a-zA-Z0-9]{2,5})($|\?)', url)
        if url_filename_match:
            return unquote(url_filename_match.group(1))
        
        return "unknown_file"
        
    except Exception as e:
        print(f"Error al obtener el nombre de archivo: {e}")
        return "download_error"
    


class FileDownloaderError(Exception):
    """Base exception for downloader errors"""

class UnsupportedServiceError(FileDownloaderError):
    """Raised for unsupported download services"""


# SUPPORTED LINKS GOFILE DOWNLOAD.GG 1FICHIER PIXELDRAIN RANOZ
class BaseDownloader:
    """Base class for file downloaders with common functionality"""
    DEFAULT_HEADERS: dict = {"User-Agent": "Mozilla/5.0"}

    def __init__(
        self, 
        download_dir: str = "downloads",
        log_level: str = "INFO",
    ) -> None:
        self.download_dir = Path(download_dir)
        self._ensure_download_directory()
        self.logger = setup_logger("DarkLoader", log_level)
        self.logger.info(f"Initialized downloader with download directory: {download_dir}")

    def _ensure_download_directory(self) -> None:
        """Create download directory if it doesn't exist"""
        if not self.download_dir.exists():
            self.download_dir.mkdir(parents=True, exist_ok=True)

    def is_downloaded(self, file_path: Path, file_size: int) -> Union[Path, str]:
        """Check if file exists and has correct size
        
        Args:
            file_path: Path to check
            file_size: Expected file size in bytes
            
        Returns:
            Path if file exists with correct size, empty string otherwise
        """
        self.logger.debug(f"Checking if {file_path} exists and matches size {file_size}")
        if not file_path.exists():
            self.logger.debug(f"File {file_path} does not exist")
            return ""
        saved_file_size = file_path.stat().st_size 
        if saved_file_size == file_size:
            self.logger.debug(f"File {file_path} exists with correct size")
            return file_path
            
        self.logger.debug(f"File size mismatch - expected {file_size}, got {saved_file_size}")
        return ""

    def get_file_url_size(self, url: str, headers: dict) -> int:
        """Get file size from URL using HEAD request
        
        Args:
            url: File URL
            headers: Request headers
            
        Returns:
            File size in bytes, 0 if request fails
        """
        self.logger.debug(f"Getting file size for URL: {url}")
        try:
            response = requests.head(url, headers=headers)
            response.raise_for_status()
            size = int(response.headers.get("Content-Length", 0))
            self.logger.debug(f"File size: {size} bytes")
            return size
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Error getting file size: {e}")
            return 0


class FileDownloader(BaseDownloader):
    """Handles the actual file downloading process"""
    
    async def download_from_url(
        self,
        url: str,
        save_path: Path,
        method: str = "GET",
        headers: Optional[dict] = None,
        data: Optional[dict] = None,
        progress_cb: Optional[Callable[[str, int, int], Any]] = None
    ) -> str:
        """Async download with progress support for GET and POST methods
        
        Args:
            url: Download URL
            save_path: Path to save file
            method: HTTP method (GET/POST)
            headers: Request headers
            data: POST data if applicable
            progress_cb: Progress callback function
            
        Returns:
            Path to downloaded file as string
            
        Raises:
            FileDownloaderError: On download failure
        """
        save_path.parent.mkdir(parents=True, exist_ok=True)
        headers = headers or self.DEFAULT_HEADERS
        self.logger.info(f"Starting download from {url} to {save_path}")
        self.logger.debug(f"Using method: {method}, headers: {headers}")

        try:
            async with aiohttp.ClientSession() as session:
                if method.upper() == "POST":
                    self.logger.debug(f"Making POST request with data: {data}")
                    async with session.post(url, headers=headers, data=data) as response:
                        response.raise_for_status()
                        return await self._stream_response(response, save_path, progress_cb)
                else:
                    self.logger.debug("Making GET request")
                    async with session.get(url, headers=headers) as response:
                        response.raise_for_status()
                        return await self._stream_response(response, save_path, progress_cb)
        except ClientResponseError as e:
            if e.status == 404:
                self.logger.error("File not found (404)")
                raise FileDownloaderError("File Not Found")
            else:
                self.logger.error(f"HTTP error {e.status}: {e.message}")
                raise FileDownloaderError(f"Error HTTP: {e.status} - {e.message}")
        except Exception as e:
            self.logger.warning(f"Download failed, retrying in 3s: {e}")
            await asyncio.sleep(3)
            return await self.download_from_url(url, save_path, method, headers, data, progress_cb)
        
    async def _stream_response(
        self, 
        response: aiohttp.ClientResponse, 
        save_path: Path, 
        progress_cb: Optional[Callable[[str, int, int], Any]]
    ) -> str:
        """Handle response streaming with progress updates
        
        Args:
            response: aiohttp response
            save_path: Path to save file
            progress_cb: Progress callback function
            
        Returns:
            Path to downloaded file as string
            
        Raises:
            FileDownloaderError: If response is invalid
        """
        total_bytes = int(response.headers.get("Content-Length", 0))
        self.logger.info(f"Starting download stream, total size: {total_bytes} bytes")
        
        if response.headers.get("Content-Type") == "text/html" or total_bytes == 0:
            self.logger.error("Invalid response: HTML content or zero bytes")
            await asyncio.sleep(2)
            raise FileDownloaderError("Server Responded With Invalid File")

        processed_bytes = 0
        chunk_size = 26214400  # 25MB chunks

        with save_path.open("wb") as file:
            async for chunk in response.content.iter_chunked(chunk_size):
                file.write(chunk)
                processed_bytes += len(chunk)
                self.logger.debug(f"Downloaded {processed_bytes}/{total_bytes} bytes")
                
                if progress_cb:
                    await progress_cb(save_path.name, processed_bytes, total_bytes)

        self.logger.info(f"Download completed: {save_path}")
        return str(save_path)


class LinkResolver:
    """Resolves direct download links from various hosting services"""
    DEFAULT_HEADERS: dict = {"User-Agent": "Mozilla/5.0"}
    
    def __init__(self, log_level: str = "DEBUG"):
        self.logger = setup_logger("LinkResolver", log_level)
        self.gofile_client = gofile.Client()
        self.debrid = MegaDebrid("DEBUG")
        self.hosts_to_debrid = ["rapidgator.net", "1fichier.com"]
        
    def get_filename(self, url: str) -> str:
        """Get filename from URL based on host service
        
        Args:
            url: Download URL
            
        Returns:
            Extracted filename
        """
        self.logger.debug(f"Getting filename for URL: {url}")
        if "gofile.io" in url:
            filename = self.gofile_client.get_filename(url)
        elif "ranoz.gg" in url:
            raise Exception("ranoz.gg links are not supported because Cloudflare is blocking the request") #TODO: Add support for ranoz.gg
            filename = ranoz.get_filename(url)
        elif "download.gg" in url:
            filename = downloadgg.get_filename(url)
        elif "1fichier.com" in url:
            filename = onefichier.get_filename(url)
        elif "pixeldrain.com" in url:
            filename = pixeldrain.get_filename(url)
        else:
            filename = get_filename_from_url(url)
        self.logger.info(f"Extracted filename: {filename}")
        return filename

    async def get_direct_link(self, url: str) -> Tuple[str, str, dict, Optional[dict]]:
        """Get direct download link for supported services
        
        Args:
            url: Original download URL
            
        Returns:
            Tuple containing:
            - Direct download URL
            - Filename
            - Headers dict
            - Optional POST data dict
            
        Raises:
            Exception: For unsupported services
        """
        self.logger.info(f"Getting direct link for URL: {url}")
        domain = urlparse(url).netloc.lower()
        
        match domain:
            case domain if "gofile.io" in domain:
                self.logger.debug("Processing gofile.io URL")
                return self.gofile_client.get_direct_link(url)
            case domain if "ranoz.gg" in domain:
                self.logger.debug("Processing ranoz.gg URL") 
                raise Exception("ranoz.gg links are not supported because Cloudflare is blocking the request") #TODO: Add support for ranoz.gg
            case domain if "1fichier.com" in domain:
                self.logger.debug("Processing 1fichier.com URL")
                return onefichier.get_direct_link(url)
            case domain if "oshi.at" in domain:
                self.logger.error("oshi.at links are not supported")
                raise Exception("oshi.at is currently not resolved by laws.")
            case domain if "pixeldrain.com" in domain:
                self.logger.debug("Processing pixeldrain.com URL")
                return pixeldrain.get_direct_link(url)
            case domain if "uploadscloud.com" in domain:
                self.logger.debug("Processing uploadscloud.com URL")
                return uploadscloud.get_direct_link(url)
            case domain if "download.gg" in domain:
                self.logger.debug("Processing download.gg URL")
                return downloadgg.get_direct_link(url)
            case domain if "desiupload.co" in domain:
                self.logger.debug("Processing desiupload.co URL")
                return desiupload.get_direct_link(url)
            case domain if domain in self.hosts_to_debrid:
                def is_running_in_colab():
                    # check if importlib is available
                    import importlib
                    return importlib.util.find_spec("google.colab") is not None
                if is_running_in_colab():
                    self.logger.debug("Running in Colab")
                    link_unmasked = get_unmasked_link(url)
                    self.logger.debug(f"Link unmasked: {link_unmasked}")
                    return link_unmasked, get_filename_from_url(link_unmasked), self.DEFAULT_HEADERS, None
                self.logger.debug(f"Processing {domain} URL with debrid")
                direct_link = self.debrid.get_debrid_link(url)
                filename = get_filename_from_url(direct_link)
                return direct_link, filename, self.DEFAULT_HEADERS, None
            case _:
                self.logger.debug("Using direct URL")
                # check if the url is a valid direct url to download like content disposition not html
                response = requests.head(url, headers=self.DEFAULT_HEADERS)
                if "Content-Disposition" in response.headers:
                    return url, get_filename_from_url(url), self.DEFAULT_HEADERS, None
                else:
                    raise Exception("Invalid direct URL")

    def _extract_oshi_filename(self, url: str) -> str:
        """Extract filename from Oshi.at URL
        
        Args:
            url: Oshi.at URL
            
        Returns:
            Extracted filename or 'unknown_file'
        """
        filename = Path(urlparse(url).path).name or "unknown_file"
        self.logger.debug(f"Extracted oshi.at filename: {filename}")
        return filename

def get_unmasked_link(url):
    """
    Obtiene el link desenmascarado del servidor MegaDebrid.
    
    Args:
        url (str): URL de Mega a desenmascarar
        
    Returns:
        str: URL desenmascarada o None si hay error
    """
    try:
        API_URL_MEGA_DEBRID = os.getenv("API_URL_MEGA_DEBRID")
        if not API_URL_MEGA_DEBRID:
            raise Exception("API_URL_MEGA_DEBRID is not set")
        server_url = f"{API_URL_MEGA_DEBRID}/unmask"
        response = requests.post(
            server_url,
            json={"url": url}
        )
        response.raise_for_status()
        if response.status_code == 200:
            return response.json()["unmasked_url"]
        else:
            raise(f"Error al desenmascarar URL: {response.json()}")
            
    except Exception as e:
        raise


class DarkLoader:
    """Async file downloader for multiple hosting services"""

    def __init__(
        self, 
        download_dir: str = "downloads",
        log_level: str = "DEBUG"
    ) -> None:
        self.download_dir = Path(download_dir)
        self.logger = setup_logger("DarkLoader", log_level)
        self.logger.info(f"Initialized DarkLoader with download directory: {download_dir}")
        
        # Initialize component classes
        self.downloader = FileDownloader(download_dir, log_level)
        self.link_resolver = LinkResolver(log_level)

    async def download_url(
        self, 
        url: str,
        dl_path: Optional[Path] = None,
        progress_cb: Optional[Callable[[str, int, int], Any]] = None
    ) -> str:
        """Main download entry point
        
        Args:
            url: Download URL
            dl_path: Optional custom download path
            progress_cb: Optional progress callback
            
        Returns:
            Path to downloaded file as string
        """
        self.logger.info(f"Starting download process for URL: {url}")
        download_path = dl_path or self.downloader.download_dir
        
        direct_link, filename, headers, data = await self.link_resolver.get_direct_link(url)
        self.logger.debug(f"Direct link info: {direct_link}, {filename}, {headers}")
        
        sanitized_name = sanitaze_name(filename)
        final_path = Path(download_path) / sanitized_name
        self.logger.debug(f"Final download path: {final_path}")
        
        file_size = self.downloader.get_file_url_size(direct_link, headers=headers)
        
        if existing_file := self.downloader.is_downloaded(final_path, file_size):
            self.logger.info(f"File already exists: {existing_file}")
            return existing_file
        
        self.logger.info("Starting file download")
        output_path = await self.downloader.download_from_url(
            direct_link, 
            final_path,
            headers=headers,
            data=data,
            method="POST" if data else "GET",
            progress_cb=progress_cb
        )
        self.logger.info(f"Download completed: {output_path}")
        return output_path


print("Running DarkLoader example")