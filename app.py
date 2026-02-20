import streamlit as st
import pandas as pd
import os
from io import BytesIO
from datetime import datetime

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="TVC Control Inventario", layout="wide", page_icon="🤖")

# Ocultar botones técnicos para proteger la estructura
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

usuario = st.session_state["usuario_actual"]
df_actual = st.session_state.inventario_data

# Alerta automática (3 cajas)
bajos_auto = df_actual[df_actual['cajas'].astype(int) <= 3]
if not bajos_auto.empty:
    st.error(f"🚨 *RELLENAR STOCK:* {', '.join(bajos_auto['nombre'].tolist())}")

with st.sidebar:
    st.title("TVC System")
    st.write(f"👤 Usuario: *{usuario.capitalize()}*")
    
    # Menús visibles para todos
    opcion = st.radio("Menú:", ["📊 Inventario y Guardado", "📥 Agregar Producto", "📤 Retirar Producto", "💾 Reportes"])
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    # --- IA CORREGIDA ---
    st.markdown(f"""<div style="border: 2px solid black; padding: 10px; border-radius: 5px; background-color: white;">
        <p style="margin: 0; font-weight: bold; color: black;">🤖 Asistente IA ({usuario})</p></div>""", unsafe_allow_html=True)
    
    pregunta = st.text_input("¿Qué necesitas saber?", key="chat_ia")
    if pregunta:
        # Limpieza de la pregunta para extraer el producto
        p_limpia = pregunta.lower().replace("cuanto hay de", "").replace("donde esta", "").replace("cantidad de", "").replace("ubicacion de", "").strip()
        
        res = df_actual[df_actual['clave'].astype(str).str.lower().str.contains(p_limpia) | 
                        df_actual['nombre'].str.lower().str.contains(p_limpia)]
        
        if not res.empty:
            prod = res.iloc[0]
            st.info(f"📦 *{prod['nombre']}\n\n💰 Cantidad: *{prod['cajas']} cajas** y *{prod['piezas_sueltas']} piezas.\n\n📍 Ubicación: *{prod['ubicacion']}**")
        else:
            st.warning(f"🔍 No encontré nada relacionado con '{p_limpia}', {usuario}.")

# --- SECCIONES ---
if opcion == "📊 Inventario y Guardado":
    st.header("📋 Inventario Editable")
    # Tabla con opción de guardado
    df_editado = st.data_editor(df_actual, use_container_width=True, num_rows="dynamic")
    if st.button("💾 Guardar Todos los Cambios"):
        guardar_datos(df_editado)
        st.session_state.inventario_data = df_editado
        st.success("¡Datos actualizados y guardados!")
        st.rerun()

elif opcion == "📥 Agregar Producto":
    st.header("📥 Registro de Producto")
    with st.form("f_reg", clear_on_submit=True):
        c1, c2 = st.columns(2)
        sku = c1.text_input("Clave")
        nom = c2.text_input("Nombre")
        c3, c4, c5 = st.columns(3)
        caj = c3.number_input("Cajas", min_value=0)
        pxc = c4.number_input("Pzas x Caja", min_value=1)
        slt = c5.number_input("Pzas Sueltas", min_value=0)
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
    st.header("📤 Salida de Producto")
    sku_ret = st.text_input("Clave:").strip()
    if sku_ret:
        mask = df_actual['clave'].astype(str).str.lower() == sku_ret.lower()
        if mask.any():
            idx = df_actual[mask].index[0]
            item = df_actual.loc[idx]
            st.info(f"📦 {item['nombre']} | Hay {item['piezas_sueltas']} piezas")
            with st.form("f_ret"):
                cant = st.number_input("Cantidad a retirar", min_value=1, max_value=int(item['piezas_sueltas']))
                if st.form_submit_button("Descontar"):
                    df_actual.at[idx, 'piezas_sueltas'] -= cant
                    guardar_datos(df_actual)
                    st.session_state.inventario_data = df_actual
                    st.rerun()

elif opcion == "💾 Reportes":
    st.header("💾 Reportes Excel")
    if st.button("➕ Nuevo Reporte"):
        n_rep = f"Reporte_{datetime.now().strftime('%d-%m-%Y_%Hh%M')}.xlsx"
        st.session_state.historial.append(n_rep)
        guardar_historial(st.session_state.historial)
        st.rerun()
    
    if st.session_state.historial:
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df_actual.to_excel(writer, index=False)
        excel_data = output.getvalue()
        for i, n in enumerate(st.session_state.historial):
            c1, c2, c3 = st.columns([3, 1, 1])
            c1.write(f"📄 {n}")
            c2.download_button("📥", data=excel_data, file_name=n, key=f"d_{i}")
            if c3.button("🗑️", key=f"b_{i}"):
                st.session_state.historial.pop(i)
                guardar_historial(st.session_state.historial)
                st.rerun()
