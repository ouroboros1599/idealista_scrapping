import requests
from bs4 import BeautifulSoup
import json
import time
import random

# --- Configuración inicial ---
base_url = "https://www.idealista.com/geo/venta-viviendas/andalucia/"
user_agents = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36"
]

# Ya no se usa proxy, elimina la lista de proxies
# proxies = [
#     "http://usuario:password@proxy_host:puerto",
#     "http://proxy2_host:puerto"
# ]

all_properties = []

# Crear una sesión para manejar cookies y encabezados
session = requests.Session()

def get_random_headers():
    """Generar encabezados aleatorios simulando navegadores."""
    return {
        "User-Agent": random.choice(user_agents),
        "Accept-Language": "es-ES,es;q=0.9,en;q=0.8",
        "Referer": "https://www.google.com/",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "Cache-Control": "max-age=0"
    }

# Elimina la función get_random_proxy ya que no usaremos proxies
# def get_random_proxy():
#     """Seleccionar un proxy aleatorio de la lista."""
#     return {"http": random.choice(proxies), "https": random.choice(proxies)} if proxies else None

def scrape_page(url, page_number):
    """Función para realizar scraping de una página específica."""
    try:
        headers = get_random_headers()
        
        # Ya no pasamos proxies aquí
        response = session.get(url, headers=headers, timeout=10)
        response.raise_for_status()  # Detectar errores HTTP

        # Validar si el contenido esperado está presente
        if "No hemos encontrado resultados" in response.text:
            print(f"⚠️ Fin de resultados en la página {page_number}.")
            return False

        soup = BeautifulSoup(response.text, 'html.parser')
        properties = soup.find_all('article', class_='item')

        if not properties:
            print("⚠️ No se encontraron propiedades. Posible cambio en la estructura del sitio.")
            return False

        for idx, property in enumerate(properties, start=1):
            title_tag = property.find('a', class_='item-link')
            title = title_tag.get_text(strip=True) if title_tag else "Título no encontrado"

            price_tag = property.find('span', class_='item-price')
            price = price_tag.get_text(strip=True) if price_tag else "Precio no disponible"

            location_tag = property.find('span', class_='item-location')
            location = location_tag.get_text(strip=True) if location_tag else "Ubicación no disponible"

            link = f"https://www.idealista.com{title_tag['href']}" if title_tag and title_tag.get('href') else "Sin enlace"

            all_properties.append({
                "title": title,
                "price": price,
                "location": location,
                "link": link
            })

            print(f"{idx}. {title} - {price} - {location}\n   Enlace: {link}")

        return True

    except requests.exceptions.RequestException as e:
        print(f"❌ Error al realizar la solicitud en la página {page_number}: {e}")
        return False

# --- Bucle principal para paginación ---
page = 1
while True:
    print(f"\n--- Página {page} ---")
    paginated_url = f"{base_url}?pagina={page}"
    success = scrape_page(paginated_url, page)
    
    if not success:
        break

    # Pausa aleatoria entre solicitudes
    time.sleep(random.uniform(3, 10))  # Espera entre 3 y 7 segundos

    page += 1

# --- Guardar resultados en JSON ---
output_file = "propiedades.json"
with open(output_file, "w", encoding="utf-8") as file:
    json.dump(all_properties, file, ensure_ascii=False, indent=4)
print(f"\n✅ Datos exportados correctamente a {output_file}")
