import requests
from bs4 import BeautifulSoup
import json
import time
import random
from datetime import datetime

# --- Configuración inicial ---
base_url = "https://www.idealista.com/geo/venta-viviendas/andalucia/"
user_agents = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36"
]

properties = []

# Sesión global para manejar cookies
session = requests.Session()

# Función para obtener encabezados aleatorios
def get_random_headers():
    return {
        "User-Agent": random.choice(user_agents),
        "Accept-Language": "es-ES,es;q=0.9,en;q=0.8",
        "Referer": "https://www.google.com/",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "Cache-Control": "max-age=0"
    }

# Función para aceptar cookies y establecer la sesión
def accept_cookies():
    try:
        headers = get_random_headers()
        url = "https://www.idealista.com/"
        print("🔄 Realizando una petición inicial para aceptar cookies...")
        session.get(url, headers=headers, timeout=10)
        print("✅ Cookies aceptadas correctamente.")
    except requests.exceptions.RequestException as e:
        print(f"❌ Error al aceptar cookies: {e}")

# Función para extraer los detalles del anuncio
def scrape_details(url):
    try:
        headers = get_random_headers()
        response = session.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.text, 'html.parser')

        # Extracción de datos
        data = {}

        # Referencia del anuncio
        ref_tag = soup.find('p', class_='txt-ref')
        data['Ref anuncio'] = ref_tag.get_text(strip=True) if ref_tag else None

        # Título del anuncio
        title_tag = soup.find('span', class_='main-info__title-main')
        data['Título Anuncio'] = title_tag.get_text(strip=True) if title_tag else None

        # Ubicación
        location_tag = soup.find('span', class_='main-info__title-minor')
        data['Calle y Número'] = location_tag.get_text(strip=True) if location_tag else None

        # Precio de venta
        price_tag = soup.find('span', class_='info-data-price')
        data['Precio Venta'] = price_tag.get_text(strip=True).replace('€', '').strip() if price_tag else None

        # Superficie construida, habitaciones, planta
        features = soup.find('div', class_='info-features')
        if features:
            spans = features.find_all('span')
            data['Superficie Construida'] = spans[0].get_text(strip=True) if len(spans) > 0 else None
            data['Dormitorios'] = spans[1].get_text(strip=True) if len(spans) > 1 else None
            data['Planta'] = spans[2].get_text(strip=True) if len(spans) > 2 else None

        # Características básicas
        details_section = soup.find('div', class_='details-property')
        if details_section:
            details_features = details_section.find_all('li')
            data['Más Características'] = [feature.get_text(strip=True) for feature in details_features]

        # Certificado energético
        energy_cert = soup.find('h2', string="Certificado energético")
        if energy_cert:
            cert_list = energy_cert.find_next('ul')
            cert_items = cert_list.find_all('li') if cert_list else []
            data['Calificación Energética'] = (
                cert_items[0].get_text(strip=True) if cert_items else "En trámite"
            )

        # URL del portal
        data['URL Portal'] = url

        # Fecha de extracción
        data['Fecha Extracción'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        return data

    except Exception as e:
        print(f"❌ Error al extraer detalles: {e}")
        return None


# Función para scrapeo general de las propiedades
def scrape_properties(url, page_number):
    try:
        headers = get_random_headers()
        response = session.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.text, 'html.parser')

        # Enlaces a las propiedades en la página
        property_links = soup.find_all('a', class_='item-link')
        for link in property_links:
            property_url = f"https://www.idealista.com{link['href']}"
            print(f"Extrayendo datos de {property_url}")
            details = scrape_details(property_url)
            if details:
                properties.append(details)

        return True

    except requests.exceptions.RequestException as e:
        print(f"❌ Error al realizar la solicitud en la página {page_number}: {e}")
        return False


# --- Bucle principal para paginación ---
accept_cookies()  # Aceptamos cookies antes de iniciar el scraping
page = 1
while page <= 3:  # Cambia el límite según lo necesites
    print(f"\n--- Página {page} ---")
    paginated_url = f"{base_url}?pagina={page}"
    success = scrape_properties(paginated_url, page)
    if not success:
        break

    time.sleep(random.uniform(3, 10))  # Espera entre solicitudes
    page += 1

# --- Guardar resultados en JSON ---
output_file = "propiedades.json"
with open(output_file, "w", encoding="utf-8") as file:
    json.dump(properties, file, ensure_ascii=False, indent=4)
print(f"\n✅ Datos exportados correctamente a {output_file}")
