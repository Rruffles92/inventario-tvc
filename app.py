import streamlit as st
import pandas as pd
import os
from io import BytesIO
from datetime import datetime

# --- BLOQUEO DE ESTRUCTURA Y MENÚS ---
st.set_page_config(page_title="TVC Control Inventario", layout="wide", page_icon="🤖")

# Ocultar botones técnicos de Streamlit para proteger la estructura del programa
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
if "usuario_actual" not in st.session_state:
    st.session_state["usuario_actual"] = ""

if not st.session_state["autenticado"]:
    st.title("🔐 Acceso TVC San Nicolás")
    nombre_login = st.text_input("Tu Nombre:").strip().lower()
    pass_login = st.text_input("Contraseña:", type="password")
    if st.button("Entrar"):
        if pass_login == "TVCsanicolas" and nombre_login != "":
            st.session_state["autenticado"] = True
            st.session_state["usuario_actual"] = nombre_login
            st.rerun()
        else: st.error("❌ Datos incorrectos")
    st.stop()

# --- INTERFAZ ---
usuario = st.session_state["usuario_actual"]
df_actual = st.session_state.inventario_data

# ALERTA DE STOCK (3 CAJAS O MENOS)
bajos_auto = df_actual[df_actual['cajas'].astype(int) <= 3]
if not bajos_auto.empty:
    st.error(f"🚨 *ALERTA DE RELLENO:* {', '.join(bajos_auto['nombre'].tolist())}")

with st.sidebar:
    st.title("TVC System")
    st.write(f"👤 Usuario: *{usuario.capitalize()}*")
    
    # Menús estáticos: La estructura de navegación no se puede cambiar
    opcion = st.radio("Navegar a:", ["📊 Stock Actual", "📥 Registrar Entrada", "📤 Retirar Producto", "💾 Reportes Excel"])
    
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown(f"""<div style="border: 3px solid black; padding: 10px; border-radius: 5px; background-color: white;">
        <p style="margin: 0; font-weight: bold; color: black;">🤖 Asistente IA ({usuario})</p></div>""", unsafe_allow_html=True)
    
    pregunta = st.text_input("¿Qué necesitas saber?", key="chat_ia")
    if pregunta:
        p = pregunta.lower().strip()
        # Búsqueda de cualquier producto (como DHT5684)
        if any(x in p for x in ["cuanto hay", "total", "cantidad"]):
            busqueda = p.replace("cuanto hay de", "").replace("total de", "").strip()
            res = df_actual[df_actual['clave'].astype(str).str.lower().str.contains(busqueda) | df_actual['nombre'].str.lower().str.contains(busqueda)]
            if not res.empty:
                prod = res.iloc[0]
                st.info(f"📦 Raúl, de *{prod['nombre']}* hay: {prod['cajas']} cajas y {prod['piezas_sueltas']} piezas.")
            else: st.warning("🔍 No encontrado.")

# --- SECCIONES DE USO ---
if opcion == "📊 Stock Actual":
    st.header("📋 Inventario (Solo Lectura)")
    # Se muestra la tabla pero sin permisos de edición de estructura
    st.dataframe(df_actual, use_container_width=True)

elif opcion == "📥 Registrar Entrada":
    st.header("📥 Registrar Entrada")
    with st.form("f_reg", clear_on_submit=True):
        col1, col2 = st.columns(2)
        sku = col1.text_input("Clave")
        nom = col2.text_input("Nombre")
        c1, c2, c3 = st.columns(3)
        caj = c1.number_input("Cajas", min_value=0)
        pxc = c2.number_input("Piezas x Caja", min_value=1)
        slt = c3.number_input("Piezas Sueltas", min_value=0)
        ubi = st.text_input("Ubicación")
        if st.form_submit_button("✅ Guardar"):
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
            st.rerun()

elif opcion == "📤 Retirar Producto":
    st.header("📤 Retirar Producto")
    sku_ret = st.text_input("Escribe la Clave:").strip()
    if sku_ret:
        mask = df_actual['clave'].astype(str).str.lower() == sku_ret.lower()
        if mask.any():
            idx = df_actual[mask].index[0]
            item = df_actual.loc[idx]
            st.info(f"📦 {item['nombre']} | {item['piezas_sueltas']} sueltas")
            with st.form("f_ret"):
                cant = st.number_input("Cantidad a quitar", min_value=1, max_value=int(item['piezas_sueltas']))
                if st.form_submit_button("Descontar"):
                    df_actual.at[idx, 'piezas_sueltas'] -= cant
                    guardar_datos(df_actual)
                    st.session_state.inventario_data = df_actual
                    st.rerun()

elif opcion == "💾 Reportes Excel":
    st.header("💾 Reportes Disponibles")
    if st.button("➕ Generar Nuevo Reporte"):
        n_rep = f"Reporte_{datetime.now().strftime('%d-%m-%Y_%Hh%M')}.xlsx"
        st.session_state.historial.append(n_rep)
        guardar_historial(st.session_state.historial)
        st.rerun()
    
    st.divider()
    if st.session_state.historial:
        # Preparar datos de descarga
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df_actual.to_excel(writer, index=False)
        excel_data = output.getvalue()

        for i, n in enumerate(st.session_state.historial):
            c_nom, c_desc, c_borr = st.columns([3, 1, 1])
            c_nom.write(f"📄 {n}")
            c_desc.download_button(label="📥 Descargar", data=excel_data, file_name=n, key=f"d_{i}")
            # Habilitado el borrado para TODOS los usuarios
            if c_borr.button("🗑️ Borrar", key=f"b_{i}"):
                st.session_state.historial.pop(i)
                guardar_historial(st.session_state.historial)
                st.rerun()
