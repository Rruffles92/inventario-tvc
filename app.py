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

# --- FUNCIONES DE PERSISTENCIA (GUARDADO FÍSICO) ---
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

# Inicializar estados de sesión
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
        st_lottie(lottie_robot, height=120, key="robot_sidebar")
    st.markdown("<h3 style='text-align: center;'>Asistente Virtual</h3>", unsafe_allow_html=True)
    st.markdown("---")
    opcion = st.radio("Navegar a:", ["📊 Stock Actual", "📥 Registrar Entrada", "📤 Retirar Producto", "💾 Reportes Excel"])
    st.markdown("---")
    st.markdown("### 🛠️ *Consultas IA*")
    pregunta = st.text_input("Pregúntame sobre el stock:")
    if pregunta and not st.session_state.inventario_data.empty:
        df_ia = st.session_state.inventario_data
        res = df_ia[df_ia.apply(lambda r: pregunta.lower() in str(r).lower(), axis=1)]
        if not res.empty: st.dataframe(res[['clave', 'nombre', 'cajas']], hide_index=True)

# --- SECCIÓN: STOCK ACTUAL ---
if opcion == "📊 Stock Actual":
    st.header("📋 Inventario Editable")
    df = st.session_state.inventario_data
    if df.empty:
        st.info("No hay productos registrados.")
    else:
        editado = st.data_editor(df, use_container_width=True, num_rows="dynamic")
        if st.button("💾 Guardar cambios permanentes"):
            st.session_state.inventario_data = editado
            guardar_datos(editado)
            st.success("✅ ¡Datos guardados en el archivo CSV!")

# --- SECCIÓN: REGISTRAR ENTRADA ---
elif opcion == "📥 Registrar Entrada":
    st.header("📥 Entrada de Mercancía")
    with st.form("form_in", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            sku = st.text_input("Clave").strip()
            nom = st.text_input("Nombre")
        with col2:
            ubi = st.text_input("Ubicación")
        c1, c2, c3 = st.columns(3)
        with c1: c_cajas = st.number_input("Cajas", min_value=0, value=1)
        with c2: c_cap = st.number_input("Piezas por Caja", min_value=1, value=1)
        with c3: c_sueltas = st.number_input("Piezas Sueltas", min_value=0, value=0)
        
        if st.form_submit_button("🚀 Guardar"):
            if sku and nom: # Corrección Línea 131
                df = st.session_state.inventario_data
                if sku.lower() in df['clave'].astype(str).str.lower().values:
                    idx = df[df
