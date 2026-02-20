import streamlit as st
import pandas as pd
import os
from io import BytesIO
from datetime import datetime

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="TVC Control Inventario", layout="wide", page_icon="🤖")

# Ocultar botones técnicos de Streamlit
st.markdown("""
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    </style>
""", unsafe_allow_html=True)

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

# --- ACCESO ---
if "autenticado" not in st.session_state:
    st.session_state["autenticado"] = False

if not st.session_state["autenticado"]:
    st.title("🔐 Acceso TVC")
    n_log = st.text_input("Nombre:").strip().lower()
    p_log = st.text_input("Contraseña:", type="password")
    if st.button("Entrar"):
        if p_log == "TVCsanicolas" and n_log != "":
            st.session_state["autenticado"] = True
            st.session_state["usuario_actual"] = n_log
            st.rerun()
    st.stop()

# --- CUERPO DE LA APP ---
usuario = st.session_state["usuario_actual"]
df_actual = st.session_state.inventario_data

st.title(f"📦 TVC System - Hola {usuario.capitalize()}")

# --- ASISTENTE IA (ARRIBA DE TODO) ---
with st.expander("🤖 PREGUNTAR AL ASISTENTE IA", expanded=False):
    pregunta = st.text_input("Ej: donde esta el DHT5684", key="chat_ia")
    if pregunta:
        # Limpieza para que encuentre el producto aunque preguntes con frases largas
        p_limpia = pregunta.lower().replace("cuanto hay de", "").replace("donde esta", "").replace("el", "").strip()
        res = df_actual[df_actual['clave'].astype(str).str.lower().str.contains(p_limpia) | 
                        df_actual['nombre'].str.lower().str.contains(p_limpia)]
        if not res.empty:
            p = res.iloc[0]
            st.info(f"✅ *{p['nombre']}*: Hay {p['cajas']} cajas y {p['piezas_sueltas']} piezas.\n📍 Ubicado en: {p['ubicacion']}")
        else: st.warning("🔍 No encontré ese producto.")

# --- MENÚS SUPERIORES (PESTAÑAS) ---
tab1, tab2, tab3, tab4 = st.tabs(["📊 Stock", "📥 Entrada", "📤 Salida", "💾 Reportes"])

with tab1:
    st.header("Inventario Editable")
    # Tabla con botón de guardado como pediste
    df_ed = st.data_editor(df_actual, use_container_width=True, num_rows="dynamic")
    if st.button("💾 Guardar Todos los Cambios"):
        guardar_datos(df_ed)
        st.session_state.inventario_data = df_ed
        st.success("¡Cambios guardados con éxito!")
        st.rerun()

with tab2:
    st.header("Registrar Entrada")
    with st.form("form_alta", clear_on_submit=True):
        c1, c2 = st.columns(2)
        sku = c1.text_input("Clave")
        nom = c2.text_input("Nombre")
        c3, c4, c5 = st.columns(3)
        caj = c3.number_input("Cajas", min_value=0)
        pxc = c4.number_input("Pzas x Caja", min_value=1)
        slt = c5.number_input("Pzas Sueltas", min_value=0)
        ubi = st.text_input("Ubicación")
        if st.form_submit_button("✅ Guardar Producto"):
            mask = df_actual['clave'].astype(str) == sku
            if mask.any():
                idx = df_actual[mask].index[0]
                df_actual.at[idx, 'cajas'] += caj
                df_actual.at[idx, 'piezas_sueltas'] += slt
            else:
                nueva = pd.DataFrame([[sku, nom, caj, pxc, slt, ubi]], columns=df_actual.columns)
                df_actual = pd.concat([df_actual, nueva], ignore_index=True)
            guardar_datos(df_actual)
            st.session_state.inventario_data = df_actual
            st.success("Ingresado correctamente.")

with tab3:
    st.header("Retirar Producto")
    sku_r = st.text_input("Busca la clave:").strip()
    if sku_r:
        mask = df_actual['clave'].astype(str).str.lower() == sku_r.lower()
        if mask.any():
            idx = df_actual[mask].index[0]
            item = df_actual.loc[idx]
            st.write(f"📦 *{item['nombre']}* | {item['piezas_sueltas']} piezas disponibles.")
            with st.form("form_baja"):
                cant = st.number_input("Cantidad a quitar", min_value=1, max_value=int(item['piezas_sueltas']))
                if st.form_submit_button("Confirmar Retiro"):
                    df_actual.at[idx, 'piezas_sueltas'] -= cant
                    guardar_datos(df_actual)
                    st.session_state.inventario_data = df_actual
                    st.rerun()

with tab4:
    st.header("Gestión de Reportes")
    if st.button("➕ Generar Reporte Nuevo"):
        n_rep = f"Reporte_{datetime.now().strftime('%d-%m-%Y_%Hh%M')}.xlsx"
        st.session_state.historial.append(n_rep)
        guardar_historial(st.session_state.historial)
        st.rerun()
    
    st.divider()
    for i, n in enumerate(st.session_state.historial):
        col_n, col_d, col_b = st.columns([3, 1, 1])
        col_n.write(f"📄 {n}")
        # Descarga
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df_actual.to_excel(writer, index=False)
        col_d.download_button("📥", data=output.getvalue(), file_name=n, key=f"d_{i}")
        # Borrar habilitado para todos
        if col_b.button("🗑️", key=f"b_{i}"):
            st.session_state.historial.pop(i)
            guardar_historial(st.session_state.historial)
            st.rerun()
