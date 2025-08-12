import streamlit as st
import pandas as pd
import os
from scraper import scrape_product_info

CSV_FILE = "products.csv"

# Cargar CSV o crearlo
if os.path.exists(CSV_FILE):
    products_df = pd.read_csv(CSV_FILE, dtype={"SKU": str})
else:
    products_df = pd.DataFrame(columns=[
        "SKU", "Name", "Description", "Price", "Stock Available", "URL", "Last Updated", "item_id"
    ])

st.title("Scraper Home Depot + Mercado Libre")

sku_input = st.text_input("Introduce SKU de Home Depot")

if st.button("Agregar SKU"):
    if sku_input:
        data = scrape_product_info(sku_input)
        if data:
            products_df = pd.concat([products_df, pd.DataFrame([data])], ignore_index=True)
            products_df.to_csv(CSV_FILE, index=False)
            st.success(f"Producto {sku_input} agregado.")
        else:
            st.error("No se pudo obtener información del producto.")

if not products_df.empty:
    st.dataframe(products_df)
    st.download_button(
        "Descargar CSV",
        data=products_df.to_csv(index=False),
        file_name="products.csv",
        mime="text/csv"
    )
