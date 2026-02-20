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
LOG_MOVIMIENTOS = "movimientos_tvc.csv" # Archivo para saber qué se mueve más

def cargar_datos():
    if os.path.exists(DB_FILE):
        return pd.read_csv(DB_FILE)
    return pd.DataFrame(columns=["clave", "nombre", "cajas", "piezas_por_caja", "piezas_sueltas", "ubicacion"])

def registrar_movimiento(nombre, cantidad):
    # Registra qué se retiró para el análisis de IA
    nueva_fila = pd.DataFrame([[datetime.now(), nombre, cantidad]], columns=["fecha", "nombre", "cantidad"])
    if os.path.exists(LOG_MOVIMIENTOS):
        nueva_fila.to_csv(LOG_MOVIMIENTOS, mode='a', header=False, index=False)
    else:
        nueva_fila.to_csv(LOG_MOVIMIENTOS, index=False)

def obtener_mas_movido():
    if os.path.exists(LOG_MOVIMIENTOS):
        df_mov = pd.read_csv(LOG_MOVIMIENTOS)
        if not df_mov.empty:
            top = df_mov.groupby('nombre')['cantidad'].sum().idxmax()
            return top
    return "Sin datos aún"

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

# --- BARRA LATERAL CON ANALÍTICA ---
with st.sidebar:
    if lottie_robot:
        st_lottie(lottie_robot, height=150, key="robot")
    st.markdown("<h3 style='text-align: center;'>Asistente Virtual</h3>", unsafe_allow_html=True)
    
    # NUEVA FUNCIÓN: AVISO DE MOVIMIENTO RÁPIDO
    top_prod = obtener_mas_movido()
    st.info(f"🚀 *Producto con más salida:*\n\n{top_prod}")
    
    st.markdown("---")
    opcion = st.radio("Navegar a:", ["📊 Stock Actual", "📥 Registrar Entrada", "📤 Retirar Producto", "💾 Reportes Excel"])

# --- SECCIONES ---

if opcion == "📊 Stock Actual":
    st.header("📋 Inventario Editable")
    df = st.session_state.inventario_data
    if df.empty:
        st.info("No hay productos registrados.")
    else:
        if any(df['cajas'].astype(int) < 2):
            st.warning("⚠️ ¡Atención! Stock bajo en algunos productos.")
        
        editado = st.data_editor(df, use_container_width=True, num_rows="dynamic")
        if st.button("💾 Guardar Cambios Permanentes"):
            st.session_state.inventario_data = editado
            guardar_datos(editado)
            st.success("✅ ¡Datos guardados!")

elif opcion == "📥 Registrar Entrada":
    st.header("📥 Registro (Escáner o Manual)")
    with st.form("form_scan", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            sku = st.text_input("Clave (Escanea o escribe)").strip()
            nom = st.text_input("Nombre del Producto")
        with col2:
            ubi = st.text_input("Ubicación")
        
        c1, c2, c3 = st.columns(3)
        with c1: boxes = st.number_input("Cajas", min_value=0, value=0)
        with c2: p_box = st.number_input("Unidades por Caja", min_value=1, value=1)
        with c3: loose = st.number_input("Piezas Sueltas", min_value=0, value=0)
        
        if st.form_submit_button("🚀 Guardar Entrada"):
            if sku and nom:
                df = st.session_state.inventario_data
                mask = df['clave'].astype(str).str.lower() == sku.lower()
                if mask.any():
                    idx = df[mask].index[0]
                    df.at[idx, 'cajas'] += boxes
                    df.at[idx, 'piezas_sueltas'] += loose
                else:
                    nueva = pd.DataFrame([[sku, nom, boxes, p_box, loose, ubi]], columns=df.columns)
                    df = pd.concat([df, nueva], ignore_index=True)
                
                guardar_datos(df)
                st.session_state.inventario_data = df
                st.success(f"✅ {nom} registrado.")
                st.rerun()

elif opcion == "📤 Retirar Producto":
    st.header("📤 Salida de Mercancía")
    df = st.session_state.inventario_data
    if df.empty:
        st.warning("No hay stock.")
    else:
        sku_ret = st.text_input("Escanea o escribe la Clave:").strip()
        if sku_ret:
            mask = df['clave'].astype(str).str.lower() == sku_ret.lower()
            if mask.any():
                idx = df[mask].index[0]
                item = df.loc[idx]
                st.info(f"📦 Stock: {item['cajas']} cajas, {item['piezas_sueltas']} sueltas.")
                
                with st.form("form_retiro"):
                    r_caj = st.number_input("Cajas a retirar", min_value=0, max_value=int(item['cajas']))
                    r_pie = st.number_input("Piezas sueltas a retirar", min_value=0, max_value=int(item['piezas_sueltas']))
                    
                    if st.form_submit_button("✅ Confirmar Salida"):
                        df.at[idx, 'cajas'] -= r_caj
                        df.at[idx, 'piezas_sueltas'] -= r_pie
                        
                        # Guardamos el movimiento para la analítica del robot
                        total_retirado = (r_caj * int(item['piezas_por_caja'])) + r_pie
                        registrar_movimiento(item['nombre'], total_retirado)
                        
                        if df.at[idx, 'cajas'] <= 0 and df.at[idx, 'piezas_sueltas'] <= 0:
                            df = df.drop(idx)
                            st.warning("🗑️ Producto agotado y eliminado.")
                        
                        guardar_datos(df)
                        st.session_state.inventario_data = df
                        st.rerun()

elif opcion == "💾 Reportes Excel":
    st.header("💾 Gestión de Reportes")
    if not st.session_state.inventario_data.empty:
        ahora = datetime.now().strftime("%d-%m-%Y_%Hh%Mm")
        nombre_f = f"Reporte_Stock_{ahora}.xlsx"
        if st.button(f"➕ Guardar reporte: {nombre_f}"):
            if nombre_f not in st.session_state.historial:
                st.session_state.historial.append(nombre_f)
                guardar_historial(st.session_state.historial)
                st.rerun()

    st.divider()
    if st.session_state.historial:
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            st.session_state.inventario_data.to_excel(writer, index=False)
        excel_bin = output.getvalue()

        for i, nombre in enumerate(st.session_state.historial):
            col_n, col_d, col_b = st.columns([3, 1, 1])
            col_n.write(f"📄 {nombre}")
            col_d.download_button("📥 Bajar", data=excel_bin, file_name=nombre, key=f"d_{i}")
            if col_b.button("🗑️ Borrar", key=f"b_{i}"):
                st.session_state.historial.pop(i)
                guardar_historial(st.session_state.historial)
                st.rerun()
