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

# --- SEGURIDAD Y LOGIN ---
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

# ALERTA AUTOMÁTICA AL ENTRAR (3 cajas o menos)
bajos_auto = df_actual[df_actual['cajas'].astype(int) <= 3]
if not bajos_auto.empty:
    st.error(f"🚨 *¡ATENCIÓN {usuario.upper()}!* Hay productos con stock muy bajo (3 cajas o menos): {', '.join(bajos_auto['nombre'].tolist())}")

with st.sidebar:
    st.title("TVC System")
    st.write(f"👤 Hola, *{usuario}*")
    opcion = st.radio("Navegar a:", ["📊 Stock Actual", "📥 Registrar Entrada", "📤 Retirar Producto", "💾 Reportes Excel"])
    
    st.markdown("<br><br>", unsafe_allow_html=True)
    
    # CHAT IA (Con funciones de conteo y alertas)
    st.markdown(f"""
        <div style="border: 3px solid black; padding: 10px; border-radius: 5px; background-color: #ffffff;">
            <p style="margin: 0; font-weight: bold; color: black; font-size: 14px;">🤖 Asistente IA ({usuario})</p>
        </div>
    """, unsafe_allow_html=True)
    
    pregunta = st.text_input("¿Qué necesitas saber?", key="chat_ia", placeholder="Ej: ¿Qué hay que rellenar?")
    
    if pregunta:
        p = pregunta.lower().strip()
        
        # Conteo de cajas y producto
        if any(x in p for x in ["cuantas cajas", "total de cajas", "cuanto producto"]):
            total_caj = df_actual['cajas'].sum()
            st.info(f"📊 {usuario}, tenemos un total de *{total_caj} cajas* en el inventario.")

        # Alertas de relleno (3 cajas o menos)
        elif any(x in p for x in ["rellenar", "acaba", "falta", "bajo"]):
            if not bajos_auto.empty:
                st.error(f"⚠️ {usuario}, estos productos tienen 3 cajas o menos: *{', '.join(bajos_auto['nombre'].tolist())}*")
            else:
                st.success(f"✅ Todo bien, {usuario}. Ningún producto tiene menos de 3 cajas.")

        # Localización
        elif any(x in p for x in ["donde", "ubica", "esta"]):
            busqueda = p.replace("donde esta", "").replace("donde", "").strip()
            res = df_actual[df_actual['clave'].astype(str).str.lower().str.contains(busqueda) | df_actual['nombre'].str.lower().str.contains(busqueda)]
            if not res.empty:
                st.info(f"📍 {usuario}, *{res.iloc[0]['nombre']}* está en: *{res.iloc[0]['ubicacion']}*")
            else:
                st.warning(f"🔍 No encuentro '{busqueda}'.")

# --- SECCIONES (IGUALES A LAS ANTERIORES) ---
if opcion == "📥 Registrar Entrada":
    st.header("📥 Registrar Producto")
    with st.form("f_reg", clear_on_submit=True):
        col1, col2 = st.columns(2)
        sku = col1.text_input("Clave (Scan)")
        nom = col2.text_input("Nombre")
        c1, c2, c3 = st.columns(3)
        caj = c1.number_input("Cajas", min_value=0)
        pxc = c2.number_input("Piezas por caja", min_value=1)
        slt = c3.number_input("Piezas sueltas", min_value=0)
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

elif opcion == "📊 Stock Actual":
    st.header("📋 Inventario")
    editado = st.data_editor(df_actual, use_container_width=True)
    if st.button("💾 Guardar Cambios"):
        guardar_datos(editado)
        st.session_state.inventario_data = editado

elif opcion == "💾 Reportes Excel":
    st.header("💾 Gestión de Reportes")
    nombre_rep = f"Reporte_{datetime.now().strftime('%d-%m-%Y_%Hh%M')}.xlsx"
    if st.button("➕ Generar Reporte"):
        st.session_state.historial.append(nombre_rep)
        guardar_historial(st.session_state.historial)
        st.rerun()
    for i, n in enumerate(st.session_state.historial):
        c1, c2 = st.columns([4, 1])
        c1.write(f"📄 {n}")
        if c2.button("🗑️", key=f"b_{i}"):
            st.session_state.historial.pop(i)
            guardar_historial(st.session_state.historial)
            st.rerun()
