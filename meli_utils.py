import requests

def get_meli_item_id(query):
    """Busca un producto en Mercado Libre y devuelve el item_id del primero encontrado."""
    url = f"https://api.mercadolibre.com/sites/MLM/search?q={query}"
    resp = requests.get(url)
    if resp.status_code != 200:
        return None
    data = resp.json()
    results = data.get("results", [])
    if not results:
        return None
    return results[0].get("id")
