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

def cargar_datos():
    if os.path.exists(DB_FILE):
        return pd.read_csv(DB_FILE)
    return pd.DataFrame(columns=["clave", "nombre", "cajas", "piezas_por_caja", "piezas_sueltas", "ubicacion"])

def guardar_datos(df):
    df.to_csv(DB_FILE, index=False)

if "inventario_data" not in st.session_state:
    st.session_state.inventario_data = cargar_datos()

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
    pregunta = st.text_input("Pregúntame algo:")

# --- SECCIONES ---
if opcion == "📊 Stock Actual":
    st.header("📋 Inventario editable")
    df = st.session_state.inventario_data
    if df.empty:
        st.info("No hay productos.")
    else:
        editado = st.data_editor(df, use_container_width=True, num_rows="dynamic")
        if st.button("💾 Guardar cambios"):
            st.session_state.inventario_data = editado
            guardar_datos(editado)
            st.success("✅ Datos actualizados.")

elif opcion == "📥 Registrar Entrada":
    st.header("📥 Registrar Entrada")
    with st.form("form_in", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            sku = st.text_input("Clave")
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
                    idx = df[df['clave'].astype(str).str.lower() == sku.lower()].index[0]
                    df.at[idx, 'cajas'] += c_cajas
                else:
                    nueva = pd.DataFrame([[sku, nom, c_cajas, c_cap, c_sueltas, ubi]], columns=df.columns)
                    df = pd.concat([df, nueva], ignore_index=True)
                st.session_state.inventario_data = df
                guardar_datos(df)
                st.rerun()

elif opcion == "📤 Retirar Producto":
    st.header("📤 Retirar Producto")
    with st.form("form_out", clear_on_submit=True):
        sku_ret = st.text_input("Clave")
        r_caj = st.number_input("Cajas a retirar", min_value=0)
        if st.form_submit_button("✅ Confirmar"):
            df = st.session_state.inventario_data
            if sku_ret.lower() in df['clave'].astype(str).str.lower().values:
                idx = df[df['clave'].astype(str).str.lower() == sku_ret.lower()].index[0]
                df.at[idx, 'cajas'] = max(0, int(df.at[idx, 'cajas']) - r_caj)
                st.session_state.inventario_data = df
                guardar_datos(df)
                st.rerun()

elif opcion == "💾 Reportes Excel":
    st.header("💾 Exportar y Gestionar Reportes")
    
    # 1. SECCIÓN DE ELIMINACIÓN (ARRIBA)
    if "historial" in st.session_state and st.session_state.historial:
        st.subheader("🗑️ Eliminar Reportes del Historial")
        archivos_a_borrar = st.multiselect("Selecciona los reportes que ya no quieres ver:", st.session_state.historial)
        if st.button("❌ Eliminar seleccionados"):
            st.session_state.historial = [a for a in st.session_state.historial if a not in archivos_a_borrar]
            st.success("Lista actualizada.")
            st.rerun()
    else:
        st.info("No hay reportes en la lista para eliminar.")

    st.divider()

    # 2. SECCIÓN DE DESCARGA Y LISTA
    if not st.session_state.inventario_data.empty:
        df_ex = st.session_state.inventario_data.copy()
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df_ex.to_excel(writer, index=False)
        
        fecha = datetime.now().strftime("%d-%m-%Y_%Hh%Mm")
        nombre_archivo = f"TVC_Stock_{fecha}.xlsx"
        
        # Corrección Línea 132 (Paréntesis cerrado correctamente)
        st.download_button(label="📥 Descargar Reporte Actual", data=output.getvalue(), file_name=nombre_archivo)
        
        if st.button("✨ Añadir este reporte a la lista"):
            if "historial" not in st.session_state:
                st.session_state.historial = []
            st.session_state.historial.append(nombre_archivo)
            st.rerun()
