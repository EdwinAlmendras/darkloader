import requests
from bs4 import BeautifulSoup
import io
import logging
import time
import re
from core.captcha_solver.ocr_captcha import CaptchaOCR
# Configurar logging para depuración
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

ocr_processor = CaptchaOCR()

  
def _fetch_initial_page(session, url):
    """Obtiene la página inicial y extrae los datos del formulario."""
    logger.debug(f"Obteniendo página inicial: {url}")
    response = session.get(url)
    if response.status_code != 200:
        logger.error(f"Fallo al obtener la página inicial. Código de estado: {response.status_code}")
        return None
    
    soup = BeautifulSoup(response.text, 'html.parser')
    try:
        post_op = soup.find('input', {'name': 'op'})['value']
        post_id = soup.find('input', {'name': 'id'})['value']
        post_fname = soup.find('input', {'name': 'fname'})['value']
        logger.debug(f"Datos extraídos - op: {post_op}, id: {post_id}, fname: {post_fname}")
        return {'op': post_op, 'id': post_id, 'fname': post_fname}
    except (TypeError, KeyError) as e:
        logger.error(f"Error al extraer datos del formulario inicial: {e}")
        return None

def _fetch_captcha_page(session, url, initial_data):
    """Envía el formulario inicial y obtiene la página con el captcha."""
    form_data = {
        'op': initial_data['op'],
        'usr_login': '',
        'id': initial_data['id'],
        'fname': initial_data['fname'],
        'referer': '',
        'method_free': 'Free Download >>'
    }
    logger.debug(f"Enviando formulario inicial: {form_data}")
    response = session.post(url, data=form_data)
    if response.status_code != 200:
        logger.error(f"Fallo al enviar formulario inicial. Código de estado: {response.status_code}")
        return None
    
    soup = BeautifulSoup(response.text, 'html.parser')
    captcha_img = soup.find('img', {'src': re.compile(r'https://anonfile.de/captchas/')})
    if not captcha_img:
        logger.error("No se encontró imagen de captcha en la página")
        return None
    
    captcha_url = captcha_img['src']
    logger.debug(f"URL del captcha encontrada: {captcha_url}")
    
    # Descargar la imagen del captcha
    captcha_response = session.get(captcha_url)
    if captcha_response.status_code != 200:
        logger.error(f"Fallo al descargar la imagen del captcha. Código de estado: {captcha_response.status_code}")
        return None
    
    
    # Resolver el captcha con pytesseract
    result = ocr_processor.process_image(
        io.BytesIO(captcha_response.content),
        data_type="NUMBERONLY",
        extra_params="ContrastStretch_5x90 Brightness_130"
    )
    if len(result) != 4:
        logger.error(f"Código de captcha inválido: {result}")
        return None
    logger.debug(f"Código de captcha resuelto: {result}")
    
    # Extraer datos adicionales del formulario
    try:
        post_op = soup.find('input', {'name': 'op'})['value']
        post_id = soup.find('input', {'name': 'id'})['value']
        post_rand = soup.find('input', {'name': 'rand'})['value']
        post_referer = soup.find('input', {'name': 'referer'})['value']
        logger.debug(f"Datos del formulario con captcha - op: {post_op}, id: {post_id}, rand: {post_rand}, referer: {post_referer}")
        return {
            'op': post_op,
            'id': post_id,
            'rand': post_rand,
            'referer': post_referer,
            'code': captcha_code
        }
    except (TypeError, KeyError) as e:
        logger.error(f"Error al extraer datos del formulario con captcha: {e}")
        return None

def _fetch_download_link(session, url, captcha_data):
    """Envía el formulario con el captcha y obtiene el enlace de descarga."""
    form_data = {
        'op': captcha_data['op'],
        'id': captcha_data['id'],
        'rand': captcha_data['rand'],
        'referer': captcha_data['referer'],
        'method_free': 'Free Download >>',
        'method_premium': '',
        'adblock_detected': '',
        'code': captcha_data['code']
    }
    logger.debug(f"Enviando formulario con captcha: {form_data}")
    time.sleep(5)  # Esperar 5 segundos como en el script original
    response = session.post(url, data=form_data)
    if response.status_code != 200:
        logger.error(f"Fallo al enviar formulario con captcha. Código de estado: {response.status_code}")
        return None
    
    soup = BeautifulSoup(response.text, 'html.parser')
    download_link_tag = soup.find('a', {'class': 'stretched-link'})
    if not download_link_tag:
        logger.error("No se encontró el enlace de descarga")
        return None
    
    download_link = download_link_tag['href']
    filename = download_link.split('/')[-1]
    logger.debug(f"Enlace de descarga encontrado: {download_link}, Nombre del archivo: {filename}")
    return download_link, filename

def get_direct_link(url):
    """
    Obtiene el enlace directo de descarga desde una URL de anonfile.de.
    
    Args:
        url (str): La URL del archivo en anonfile.de.
    
    Returns:
        tuple: (direct_link, filename, headers, cookies, data) o None si falla.
    """
    session = requests.Session()
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    session.headers.update(headers)
    logger.debug(f"Iniciando sesión con headers: {headers}")

    # Paso 1: Obtener datos de la página inicial
    initial_data = _fetch_initial_page(session, url)
    if not initial_data:
        return None

    # Paso 2: Obtener datos de la página con captcha
    captcha_data = _fetch_captcha_page(session, url, initial_data)
    if not captcha_data:
        return None

    # Paso 3: Obtener el enlace de descarga
    result = _fetch_download_link(session, url, captcha_data)
    if not result:
        return None
    
    download_link, filename = result
    return (download_link, filename, session.headers, session.cookies.get_dict(), None)
# Uso ejemplo:
