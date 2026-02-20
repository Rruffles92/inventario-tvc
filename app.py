import streamlit as st
import pandas as pd
import os
from io import BytesIO
from datetime import datetime

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

# --- SEGURIDAD ---
if "autenticado" not in st.session_state:
    st.session_state["autenticado"] = False
if "usuario_actual" not in st.session_state:
    st.session_state["usuario_actual"] = "Invitado"

if not st.session_state["autenticado"]:
    st.title("🔐 Acceso TVC San Nicolás")
    nombre_login = st.text_input("Tu Nombre:")
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

# ALERTA AUTOMÁTICA (3 cajas o menos)
bajos_auto = df_actual[df_actual['cajas'].astype(int) <= 3]
if not bajos_auto.empty:
    st.error(f"🚨 *¡ATENCIÓN {usuario.upper()}!* Quedan 3 cajas o menos de: {', '.join(bajos_auto['nombre'].tolist())}")

with st.sidebar:
    st.title("TVC System")
    st.write(f"👤 Hola, *{usuario}*")
    opcion = st.radio("Navegar a:", ["📊 Stock Actual", "📥 Registrar Entrada", "📤 Retirar Producto", "💾 Reportes Excel"])
    
    st.markdown("<br><br>", unsafe_allow_html=True)
    
    # CHAT IA (Recuadro Negro con búsqueda mejorada)
    st.markdown(f"""
        <div style="border: 3px solid black; padding: 10px; border-radius: 5px; background-color: #ffffff;">
            <p style="margin: 0; font-weight: bold; color: black; font-size: 14px;">🤖 Asistente IA ({usuario})</p>
        </div>
    """, unsafe_allow_html=True)
    
    pregunta = st.text_input("¿Qué necesitas saber?", key="chat_ia")
    if pregunta:
        p = pregunta.lower().strip()
        # Búsqueda de totales (DHT5684, etc)
        if any(x in p for x in ["cuanto hay", "total", "cantidad"]):
            busqueda = p.replace("cuanto hay de", "").replace("total de", "").replace("cuanto hay", "").strip()
            res = df_actual[df_actual['clave'].astype(str).str.lower().str.contains(busqueda) | df_actual['nombre'].str.lower().str.contains(busqueda)]
            if not res.empty:
                prod = res.iloc[0]
                st.info(f"📦 {usuario}, de *{prod['nombre']}* hay: *{prod['cajas']} cajas* y *{prod['piezas_sueltas']} piezas*.")
            else: st.warning(f"🔍 No encuentro nada para '{busqueda}', {usuario}.")
        elif any(x in p for x in ["donde", "ubica"]):
            busqueda = p.replace("donde esta", "").replace("donde", "").strip()
            res = df_actual[df_actual['clave'].astype(str).str.lower().str.contains(busqueda) | df_actual['nombre'].str.lower().str.contains(busqueda)]
            if not res.empty: st.info(f"📍 Ubicación: *{res.iloc[0]['ubicacion']}*")
            else: st.warning("🔍 No encontrado.")

# --- SECCIONES ---
if opcion == "📊 Stock Actual":
    st.header("📋 Inventario")
    editado = st.data_editor(df_actual, use_container_width=True)
    if st.button("💾 Guardar Cambios"):
        guardar_datos(editado)
        st.session_state.inventario_data = editado
        st.success("Guardado correctamente.")

elif opcion == "📥 Registrar Entrada":
    st.header("📥 Registrar Producto")
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
    st.header("📤 Retirar Piezas")
    sku_ret = st.text_input("Escanea Clave:").strip()
    if sku_ret:
        mask = df_actual['clave'].astype(str).str.lower() == sku_ret.lower()
        if mask.any():
            idx = df_actual[mask].index[0]
            item = df_actual.loc[idx]
            st.info(f"📦 {item['nombre']} | {item['piezas_sueltas']} sueltas")
            with st.form("f_ret"):
                cant = st.number_input("Piezas a quitar", min_value=0, max_value=int(item['piezas_sueltas']))
                if st.form_submit_button("Descontar"):
                    df_actual.at[idx, 'piezas_sueltas'] -= cant
                    guardar_datos(df_actual)
                    st.session_state.inventario_data = df_actual
                    st.rerun()

elif opcion == "💾 Reportes Excel":
    st.header("💾 Gestión de Reportes")
    nombre_rep = f"Reporte_{datetime.now().strftime('%d-%m-%Y_%Hh%M')}.xlsx"
    
    if st.button("➕ Generar Reporte"):
        if nombre_rep not in st.session_state.historial:
            st.session_state.historial.append(nombre_rep)
            guardar_historial(st.session_state.historial)
            st.rerun()

    st.divider()
    
    # LISTA DE REPORTES CON DESCARGA
    if st.session_state.historial:
        # Generar Excel para descarga
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df_actual.to_excel(writer, index=False)
        excel_data = output.getvalue()

        for i, n in enumerate(st.session_state.historial):
            col_nom, col_desc, col_borr = st.columns([3, 1, 1])
            col_nom.write(f"📄 {n}")
            # Botón de Descarga
            col_desc.download_button(label="📥 Descargar", data=excel_data, file_name=n, key=f"desc_{i}")
            # Botón de Borrado
            if col_borr.button("🗑️ Borrar", key=f"borr_{i}"):
                st.session_state.historial.pop(i)
                guardar_historial(st.session_state.historial)
                st.rerun()
