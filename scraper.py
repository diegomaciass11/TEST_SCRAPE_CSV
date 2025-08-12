# scraper.py (versión corregida)
from selenium import webdriver
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import pandas as pd
from datetime import datetime
from meli_utils import obtener_item_id_por_sku   # asegúrate de tener este módulo

_driver = None  # cache del driver

def get_driver():
    global _driver
    if _driver is None:
        options = webdriver.ChromeOptions()
        options.add_argument('--headless')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-gpu')
        # options.binary_location = "/usr/bin/chromium"  # si lo necesitas
        service = Service(ChromeDriverManager(driver_version="120.0.6099.224").install())
        _driver = webdriver.Chrome(service=service, options=options)
        _driver.implicitly_wait(0)
    return _driver

def _safe_text(driver, by, selector):
    try:
        el = driver.find_element(by, selector)
        return el.text.strip()
    except Exception:
        return None

def scrape_product_info(sku: str, timeout_search=10):
    driver = get_driver()
    search_url = f"https://www.homedepot.com.mx/s/{sku}"
    driver.get(search_url)
    print(f"[INFO] Buscando SKU en: {search_url}")

    # 1) Intentamos detectar si la búsqueda redirigió directamente a la página de producto
    name = None
    try:
        name = WebDriverWait(driver, 5).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "h1.product-name"))
        ).text
        product_url = driver.current_url
        print(f"[INFO] Redirigido directo a producto: {product_url}")
    except TimeoutException:
        # 2) No hubo redirección directa -> esperamos y hacemos click en el primer resultado (/p/)
        try:
            link = WebDriverWait(driver, timeout_search).until(
                EC.element_to_be_clickable((By.XPATH, "//a[contains(@href,'/p/')]"))
            )
            product_url = link.get_attribute("href")
            print(f"[INFO] Abriendo primer resultado: {product_url}")
            driver.get(product_url)
            # ahora esperamos el nombre en la página de producto
            try:
                name = WebDriverWait(driver, 8).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "h1.product-name"))
                ).text
            except TimeoutException:
                # fallback a cualquier h1
                name = _safe_text(driver, By.TAG_NAME, "h1") or "Sin nombre"
        except TimeoutException:
            # no encontramos resultados buscables
            print(f"[WARN] No se encontró resultado /p/ en la búsqueda para SKU {sku}")
            return pd.DataFrame([{
                "SKU": sku,
                "Name": "No encontrado",
                "Description": "",
                "Price": "",
                "Stock Available": "",
                "URL": search_url,
                "Last Updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "item_id": None
            }])

    # 3) Cerrar popups si aparece alguno (silencioso)
    try:
        close_icon = WebDriverWait(driver, 2).until(
            EC.element_to_be_clickable((By.CLASS_NAME, "dialogStore--icon--highlightOff"))
        )
        close_icon.click()
    except TimeoutException:
        pass
    except Exception:
        pass

    # 4) Extraer descripción (varias opciones)
    description = None
    for sel in [
        "div.product-description",
        "div#product-description",
        "div[itemprop='description']",
        "p.MuiTypography-root"
    ]:
        description = _safe_text(driver, By.CSS_SELECTOR, sel)
        if description:
            break
    if not description:
        description = "Not found"

    # 5) Extraer precio (tratamos varios selectores y fallback con JS)
    price = None
    for sel in ["p.product-price", "span.price-format__main-price", "span.price", "div.price"]:
        txt = _safe_text(driver, By.CSS_SELECTOR, sel)
        if txt:
            price = txt
            break

    if not price:
        # intento con script para juntar nodos (igual que tu versión anterior)
        try:
            price_elem = driver.find_element(By.CSS_SELECTOR, "p.product-price")
            js_script = """
            var element = arguments[0];
            var mainText = '';
            var supText = '';
            var supCount = 0;
            for (var i = 0; i < element.childNodes.length; i++) {
                var node = element.childNodes[i];
                if (node.nodeType === Node.TEXT_NODE) {
                    mainText += node.textContent.trim();                
                } else if (node.nodeType === Node.ELEMENT_NODE && node.tagName === 'SUP') {
                    supCount++;
                    if (supCount === 2) {
                        supText = node.textContent.trim();
                    }
                }
            }
            return mainText + (supText ? ('.' + supText) : '');
            """
            price = driver.execute_script(js_script, price_elem).replace(',', '').strip()
        except Exception:
            price = "Not found"

    # 6) Extraer stock (buscamos textos que contengan 'disponible' o 'disponibles')
    stock = None
    try:
        stock_elem = driver.find_element(
            By.XPATH,
            "//p[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'disponible') or contains(., 'disponibles')]"
        )
        stock_digits = ''.join(c for c in stock_elem.text if c.isdigit())
        stock = int(stock_digits) if stock_digits else stock_elem.text.strip()
    except Exception:
        # fallback: buscar cualquier texto con 'agotado' o 'no disponible'
        try:
            no_disp = driver.find_element(By.XPATH, "//*[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'agotado') or contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'no disponible')]")
            stock = "0 (" + no_disp.text.strip() + ")"
        except Exception:
            stock = "Not found"

    # 7) Obtener item_id de Mercado Libre (si tienes el módulo)
    try:
        item_id = obtener_item_id_por_sku(sku)
    except Exception as e:
        print(f"[WARN] Error buscando item_id en Mercado Libre: {e}")
        item_id = None

    # 8) Resultado
    return pd.DataFrame([{
        "SKU": sku,
        "Name": name or "Sin nombre",
        "Description": description,
        "Price": price,
        "Stock Available": stock,
        "URL": driver.current_url,
        "Last Updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "item_id": item_id
    }])
