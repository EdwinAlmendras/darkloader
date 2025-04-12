import requests
from darkloader.logger import setup_logger
import os
from dotenv import load_dotenv
load_dotenv()

USERNAME = os.getenv("MEGA_DEBRID_USERNAME")
PASSWORD = os.getenv("MEGA_DEBRID_PASSWORD")
TOKEN = os.getenv("MEGA_DEBRID_TOKEN")
    
class MegaDebrid:
    API_URL = "https://www.mega-debrid.eu/api.php"
    def __init__(self, log_level="INFO"):
        self.logger = setup_logger("MegaDebrid", log_level)
        self.logger.debug("MegaDebrid instance initialized")
        self.USERNAME = USERNAME
        self.PASSWORD = PASSWORD
        self.token = TOKEN

    def get_token(self) -> str:
        self.logger.debug(f"Getting token with username: {self.USERNAME}")
        params = {"action": "connectUser", "login": self.USERNAME, "password": self.PASSWORD}
        self.logger.debug(f"Sending GET request to {self.API_URL} with params: {params}")
        
        try:
            response = requests.get(self.API_URL, params=params)
            self.logger.debug(f"Response status code: {response.status_code}")
            self.logger.debug(f"Response: {response.text}")
            response.raise_for_status()
            response_json = response.json()
            self.logger.debug(f"Response JSON: {response_json}")
            
            self.token = response_json.get("token")
            if self.token:
                self.logger.info("Successfully obtained token")
                self.logger.debug(f"Token: {self.token}")
            else:
                self.logger.error("Failed to obtain token")
            
            return self.token
        except Exception as e:
            self.logger.error(f"Error getting token: {str(e)}")
            raise

    def get_debrid_link(self, url: str) -> str:
        self.logger.info(f"Getting debrid link for URL: {url}")
        if not self.token:
            self.logger.debug("Token not found, getting new token")
            self.get_token()
        
        try:
            response_debrid = self._post_debrid_request(url)
            debrid_link = self._parse_debrid_response(response_debrid)
            self.logger.info(f"Successfully obtained debrid link")
            self.logger.debug(f"Debrid link: {debrid_link}")
            return debrid_link
        except Exception as e:
            self.logger.error(f"Error getting debrid link: {str(e)}")
            raise

    def _post_debrid_request(self, url: str) -> requests.Response:
        self.logger.debug(f"Preparing debrid request for URL: {url}")
        params = {
            "action": "getLink",
            "token": self.token
        }
        data = {
            "link": url,
            "password": ""
        }
        
        self.logger.debug(f"Sending POST request to {self.API_URL}")
        self.logger.debug(f"Request params: {params}")
        self.logger.debug(f"Request data: {data}")
        
        try:
            response = requests.post(self.API_URL, params=params, data=data)
            self.logger.debug(f"Response status code: {response.status_code}")
            self.logger.debug(f"Response headers: {response.headers}")
            self.logger.debug(f"Response content: {response.text[:200]}...")  # Log first 200 chars
            return response
        except Exception as e:
            self.logger.error(f"Error in POST request: {str(e)}")
            raise

    def _parse_debrid_response(self, response: requests.Response) -> str:
        self.logger.debug("Parsing debrid response")
        try:
            data = response.json()
            self.logger.debug(f"Response JSON: {data}")
            
            if data.get("response_code") != "ok":
                error_message = data.get("response_text", "Unknown error")
                self.logger.error(f"API returned error: {error_message}")
                raise Exception(error_message)
            
            debrid_link = data.get("debridLink")
            if not debrid_link:
                self.logger.error("No debrid link found in response")
                raise Exception("No debrid link found in response")
                
            self.logger.debug(f"Successfully parsed debrid link: {debrid_link}")
            return debrid_link
        except Exception as e:
            self.logger.error(f"Error parsing response: {str(e)}")
            raise
