import re
class UnsupportedServiceError(Exception):
    pass
def get_direct_link(link):
    from darkloader.darkloader import get_filename_from_url
    match = re.search(r"/u/([a-zA-Z0-9]+)", link)
    if match:
        file_id = match.group(1)
        direct_link =  f"https://pixeldrain.com/api/file/{file_id}"
        filename = get_filename_from_url(direct_link)
        if not filename:
            raise UnsupportedServiceError("Invalid Pixeldrain link")
        return direct_link, filename, None, None
    raise UnsupportedServiceError("Invalid Pixeldrain link")

def get_filename(link):
    from darkloader.darkloader import get_filename_from_url
    match = re.search(r"/u/([a-zA-Z0-9]+)", link)
    if match:
        file_id = match.group(1)
        direct_link =  f"https://pixeldrain.com/api/file/{file_id}"
        filename = get_filename_from_url(direct_link)
        if not filename:
            raise UnsupportedServiceError("Invalid Pixeldrain link")
        return filename
    raise UnsupportedServiceError("Invalid Pixeldrain link")