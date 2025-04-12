# download.gg
from typing import Tuple
from bs4 import BeautifulSoup
import requests
def get_direct_link(url: str) -> Tuple[str, str, dict, dict]:
    response = requests.get(url)
    soup = BeautifulSoup(response.text, "html.parser")
    form = soup.find("form")
    action_url = form.get("action")
    payload = {inp["name"]: inp["value"] for inp in form.find_all("input", {"type": "hidden"})}
    filename = soup.select_one(".uploadProgress .name").get_text()
    cookies_dict = response.cookies.get_dict()  
    cookie_header = "; ".join([f"{k}={v}" for k, v in cookies_dict.items()])
    headers = {"Cookie": cookie_header}
    return action_url, filename, headers, payload
    
def get_filename(url: str) -> str:
    response = requests.get(url)
    soup = BeautifulSoup(response.text, "html.parser")
    filename = soup.select_one(".uploadProgress .name").get_text()
    return filename
    