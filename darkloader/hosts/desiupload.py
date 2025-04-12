import re
import time
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse, urljoin, unquote

def get_direct_link(url):
    session = requests.Session()
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept-Language": "en-US,en;q=0.9",
    }
    
    # Primera solicitud para obtener parámetros iniciales y cookies
    response = session.get(url, headers=headers)
    if response.status_code != 200:
        raise Exception(f"Error al cargar la página: {response.status_code}")
    
    soup = BeautifulSoup(response.text, 'html.parser')
    
    # Verificar si el archivo existe
    error_messages = soup.find_all(text=re.compile(r'File Not Found|No such file|File was deleted'))
    if error_messages:
        raise Exception("El archivo no existe o fue eliminado")
    
    # Extraer parámetros del formulario
    form = soup.find('form', {'name': 'F1'})
    if not form:
        raise Exception("No se encontró el formulario de descarga")
    
    post_url = urljoin(url, form.get('action', ''))
    post_data = {
        'op': form.find('input', {'name': 'op'}).get('value', ''),
        'id': form.find('input', {'name': 'id'}).get('value', ''),
        'rand': form.find('input', {'name': 'rand'}).get('value', ''),
        'referer': form.find('input', {'name': 'referer'}).get('value', ''),
        'method_free': '',
        'method_premium': '',
        'adblock_detected': '',
        'code': ''
    }
    
    # Extraer y resolver CAPTCHA (versión HTML del script original)
    captcha_div = soup.find('div', style=lambda s: 'width:80px;height:26px' in str(s))
    captcha_spans = captcha_div.find_all('span', style=re.compile(r'position:absolute')) if captcha_div else []
    
    captcha_digits = {}
    for span in captcha_spans:
        style = span.get('style', '')
        # Determinar posición por padding-left
        padding_left = re.search(r'padding-left:(\d+)px', style)
        if not padding_left: continue
        print(padding_left.group(1))
        px_value = int(padding_left.group(1))
        # Misma lógica de agrupamiento que el script original
        if px_value <= 19: group = 1
        elif 20 <= px_value <= 29: group = 2
        elif 40 <= px_value <= 49: group = 3
        elif 60 <= px_value <= 69: group = 4
        else: continue
        print(span)
        # Extraer valor Unicode del span
        digit = span.get_text()
        if digit and digit.isdigit():
            captcha_digits[group] = int(digit)
        else:
            # Fallback: si BeautifulSoup no decodificó el carácter
            raw_span = repr(span.encode('unicode-escape'))
            unicode_match = re.search(r'\\u([0-9a-fA-F]{4})', raw_span)
            if unicode_match:
                captcha_digits[group] = int(unicode_match.group(1), 16) - 48
    # Construir código CAPTCHA en orden
    print(captcha_digits)
    captcha_code = ''.join(str(captcha_digits.get(i, '')) for i in [1,2,3,4])
    print(f"CAPTCHA resuelto: {captcha_code}")
    if len(captcha_code) != 4:
        raise Exception("No se pudo resolver el CAPTCHA")
    
    post_data['code'] = captcha_code
    
    # Espera de 15 segundos como el original
    print("Esperando 15 segundos...")
    time.sleep(15)
    
    # Enviar formulario con CAPTCHA
    response = session.post(post_url, data=post_data, headers=headers)
    soup = BeautifulSoup(response.text, 'html.parser')
    
    # Extraer enlace directo
    direct_link_tag = soup.find('span', {'id': 'direct_link'}).find('a') if soup.find('span', {'id': 'direct_link'}) else None
    if not direct_link_tag:
        raise Exception("No se encontró el enlace directo")
    
    direct_url = urljoin(url, direct_link_tag.get('href', ''))
    
    # Obtener nombre del archivo
    #filename_tag = soup.find('nobr', text=re.compile(r'Filename:'))
    #filename = unquote(re.search(r'<b>(.*?)</b>', str(filename_tag)).group(1)) if filename_tag else direct_url.split('/')[-1]
    
    # Obtener headers finales
    head_response = session.head(direct_url, headers=headers)
    
    content_disposition = head_response.headers.get('Content-Disposition', '')
    filename = None
    if content_disposition:
        filename = extract_filename_from_cd(content_disposition)

    if not filename:
        filename_tag = soup.find('nobr', text=re.compile(r'Filename:'))
        if filename_tag:
            filename = unquote(re.search(r'<b>(.*?)</b>', str(filename_tag)).group(1))

    # 3. Si todo falla, extrae del URL directo
    if not filename:
        filename = unquote(direct_url.split('/')[-1].split('?')[0])  # Limpia parámetros URL

    # Limpieza adicional (opcional)
    # filename = re.sub(r'[<>:"/\\|?*]', '_', filename) 
    final_headers = dict(head_response.headers)  # Copia los headers originales
    cookies_str = "; ".join([f"{k}={v}" for k, v in session.cookies.get_dict().items()])
    headers["Cookie"] = cookies_str
    
    return direct_url, filename, headers, None

import re
from urllib.parse import unquote

def extract_filename_from_cd(content_disposition):
    # Regex mejorado para filename/filename* según RFC 6266
    filename_match = re.search(
        r'''(?x)                    # Verbose mode
        (?:                         # Grupo no capturador para las opciones
            filename\*?=([^;]+)     # Opción 1: filename* o filename (grupo 1)
            |                       # O
            filename\s*=\s*         # Opción 2: filename tradicional
            (?:                     # Subgrupo para comillas
                "((?:\\"|[^"])*)"   # Grupo 2: entre comillas (permite \" escapados)
                |                   # O
                ([^;\n]*)           # Grupo 3: sin comillas
            )
        )
        ''',
        content_disposition,
        re.IGNORECASE
    )
    if not filename_match:
        return None

    # Prioridad: filename* (RFC 5987) > filename entre comillas > filename sin comillas
    filename = (
        filename_match.group(1) or    # filename*
        filename_match.group(3) or    # filename="..."
        filename_match.group(4)       # filename=...
    ).strip()

    # Limpieza y unquote (para %20, etc.)
    return unquote(filename.strip('"\''))

def get_filename(url):
    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')
    filename_tag = soup.find('nobr', text=re.compile(r'Filename:'))
    filename = unquote(re.search(r'<b>(.*?)</b>', str(filename_tag)).group(1)) if filename_tag else url.split('/')[-1]
    return filename