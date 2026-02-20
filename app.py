import streamlit as st
import pandas as pd
import os
from io import BytesIO
from datetime import datetime
import requests
from streamlit_lottie import st_lottie

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="TVC Control Inventario", layout="wide", page_icon="🤖")
DB_FILE = "inventario_tvc.csv"

# Persistencia de datos física
def cargar_datos():
    if os.path.exists(DB_FILE):
        return pd.read_csv(DB_FILE)
    return pd.DataFrame(columns=["clave", "nombre", "cajas", "piezas_por_caja", "piezas_sueltas", "ubicacion"])

def guardar_datos(df):
    df.to_csv(DB_FILE, index=False)

if "inventario_data" not in st.session_state:
    st.session_state.inventario_data = cargar_datos()

# --- ASISTENTE VIRTUAL (Robot) ---
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

# --- BARRA LATERAL CON IA ---
with st.sidebar:
    if lottie_robot:
        st_lottie(lottie_robot, height=120, key="robot_sidebar")
    st.markdown("<h3 style='text-align: center;'>Asistente Virtual</h3>", unsafe_allow_html=True)
    st.markdown("---")
    
    opcion = st.radio("Navegar a:", ["📊 Stock Actual", "📥 Registrar Entrada", "📤 Retirar Producto", "💾 Reportes Excel"])
    
    st.markdown("---")
    st.markdown("### 🛠️ *Consultas IA*") # Reactivado
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
        # Edición directa y guardado en CSV
        editado = st.data_editor(df, use_container_width=True, num_rows="dynamic")
        if st.button("💾 Guardar cambios permanentes"):
            st.session_state.inventario_data = editado
            guardar_datos(editado)
            st.success("✅ ¡Datos guardados en el programa!")

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
            if sku and nom: # CORRECCIÓN LÍNEA 131
                df = st.session_state.inventario_data
                if sku.lower() in df['clave'].astype(str).str.lower().values:
                    idx = df[df['clave'].astype(str).str.lower() == sku.lower()].index[0]
                    df.at[idx, 'cajas'] += c_cajas
                    df.at[idx, 'piezas_sueltas'] += c_sueltas
                else:
                    nueva = pd.DataFrame([[sku, nom, c_cajas, c_cap, c_sueltas, ubi]], columns=df.columns)
                    df = pd.concat([df, nueva], ignore_index=True)
                
                st.session_state.inventario_data = df
                guardar_datos(df)
                st.success("✅ Guardado en sistema.")
                st.rerun()

# --- SECCIÓN: RETIRAR PRODUCTO ---
elif opcion == "📤 Retirar Producto":
    st.header("📤 Salida de Almacén")
    with st.form("form_out", clear_on_submit=True):
        sku_ret = st.text_input("Clave a retirar").strip()
        r1, r2 = st.columns(2)
        with r1: r_caj = st.number_input("Cajas", min_value=0)
        with r2: r_pie = st.number_input("Piezas", min_value=0)
        
        if st.form_submit_button("✅ Confirmar Salida"):
            df = st.session_state.inventario_data
            mask = df['clave'].astype(str).str.lower() == sku_ret.lower()
            if mask.any():
                idx = df[mask].index[0]
                df.at[idx, 'cajas'] = max(0, int(df.at[idx, 'cajas']) - r_caj)
                df.at[idx, 'piezas_sueltas'] = max(0, int(df.at[idx, 'piezas_sueltas']) - r_pie)
                if df.at[idx, 'cajas'] == 0 and df.at[idx, 'piezas_sueltas'] == 0:
                    df = df.drop(idx)
                st.session_state.inventario_data = df
                guardar_datos(df)
                st.success("✅ Retiro exitoso.")
                st.rerun()

# --- SECCIÓN: REPORTES EXCEL (CON BORRADO SELECCIONADO) ---
elif opcion == "💾 Reportes Excel":
    st.header("💾 Exportar y Gestionar Reportes")
    
    if not st.session_state.inventario_data.empty:
        df_ex = st.session_state.inventario_data.copy()
        df_ex['TOTAL_PIEZAS'] = (df_ex['cajas'] * df_ex['piezas_por_caja']) + df_ex['piezas_sueltas']
        
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df_ex.to_excel(writer, index=False)
        
        fecha = datetime.now().strftime("%d-%m-%Y_%Hh%Mm")
        nombre_archivo = f"Stock_TVC_{fecha}.xlsx"
        
        # CORRECCIÓN LÍNEA 132 (Paréntesis cerrados)
        st.download_button(label=f"📥 Descargar Reporte Actual", data=output.getvalue(), file_name=nombre_archivo)
        
        if st.button("✨ Añadir a historial de descargas"):
            if "historial" not in st.session_state: st.session_state.historial = []
            st.session_state.historial.append(nombre_archivo)
    
    st.divider()
    st.subheader("🗑️ Eliminar Reportes del Historial") # Nueva función solicitada
    if "historial" in st.session_state and st.session_state.historial:
        seleccionados = st.multiselect("Selecciona los reportes que quieres borrar:", st.session_state.historial)
        if st.button("❌ Eliminar seleccionados"):
            st.session_state.historial = [h for h in st.session_state.historial if h not in seleccionados]
            st.success("Historial actualizado.")
            st.rerun()
    else:
        st.info("No hay reportes en la lista.")
