import streamlit as st
import pandas as pd
import os
from io import BytesIO
from datetime import datetime
import requests
from streamlit_lottie import st_lottie

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="TVC Control Inventario", layout="wide", page_icon="🤖")
DB_FILE = "inventario_tvc.csv"
HISTORIAL_FILE = "historial_reportes.txt"

def cargar_datos():
    if os.path.exists(DB_FILE):
        return pd.read_csv(DB_FILE)
    return pd.DataFrame(columns=["clave", "nombre", "cajas", "piezas_por_caja", "piezas_sueltas", "ubicacion"])

def guardar_datos(df):
    df.to_csv(DB_FILE, index=False)

def cargar_historial():
    if os.path.exists(HISTORIAL_FILE):
        with open(HISTORIAL_FILE, "r") as f:
            return [line.strip() for line in f.readlines()]
    return []

def guardar_historial(lista):
    with open(HISTORIAL_FILE, "w") as f:
        for item in lista:
            f.write(f"{item}\n")

if "inventario_data" not in st.session_state:
    st.session_state.inventario_data = cargar_datos()
if "historial" not in st.session_state:
    st.session_state.historial = cargar_historial()

# --- ASISTENTE VIRTUAL ---
def load_lottieurl(url: str):
    try:
        r = requests.get(url, timeout=5)
        return r.json() if r.status_code == 200 else None
    except: return None

lottie_robot = load_lottieurl("https://lottie.host/8026131b-789d-4899-b903-f09d84656041/7zH665M5K1.json")

# --- SEGURIDAD ---
if "autenticado" not in st.session_state:
    st.session_state["autenticado"] = False

if not st.session_state["autenticado"]:
    st.title("🔐 Acceso TVC San Nicolás")
    password = st.text_input("Contraseña:", type="password")
    if st.button("Entrar"):
        if password == "TVCsanicolas":
            st.session_state["autenticado"] = True
            st.rerun()
        else: st.error("❌ Incorrecta")
    st.stop()

# --- BARRA LATERAL ---
with st.sidebar:
    if lottie_robot:
        st_lottie(lottie_robot, height=150, key="robot")
    st.markdown("<h3 style='text-align: center;'>Asistente Virtual</h3>", unsafe_allow_html=True)
    st.markdown("---")
    opcion = st.radio("Navegar a:", ["📊 Stock Actual", "📥 Registrar Entrada", "📤 Retirar Producto", "💾 Reportes Excel"])

# --- SECCIONES PRINCIPALES ---
if opcion == "📊 Stock Actual":
    st.header("📋 Inventario")
    df = st.session_state.inventario_data
    if df.empty:
        st.info("No hay productos.")
    else:
        st.dataframe(df, use_container_width=True)

elif opcion == "📥 Registrar Entrada":
    st.header("📥 Entrada")
    with st.form("form_in", clear_on_submit=True):
        sku = st.text_input("Clave")
        nom = st.text_input("Nombre")
        c_cajas = st.number_input("Cajas", min_value=1)
        if st.form_submit_button("Guardar"):
            df = st.session_state.inventario_data
            nueva = pd.DataFrame([[sku, nom, c_cajas, 0, 0, "Almacén"]], columns=df.columns)
            df = pd.concat([df, nueva], ignore_index=True)
            st.session_state.inventario_data = df
            guardar_datos(df)
            st.rerun()

elif opcion == "📤 Retirar Producto":
    st.header("📤 Retirar")
    # Lógica de retiro simple
    st.write("Selecciona un producto para retirar.")

# --- SECCIÓN: GESTIÓN DE REPORTES (LO QUE PEDISTE) ---
elif opcion == "💾 Reportes Excel":
    st.header("💾 Gestionar Reportes de Inventario")

    # 1. Crear nuevo reporte
    st.subheader("✨ Generar Nuevo Reporte")
    if not st.session_state.inventario_data.empty:
        fecha_hora = datetime.now().strftime("%d-%m-%Y_%Hh%Mm")
        nombre_sugerido = f"Reporte_{fecha_hora}.xlsx"
        
        if st.button(f"➕ Crear y Guardar Reporte: {nombre_sugerido}"):
            if nombre_sugerido not in st.session_state.historial:
                st.session_state.historial.append(nombre_sugerido)
                guardar_historial(st.session_state.historial)
                st.success(f"Reporte {nombre_sugerido} añadido a la lista.")
                st.rerun()
    
    st.divider()

    # 2. Lista de reportes con opciones individuales
    st.subheader("📂 Reportes Guardados")
    if st.session_state.historial:
        # Generamos el archivo Excel actual para descarga
        df_ex = st.session_state.inventario_data
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df_ex.to_excel(writer, index=False)
        excel_data = output.getvalue()

        for idx, nombre in enumerate(st.session_state.historial):
            col_nombre, col_descarga, col_borrar = st.columns([3, 1, 1])
            
            with col_nombre:
                st.write(f"📄 {nombre}")
            
            with col_descarga:
                st.download_button(
                    label="📥 Bajar",
                    data=excel_data,
                    file_name=nombre,
                    key=f"dl_{idx}"
                )
            
            with col_borrar:
                if st.button("🗑️ Eliminar", key=f"del_{idx}"):
                    st.session_state.historial.pop(idx)
                    guardar_historial(st.session_state.historial)
                    st.rerun()
    else:
        st.info("No hay reportes en la lista. Haz clic en 'Crear y Guardar' arriba.")
