import streamlit as st
import pandas as pd

st.title("📦 Mi Inventario TVC")

# Crear una tabla de prueba
datos = {
    'Producto': ['Cámara Hikvision', 'Cable UTP', 'Monitor'],
    'Stock': [10, 50, 5]
}
df = pd.DataFrame(datos)

st.write("### Lista de productos actuales:")
st.table(df)

st.success("¡Si ves esto, tu programa ya funciona!")
