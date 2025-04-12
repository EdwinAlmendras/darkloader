import pytest
import requests
from unittest.mock import patch, MagicMock

from darkloader.debrid.mega_debrid import MegaDebrid

import re

def is_unrestrict_download_url(url: str) -> bool:
    """
    Validates if a URL is a valid unrestrict.link download URL.
    
    Args:
        url (str): The URL to validate
        
    Returns:
        bool: True if the URL matches the unrestrict.link download pattern, False otherwise
    """
    pattern = r'^https?://(?:www\d*\.)?unrestrict\.link/download/file/[a-zA-Z0-9]+/[^/]+$'
    return bool(re.match(pattern, url))

# Example usage
RAPIDGATOR_TEST_LINK = "https://rapidgator.net/file/d71e1b914795643965155fed0bac8b19/Penetration.Testing.and.Ethical.Hacking.02.19.part5.rar.html"
@pytest.fixture
def mega_debrid():
    return MegaDebrid()


class TestMegaDebrid:
    def get_direct_link(self, mega_debrid):
        return MegaDebrid().get_debrid_link(RAPIDGATOR_TEST_LINK)
    
    def test_get_token(self, mega_debrid):
        link = self.get_direct_link(mega_debrid)
        assert is_unrestrict_download_url(link)
