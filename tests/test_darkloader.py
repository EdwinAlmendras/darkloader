import pytest
import asyncio
from pathlib import Path
import os
import tempfile
from unittest.mock import patch, MagicMock, AsyncMock

from darkloader.darkloader import (
    DarkLoader,
    FileDownloader,
    LinkResolver,
    BaseDownloader,
    sanitaze_name,
    get_filename_from_url,
    setup_logger,
    FileDownloaderError,
    UnsupportedServiceError
)


@pytest.fixture
def temp_download_dir():
    with tempfile.TemporaryDirectory() as tmpdirname:
        yield tmpdirname


@pytest.fixture
def dark_loader(temp_download_dir):
    return DarkLoader(download_dir=temp_download_dir, log_level="INFO")


@pytest.fixture
def file_downloader(temp_download_dir):
    return FileDownloader(download_dir=temp_download_dir, log_level="INFO")


@pytest.fixture
def link_resolver():
    return LinkResolver(log_level="INFO")


class TestSanitazeName:
    def test_sanitaze_name_with_7z_suffix(self):
        assert sanitaze_name("file--7_.ext") == "file.7z"

    def test_sanitaze_name_with_7z_part_number(self):
        assert sanitaze_name("file.7z_7--001_.ext") == "file.7z.001.ext"

    def test_sanitaze_name_with_part_suffix(self):
        assert sanitaze_name("file_-7--001_.ext") == "file.7z.001"

    def test_sanitaze_name_no_change(self):
        assert sanitaze_name("normal_file.ext") == "normal_file.ext"


class TestGetFilenameFromUrl:
    @patch("darkloader.darkloader.requests.head")
    def test_get_filename_from_content_disposition(self, mock_head):
        mock_response = MagicMock()
        mock_response.headers = {"Content-Disposition": 'attachment; filename="test_file.zip"'}
        mock_head.return_value = mock_response
        
        assert get_filename_from_url("http://example.com/download") == "test_file.zip"

    @patch("darkloader.darkloader.requests.head")
    def test_get_filename_from_url_path(self, mock_head):
        mock_response = MagicMock()
        mock_response.headers = {}
        mock_head.return_value = mock_response
        
        assert get_filename_from_url("http://example.com/files/test_file.zip") == "test_file.zip"

    @patch("darkloader.darkloader.requests.head")
    def test_get_filename_fallback(self, mock_head):
        mock_response = MagicMock()
        mock_response.headers = {}
        mock_head.return_value = mock_response
        
        assert get_filename_from_url("http://example.com/download") == "unknown_file"


class TestBaseDownloader:
    def test_init_creates_directory(self, temp_download_dir):
        test_dir = os.path.join(temp_download_dir, "test_subdir")
        downloader = BaseDownloader(download_dir=test_dir)
        assert Path(test_dir).exists()

    def test_is_downloaded_file_exists_correct_size(self, temp_download_dir, file_downloader):
        test_file = Path(temp_download_dir) / "test.txt"
        with open(test_file, "w") as f:
            f.write("test content")
        
        file_size = test_file.stat().st_size
        result = file_downloader.is_downloaded(test_file, file_size)
        assert result == test_file

    def test_is_downloaded_file_not_exists(self, temp_download_dir, file_downloader):
        test_file = Path(temp_download_dir) / "nonexistent.txt"
        result = file_downloader.is_downloaded(test_file, 100)
        assert result == ""

    def test_is_downloaded_wrong_size(self, temp_download_dir, file_downloader):
        test_file = Path(temp_download_dir) / "test.txt"
        with open(test_file, "w") as f:
            f.write("test content")
        
        wrong_size = test_file.stat().st_size + 10
        result = file_downloader.is_downloaded(test_file, wrong_size)
        assert result == ""

    @patch("darkloader.darkloader.requests.head")
    def test_get_file_url_size(self, mock_head, file_downloader):
        mock_response = MagicMock()
        mock_response.headers = {"Content-Length": "1024"}
        mock_head.return_value = mock_response
        
        size = file_downloader.get_file_url_size("http://example.com/file.zip", {})
        assert size == 1024


class TestFileDownloader:
    @pytest.mark.asyncio
    @patch("aiohttp.ClientSession")
    async def test_download_from_url_get(self, mock_session, file_downloader, temp_download_dir):
        mock_client = AsyncMock()
        mock_response = AsyncMock()
        mock_session.return_value.__aenter__.return_value = mock_client
        mock_client.get.return_value.__aenter__.return_value = mock_response
        
        mock_response.headers = {"Content-Length": "100", "Content-Type": "application/zip"}
        mock_response.content.iter_chunked.return_value.__aiter__.return_value = [b"test data"]
        
        save_path = Path(temp_download_dir) / "test_download.zip"
        
        result = await file_downloader.download_from_url(
            "http://example.com/file.zip",
            save_path
        )
        
        assert result == str(save_path)
        assert Path(result).exists()
        assert Path(result).read_bytes() == b"test data"


class TestLinkResolver:
    @pytest.mark.asyncio
    @patch("darkloader.darkloader.requests.head")
    async def test_get_direct_link_direct_url(self, mock_head, link_resolver):
        mock_response = MagicMock()
        mock_response.headers = {"Content-Disposition": 'attachment; filename="test.zip"'}
        mock_head.return_value = mock_response
        
        result = await link_resolver.get_direct_link("http://example.com/direct.zip")
        
        assert result[0] == "http://example.com/direct.zip"  # direct_link
        assert result[1] == "test.zip"  # filename
        assert result[2] == link_resolver.DEFAULT_HEADERS  # headers
        assert result[3] is None  # data


class TestDarkLoader:
    @pytest.mark.asyncio
    @patch.object(LinkResolver, "get_direct_link")
    @patch.object(FileDownloader, "get_file_url_size")
    @patch.object(FileDownloader, "download_from_url")
    async def test_download_url(self, mock_download, mock_get_size, mock_get_link, dark_loader, temp_download_dir):
        # Setup mocks
        mock_get_link.return_value = ("http://direct.link/file.zip", "file.zip", {}, None)
        mock_get_size.return_value = 1024
        mock_download.return_value = os.path.join(temp_download_dir, "file.zip")
        
        # Call the method
        result = await dark_loader.download_url("http://example.com/file.zip")
        
        # Verify
        assert result == os.path.join(temp_download_dir, "file.zip")
        mock_get_link.assert_called_once_with("http://example.com/file.zip")
        mock_get_size.assert_called_once()
        mock_download.assert_called_once()

    @pytest.mark.asyncio
    @patch.object(LinkResolver, "get_direct_link")
    @patch.object(FileDownloader, "get_file_url_size")
    @patch.object(FileDownloader, "is_downloaded")
    async def test_download_url_file_exists(self, mock_is_downloaded, mock_get_size, mock_get_link, dark_loader, temp_download_dir):
        # Setup mocks
        mock_get_link.return_value = ("http://direct.link/file.zip", "file.zip", {}, None)
        mock_get_size.return_value = 1024
        existing_file = os.path.join(temp_download_dir, "file.zip")
        mock_is_downloaded.return_value = existing_file
        
        # Call the method
        result = await dark_loader.download_url("http://example.com/file.zip")
        
        # Verify
        assert result == existing_file
        mock_get_link.assert_called_once_with("http://example.com/file.zip")
        mock_get_size.assert_called_once()
