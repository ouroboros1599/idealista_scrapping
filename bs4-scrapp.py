import requests
from bs4 import BeautifulSoup
import json
import random
import time
from datetime import datetime
import re
import urllib.parse as urlparse
from deep_translator import GoogleTranslator

# --- Configuración inicial ---
base_url = "https://www.idealista.com/geo/venta-viviendas/andalucia/"
user_agents = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 Safari/537.36"
]

languages = ["en", "de", "pt"]  # Idiomas a traducir
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
    """Simula la aceptación de cookies inicial."""
    headers = get_random_headers()
    session.get("https://www.idealista.com/", headers=headers)

def translate_text(text, lang):
    """Traduce un texto a un idioma específico utilizando Google Translate."""
    try:
        return GoogleTranslator(source="es", target=lang).translate(text)
    except Exception as e:
        print(f"❌ Error al traducir: {e}")
        return text

def extract_comments(soup):
    """Extrae comentarios y genera traducciones."""
    comments_data = []
    comment_tag = soup.find('div', class_='comment')
    if comment_tag:
        comment = comment_tag.find('p')
        if comment:
            original_text = comment.get_text(strip=True)
            for lang in languages:
                translated_text = translate_text(original_text, lang)
                comments_data.append({
                    "propertyComment": translated_text,
                    "autoTranslated": lang != "es",
                    "language": lang,
                    "defaultLanguage": lang == "es"
                })
    return comments_data

def extract_data_from_html(soup):
    """Extrae los datos necesarios del HTML y los organiza según idealista.json."""
    data = {
        "adid": None,
        "price": None,
        "priceInfo": {"amount": None, "currencySuffix": None},
        "operation": "sale",
        "propertyType": "homes",
        "state": "active",
        "multimedia": {"images": [], "videos": []},
        "ubication": {"title": None, "latitude": None, "longitude": None, "administrativeAreas": {}},
        "moreCharacteristics": {},
        "comments": []
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

    # Comentarios
    data["comments"] = extract_comments(soup)

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
