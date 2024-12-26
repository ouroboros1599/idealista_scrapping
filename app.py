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
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:90.0) Gecko/20100101 Firefox/90.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Edge/91.0.864.48",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 15_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.0 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (Linux; Android 11; SM-G973F) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/93.0.4577.62 Mobile Safari/537.36",
    "Mozilla/5.0 (iPad; CPU OS 14_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Mobile/15E148 Safari/604.1"
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
    """Simula la aceptación de cookies inicial."""
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
        script_tag = soup.find('script', string=re.compile(r'var utag_data ='))
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
            "ubication": {
                "locationId": ad_data.get('address', {}).get('locationId'),
            },
            "moreCharacteristics": {
                "communityCosts": characteristics.get('communityCosts'),
                "roomNumber": characteristics.get('roomNumber'),
                "isStudio": bool(int(characteristics.get('isStudio', 0))),
                "bathNumber": characteristics.get('bathNumber'),
                "exterior": bool(int(characteristics.get('isExterior', 0))),
                "housingFurnitures": bool(int(characteristics.get('hasFurniture', 0))),
                "isPenthouse": bool(int(characteristics.get('isPenthouse', 0))),
                "energyCertificationType": ad_data.get('energyCertification', {}).get('type'),
                "swimmingPool": bool(int(characteristics.get('hasSwimmingPool', 0))),
                "flatLocation": characteristics.get('flatLocation'),
                "modificationDate": ad_data.get('modificationDate'),
                "constructedArea": characteristics.get('constructedArea'),
                "lift": bool(int(characteristics.get('hasLift', 0))),
                "garden": bool(int(characteristics.get('hasGarden', 0))),
                "boxroom": bool(int(characteristics.get('hasBoxroom', 0))),
                "isDuplex": bool(int(characteristics.get('isDuplex', 0))),
                "floor": characteristics.get('floor'),
                "status": (
                    "excellent" if condition.get('isNewDevelopment') == "1" else
                    "good" if condition.get('isGoodCondition') == "1" else
                    "bad" if condition.get('isNeedsRenovating') == "1" else None
                ),
                "isSuitableForRecommended": bool(int(ad_data.get('isSuitableForRecommended', 0)))
            }
        }
    except Exception as e:
        print(f"❌ Error al extraer utag_data: {e}")
        return {"ubication": {}, "moreCharacteristics": {}}

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
    
# def extract_contact_info(soup):
#     """Extrae la información de contacto del HTML y obtiene los teléfonos a través de una solicitud AJAX."""
#     contact_info = {
#         "phone1": {
#             "phoneNumber": None,
#             "formattedPhone": None,
#             "prefix": None,
#             "phoneNumberForMobileDialing": None,
#             "nationalNumber": None,
#             "formattedPhoneWithPrefix": None
#         },
#         "phone2": {
#             "phoneNumber": None,
#             "formattedPhone": None,
#             "prefix": None,
#             "phoneNumberForMobileDialing": None,
#             "nationalNumber": None,
#             "formattedPhoneWithPrefix": None
#         },
#         "contactName": None,
#         "userType": None,
#         "contactMethod": "all",
#         "sharedSeekerProfile": False,
#         "totalAds": 0,
#         "professional": None,
#         "chatEnabled": None
#     }

#     # Obtener el data-adid del HTML
#     adid_tag = soup.find('a', class_='btn nav next icon-arrow-right-after --not-mobile', attrs={'data-adid': True})
#     if not adid_tag:
#         print("No se encontró el data-adid en el HTML.")
#         return contact_info

#     adid = adid_tag['data-adid']

#     # Contact Name
#     contact_name_tag = soup.find('div', class_='professional-name')
#     if contact_name_tag:
#         name_tag = contact_name_tag.find('input', {'name': 'user-name'})
#         if name_tag:
#             contact_info["contactName"] = name_tag['value'].strip()

#     # User Type
#     user_type_tag = soup.find('div', {'data-is-private-user': True})
#     if user_type_tag:
#         contact_info["userType"] = "private"
#         contact_info["professional"] = False
#     else:
#         contact_info["userType"] = "professional"
#         contact_info["professional"] = True

#     # Chat Enabled
#     chat_tag = soup.find('div', {'data-has-chat-enabled': True})
#     contact_info["chatEnabled"] = chat_tag is not None

#     # Realizar la solicitud AJAX para obtener los teléfonos utilizando adid
#     try:
#         url = f"https://www.idealista.com/es/ajax/ads/{adid}/contact-phones"
#         response = requests.get(url)
#         response.raise_for_status()
#         phones_data = response.json()  # Suponiendo que la respuesta es JSON

#         # Extraer y formatear los teléfonos si existen
#         if phones_data.get("phone1"):
#             phone1 = phones_data["phone1"]
#             contact_info["phone1"] = {
#                 "phoneNumber": phone1,
#                 "formattedPhone": f"{phone1[:3]} {phone1[3:5]} {phone1[5:]}",
#                 "prefix": "34",
#                 "phoneNumberForMobileDialing": f"+34{phone1}",
#                 "nationalNumber": True,
#                 "formattedPhoneWithPrefix": f"+34 {phone1[:3]} {phone1[3:5]} {phone1[5:]}"
#             }

#         if phones_data.get("phone2"):
#             phone2 = phones_data["phone2"]
#             contact_info["phone2"] = {
#                 "phoneNumber": phone2,
#                 "formattedPhone": f"{phone2[:3]} {phone2[3:5]} {phone2[5:]}",
#                 "prefix": "34",
#                 "phoneNumberForMobileDialing": f"+34{phone2}",
#                 "nationalNumber": True,
#                 "formattedPhoneWithPrefix": f"+34 {phone2[:3]} {phone2[3:5]} {phone2[5:]}"
#             }
    
#     except requests.exceptions.RequestException as e:
#         print(f"Error al realizar la solicitud AJAX: {e}")

#     # Teléfonos (extracción dinámica desde el HTML)
#     phone1_tag = soup.find('a', href=re.compile(r'tel:\+34'))
#     if phone1_tag:
#         phone1 = phone1_tag['href'].replace('tel:', '')
#         contact_info["phone1"] = {
#             "phoneNumber": phone1,
#             "formattedPhone": f"{phone1[:3]} {phone1[3:5]} {phone1[5:]}",
#             "prefix": "34",
#             "phoneNumberForMobileDialing": f"+34{phone1}",
#             "nationalNumber": True,
#             "formattedPhoneWithPrefix": f"+34 {phone1[:3]} {phone1[3:5]} {phone1[5:]}"
#         }

#     phone2_tag = soup.find('a', href=re.compile(r'tel:\+34'))
#     if phone2_tag and phone2_tag != phone1_tag:
#         phone2 = phone2_tag['href'].replace('tel:', '')
#         contact_info["phone2"] = {
#             "phoneNumber": phone2,
#             "formattedPhone": f"{phone2[:3]} {phone2[3:5]} {phone2[5:]}",
#             "prefix": "34",
#             "phoneNumberForMobileDialing": f"+34{phone2}",
#             "nationalNumber": True,
#             "formattedPhoneWithPrefix": f"+34 {phone2[:3]} {phone2[3:5]} {phone2[5:]}"
#         }

#     return contact_info


def translate_comment(comment_text, target_languages=[
            "ca",  # Català
            "en",  # English
            "fr",  # Français
            "de",  # Deutsch
            "it",  # Italiano
            "pt",  # Português
            "da",  # Dansk
            "fi",  # Suomi
            "no",  # Norsk
            "nl",  # Nederlands
            "pl",  # Polski
            "ro",  # Română
            "ru",  # русский 
            "sv",  # Svenska
            "el",  # Ελληνικά
            "zh-CN",  # 中文
            "uk",  # Українська
        ]): #añadir idiomas a elección
    """Traduce el comentario a los idiomas especificados."""
    translations = []
    
    # Traducir al idioma original (español)
    translations.append({
        "propertyComment": comment_text,
        "autoTranslated": False,
        "language": "es",
        "defaultLanguage": True
    })

    # Traducir a los otros idiomas
    for lang in target_languages:
        try:
            translated_text = GoogleTranslator(source='auto', target=lang).translate(comment_text)
            translations.append({
                "propertyComment": translated_text,
                "autoTranslated": True,
                "language": lang,
                "defaultLanguage": False
            })
        except Exception as e:
            print(f"❌ Error al traducir a {lang}: {e}")
    
    return translations

def extract_energy_certification(soup):
    """Extrae los detalles del certificado energetico"""
    energy_cerifications = []

    energy_features = soup.find('div', class_ = 'details-property-feature-two')
    if not energy_features:
        return []
    
    #iterar sobre las caracteristicas energéticas
    for item in energy_features.find_all('li'):
        prefix = item.find('span').get_text(strip = True) if item.find('span') else None
        icon_span = item.find('span', class_ = re.compile(r'icon-energy-c-[a-g]'))

        if icon_span: 
            suffix = icon_span['class'][0].split('-')[-1].upper()
            has_icon = True
        else:
            suffix = None
            has_icon = False

        energy_cerifications.append({
            "prefix": prefix,
            "suffix": suffix,
            "hasIcon": has_icon
        })

    return energy_cerifications

def check_offer_text(soup):
    """Busca el texto Hacer una contraoferta en todo el HTML de la página"""
    try: 
        page_text = soup.get_text()
        if "Hacer una contraoferta" in page_text:
            return True
        return False
    except Exception as e: 
        print(f"❌ Error al buscar el texto de la contraoferta: {e}")
        return False

def extract_remote_visit_and_360(soup):
    """
    Extrae los valores correspondientes a 'allowsRemoteVisit' y 'has360VHS' 
    a partir del bloque de datos de 'visit3DTour' en el HTML.
    """
    try:
        script_tag = soup.find('script', string=re.compile(r'visit3DTour'))
        if not script_tag:
            print("❌ No se encontró el bloque 'visit3DTour'.")
            return {"allowsRemoteVisit": False, "has360VHS": False}

        # Buscar la estructura JSON dentro del script
        script_content = script_tag.string
        json_data_match = re.search(r'visit3DTour:\s*(\[\{.*?\}\])', script_content, re.DOTALL)
        if not json_data_match:
            print("❌ No se pudo extraer los datos de 'visit3DTour'.")
            return {"allowsRemoteVisit": False, "has360VHS": False}

        # Parsear el JSON encontrado
        visit3D_data = json.loads(json_data_match.group(1))
        
        # Obtener los valores de '3d' y '360' del primer elemento de la lista
        if visit3D_data and isinstance(visit3D_data, list):
            first_entry = visit3D_data[0]
            allows_remote_visit = first_entry.get("3d", False)
            has_360_vhs = first_entry.get("360", False)

            return {
                "allowsRemoteVisit": allows_remote_visit,
                "has360VHS": has_360_vhs
            }

        return {"allowsRemoteVisit": False, "has360VHS": False}
    except Exception as e:
        print(f"❌ Error al extraer datos de 'visit3DTour': {e}")
        return {"allowsRemoteVisit": False, "has360VHS": False}

def check_mortgage_simluator(soup):
    """Busca el simulador de hipotecas en el HTML de la página."""
    simulator_section = soup.find("div", class_="item-form item-redils js-buying-price-slider buying-price")
    if not simulator_section:
        return False
    return True

def extract_data_from_html(soup):
    """Extrae los datos necesarios del HTML y los organiza según idealista.json."""
    data = {
        "adid": None,
        "price": None,
        "priceInfo": {  "amount": None, 
                        "currencySuffix": None},
        "operation": "sale",
        "propertyType": "homes",
        "state": "active",
        "multimedia": { "images": [], 
                        "videos": []},
        "propertyComment": None,
        "ubication": {  "title": None, 
                        "latitude": None, 
                        "longitude": None, 
                        "administrativeAreas": {}}, #falta el hasHidenAddress, administrativeAreaLevel1Id, locationName
        "country": "ES",
        # "contactInfo": {},   //testear
        "moreCharacteristics": {}, #communityCosts, roomNumber, isStudio, bathNumber, exterior, housingFurnitures, isPenthouse, energyCertificationType, swimmingPool, flatLocation, modaificationDate, constructedArea, lift, garden, boxroom, isDuplex, floor, status //corroborar con cliente si es necesario o no este elemento, ya que no se traduce nada de lo que existe aqui a otro lenguaje
        #translatedText (floorNumberDescription, layoutDescription, characteristicsDescriptions {key, title, phrases}) //corroborar con cliente si es necesario o no este elemento, ya que no se traduce nada de lo que existe aqui a
        #suggestedTexts (title) //no exsite dentro del html
        #detailedType (typology, subTypology) //no existe dentro del html
        "comments": [], 
        "detailWebLink": None,
        "energyCertification": [],
        "allowsCounterOffers": False,
        "allowsRemoteVisit": False, 
        "allowsMortgageSimulator": False,
        #allowsProfileQualification
        #tracking (isSuitableForRecommended)
        "has360VHS": False
        #labels
        #showSuggestedPrice
        #allowsRecommendation
        #modificationDate (value, text)
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
    utag_data = extract_utag_data(soup)
    data["ubication"].update(utag_data.get("ubication", {}))
    data["moreCharacteristics"].update(utag_data.get("moreCharacteristics", {}))

    # Datos de contacto
    #data["contactInfo"] = extract_contact_info(soup) descomentar

    # Comentarios y traducciones
    comment_tag = soup.find('div', class_='comment')
    if comment_tag: 
        comment = comment_tag.find('p')
        if comment:
            comment_text = comment.get_text(strip=True)
            data["comments"] = translate_comment(comment_text)

    # Enlace de la web scrapeada
    data["detailWebLink"] = soup.find('link', rel='canonical')['href']

    # Datos de certificación energética
    data["energyCertification"] = extract_energy_certification(soup)

    # Datos de si la oferta existe
    data["allowsCounterOffers"] = check_offer_text(soup)

    # Datos de visitas remotas y 360
    data["allowsRemoteVisit"] = extract_remote_visit_and_360(soup)["allowsRemoteVisit"]
    data["has360VHS"] = extract_remote_visit_and_360(soup)["has360VHS"]

    data["allowsMortgageSimulator"] = check_mortgage_simluator(soup)
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
            time.sleep(random.uniform(0, 1))
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
