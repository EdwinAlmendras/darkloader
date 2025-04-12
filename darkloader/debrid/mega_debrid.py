import requests
import os

class MegaDebrid:
    API_URL = "https://www.mega-debrid.eu/api.php"
    USERNAME = os.getenv("MEGA_DEBRID_USERNAME")
    PASSWORD = os.getenv("MEGA_DEBRID_PASSWORD")

    def __init__(self):
        self.token = None

    def get_token(self) -> str:
        params = {"action": "connectUser", "login": self.USERNAME, "password": self.PASSWORD}
        response = requests.get(self.API_URL, params=params)
        print(response)
        print(response.json())
        self.token = response.json().get("token")
        return self.token

    def get_debrid_link(self, url: str) -> str:
        response_debrid = self._post_debrid_request(url)
        return self._parse_debrid_response(response_debrid)

    def _post_debrid_request(self, url: str) -> requests.Response:
        params = {
            "action": "getLink",
            "token": self.token
        }
        data = {
            "link": url,
            "password": ""
        }
        return requests.post(self.API_URL, params=params, data=data)

    def _parse_debrid_response(self, response: requests.Response) -> str:
        data = response.json()
        if data.get("response_code") != "ok":
            raise Exception(data.get("response_text"))
        return data.get("debridLink")
    
