import requests
from bs4 import BeautifulSoup
from datetime import datetime
from meli_utils import get_meli_item_id

def scrape_product_info(sku):
    """Extrae datos de un producto de Home Depot y busca su item_id en Mercado Libre."""
    base_url = "https://www.homedepot.com.mx/producto/"
    url = f"{base_url}{sku}"
    resp = requests.get(url)

    if resp.status_code != 200:
        return None

    soup = BeautifulSoup(resp.text, "html.parser")

    # Ejemplo de extracción
    name = soup.find("h1")
    name = name.text.strip() if name else "Sin nombre"

    description = soup.find("div", class_="product-description")
    description = description.text.strip() if description else "Sin descripción"

    price_tag = soup.find("span", class_="price")
    price = price_tag.text.strip() if price_tag else "N/A"

    stock_tag = soup.find("div", class_="availability-msg")
    stock = stock_tag.text.strip() if stock_tag else "Desconocido"

    # Buscar item_id en Mercado Libre
    item_id = get_meli_item_id(sku)

    return {
        "SKU": sku,
        "Name": name,
        "Description": description,
        "Price": price,
        "Stock Available": stock,
        "URL": url,
        "Last Updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "item_id": item_id
    }
