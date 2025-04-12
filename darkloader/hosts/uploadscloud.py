import requests
from bs4 import BeautifulSoup
import logging
import time
import sys
from darkloader.logger import setup_logger
logger = setup_logger(__name__)

def get_direct_link(url):
    """
    Extract direct download link from a webpage.
    
    Args:
        url (str): The URL of the webpage containing the download form
        
    Returns:
        tuple: (filename, direct_url, response_time, content_type)
        
    Raises:
        ValueError: If form is not found or redirection fails
        requests.RequestException: For any request-related errors
    """
    start_time = time.time()
    logger.info(f"Starting direct link extraction for URL: {url}")
    
    try:
        # Configure session to maintain cookies
        session = requests.Session()
        logger.debug("Created new requests session")
        
        # Get initial HTML
        logger.debug(f"Sending GET request to: {url}")
        response = session.get(url)
        response.raise_for_status()
        
        request_time = time.time() - start_time
        logger.debug(f"Initial GET request completed in {request_time:.2f} seconds")
        logger.debug(f"Response status code: {response.status_code}")
        logger.debug(f"Response headers: {response.headers}")
        
        # Parse HTML with BeautifulSoup
        logger.debug("Parsing HTML with BeautifulSoup")
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Find filename from span with class "dfilename"
        filename_elem = soup.find("span", {"class": "dfilename"})
        if not filename_elem:
            logger.error("Filename element not found in the page")
            raise ValueError("Filename element not found in the page")
            
        filename = filename_elem.text
        logger.info(f"Found filename: {filename}")
        
        # Find the form by name (F1)
        form = soup.find('form', {'name': 'F1'})
        if not form:
            logger.error("Form 'F1' not found in the page")
            raise ValueError("Form 'F1' not found in the page")
        
        logger.debug(f"Found form with action: {form.get('action', 'No action specified')}")
        
        # Extract all form fields
        form_data = {}
        for input_tag in form.find_all('input'):
            name = input_tag.get('name')
            value = input_tag.get('value', '')
            if name:
                form_data[name] = value
        
        logger.debug(f"Extracted form data: {form_data}")
        
        # Submit form without following redirects
        post_url = form.get('action', url)  # Use form action if available, otherwise use the same URL
        logger.info(f"Submitting form to: {url}")
        
        post_response = session.post(url, data=form_data, allow_redirects=False)
        post_response.raise_for_status()
        
        logger.debug(f"POST response status code: {post_response.status_code}")
        logger.debug(f"POST response headers: {post_response.headers}")
        
        # Get the redirection location
        if 300 <= post_response.status_code < 400:
            direct_url = post_response.headers.get('Location')
            if not direct_url:
                logger.error("Redirection header 'Location' not found in response")
                raise ValueError("Redirection header 'Location' not found in response")
                
            logger.info(f"Successfully extracted direct link: {direct_url}")
            
            return direct_url, filename, None, None
        else:
            logger.error(f"Expected redirection (3xx) status code, but got: {post_response.status_code}")
            raise ValueError(f"Expected redirection status code, but got: {post_response.status_code}")
            
    except requests.RequestException as e:
        logger.error(f"Request error: {str(e)}")
        raise
    except ValueError as e:
        logger.error(f"Value error: {str(e)}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        raise

