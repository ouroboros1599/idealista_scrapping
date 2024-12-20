import requests
from bs4 import BeautifulSoup
import json
import random
import time
from datetime import datetime
import re
import urllib.parse as urlparse

# --- Configuración inicial ---
base_url = "https://www.idealista.com/geo/venta-viviendas/andalucia/"
user_agents = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 Safari/537.36"
]

properties = []

# Sesión global para manejar cookies
session = requests.Session()

def get_random_headers():
    return {
        "User-Agent": random.choice(user_agents),
        "Accept-Language": "es-ES,es;q=0.9,en;q=0.8",
        "Referer": "https://www.google.com/",
    }

def accept_cookies():
    """ Simula la aceptación de cookies inicial """
    headers = get_random_headers()
    session.get("https://www.idealista.com/", headers=headers)

def extract_lat_lon(map_url):
    """Extrae latitud y longitud desde la URL del mapa."""
    try:
        query = urlparse.urlparse(map_url).query
        params = urlparse.parse_qs(query)
        center = params.get('center', [None])[0]
        if center:
            lat, lon = map(float, center.split(','))
            return lat, lon
        return None, None
    except Exception as e:
        print(f"❌ Error al extraer lat/lon: {e}")
        return None, None

def extract_administrative_areas(soup):
    """Extrae áreas administrativas desde el bloque de ubicación."""
    try:
        header_map = soup.find('div', id='headerMap')
        area_list = header_map.find_all('li', class_='header-map-list') if header_map else []
        areas = [area.get_text(strip=True) for area in area_list]

        return {
            "administrativeAreaLevel4": areas[0] if len(areas) > 0 else None,
            "administrativeAreaLevel3": areas[1] if len(areas) > 1 else None,
            "administrativeAreaLevel2": areas[2] if len(areas) > 2 else None,
            "administrativeAreaLevel1": areas[3] if len(areas) > 3 else None,
        }
    except Exception as e:
        print(f"❌ Error al extraer áreas administrativas: {e}")
        return {}

def extract_utag_data(soup):
    """Extrae datos avanzados desde el objeto utag_data en el JavaScript embebido."""
    try:
        script_tag = soup.find('script', text=re.compile(r'var utag_data ='))
        if not script_tag:
            return {}

        script_content = script_tag.string
        json_data_match = re.search(r'var utag_data = ({.*});', script_content)
        if not json_data_match:
            return {}

        utag_data = json.loads(json_data_match.group(1))
        ad_data = utag_data.get('ad', {})
        characteristics = ad_data.get('characteristics', {})
        condition = ad_data.get('condition', {})

        return {
            "locationId": ad_data.get('address', {}).get('locationId'),
            "roomNumber": characteristics.get('roomNumber'),
            "bathNumber": characteristics.get('bathNumber'),
            "constructedArea": characteristics.get('constructedArea'),
            "energyCertificationType": ad_data.get('energyCertification', {}).get('type'),
            "swimmingPool": bool(int(characteristics.get('hasSwimmingPool', 0))),
            "floor": characteristics.get('floor'),
            "status": (
                "excellent" if condition.get('isNewDevelopment') == "1" else
                "good" if condition.get('isGoodCondition') == "1" else
                "bad" if condition.get('isNeedsRenovating') == "1" else None
            ),
            "isSuitableForRecommended": bool(int(ad_data.get('isSuitableForRecommended', 0)))
        }
    except Exception as e:
        print(f"❌ Error al extraer utag_data: {e}")
        return {}

def extract_multimedia(soup):
    """Extrae URLs de imágenes y etiquetas multimedia."""
    multimedia = {
        "images": [],
        "videos": []
    }
    image_tags = soup.find_all('img', {'src': True})
    for img in image_tags:
        multimedia["images"].append({
            "url": img['src'],
            "tag": img.get('alt', 'image'),
            "localizedName": img.get('alt', 'image'),
            "deeplinkUrl": img.get('data-url', '')
        })
    return multimedia

def extract_data_from_html(soup):
    """ Extrae los datos necesarios del HTML y los organiza según idealista.json """
    data = {
        "adid": None,
        "price": None,
        "priceInfo": {"amount": None, "currencySuffix": None},
        "operation": "sale",
        "propertyType": "homes",
        "state": "active",
        "multimedia": {"images": [], "videos": []},
        "ubication": {"title": None, "latitude": None, "longitude": None, "administrativeAreas": {}},
        "moreCharacteristics": [],
    }

    # ID del anuncio
    adid_tag = soup.find('div', class_='ad-reference-container')
    if adid_tag:
        adid = adid_tag.find('p', class_='txt-ref')
        if adid:
            data["adid"] = adid.get_text(strip=True)

    # Precio
    price_tag = soup.find('span', class_='info-data-price')
    if price_tag:
        price = price_tag.get_text(strip=True).replace('€', '').replace('.', '')
        data["price"] = int(price)
        data["priceInfo"] = {"amount": int(price), "currencySuffix": "€"}

    # Ubicación
    location_tag = soup.find('span', class_='main-info__title-minor')
    if location_tag:
        data["ubication"]["title"] = location_tag.get_text(strip=True)

    # Latitud y Longitud
    map_tag = soup.find('div', class_='map')
    map_url = map_tag.get('data-url') if map_tag else None
    lat, lon = extract_lat_lon(map_url)
    data["ubication"]["latitude"] = lat
    data["ubication"]["longitude"] = lon

    # Áreas administrativas
    data["ubication"]["administrativeAreas"] = extract_administrative_areas(soup)

    # Multimedia
    data["multimedia"] = extract_multimedia(soup)

    # Datos avanzados de utag_data
    data.update(extract_utag_data(soup))

    # Extract "moreCharacteristics"
    more_characteristics = soup.find_all('li', class_='feature-list-item')
    for characteristic in more_characteristics:
        characteristic_text = characteristic.get_text(strip=True)
        if characteristic_text:
            data["moreCharacteristics"].append(characteristic_text)

    return data

def scrape_page(page_url):
    """Procesa una página completa y extrae todas las propiedades."""
    headers = get_random_headers()
    response = session.get(page_url, headers=headers)
    soup = BeautifulSoup(response.text, 'html.parser')

    property_links = soup.find_all('a', class_='item-link')
    for link in property_links:
        property_url = f"https://www.idealista.com{link['href']}"
        print(f"🛠️ Extrayendo datos de: {property_url}")
        response = session.get(property_url, headers=headers)
        property_soup = BeautifulSoup(response.text, 'html.parser')
        properties.append(extract_data_from_html(property_soup))
        time.sleep(random.uniform(1, 3))

def main():
    accept_cookies()
    page = 1
    while True:
        print(f"\n🔎 Procesando página {page}...")
        paginated_url = f"{base_url}?pagina={page}"
        try:
            scrape_page(paginated_url)
            time.sleep(random.uniform(2, 5))
        except Exception as e:
            print(f"❌ Error en la página {page}: {e}")
            break

        headers = get_random_headers()
        response = session.get(paginated_url, headers=headers)
        soup = BeautifulSoup(response.text, 'html.parser')
        next_button = soup.find('a', class_='icon-arrow-right-after')
        if not next_button:
            print("✅ No hay más páginas disponibles.")
            break

        page += 1

    # Guardar resultados
    output_file = "idealista_output.json"
    with open(output_file, "w", encoding="utf-8") as file:
        json.dump(properties, file, ensure_ascii=False, indent=4)
    print(f"\n✅ Datos guardados en {output_file}")

if __name__ == "__main__":
    main()
