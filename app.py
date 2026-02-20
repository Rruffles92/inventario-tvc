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

# --- SEGURIDAD Y REGISTRO DE USUARIO ---
if "autenticado" not in st.session_state:
    st.session_state["autenticado"] = False
    st.session_state["usuario_actual"] = ""

if not st.session_state["autenticado"]:
    st.title("🔐 Acceso TVC San Nicolás")
    nombre_user = st.text_input("Escribe tu nombre:")
    password = st.text_input("Contraseña:", type="password")
    if st.button("Entrar"):
        if password == "TVCsanicolas" and nombre_user != "":
            st.session_state["autenticado"] = True
            st.session_state["usuario_actual"] = nombre_user
            st.rerun()
        elif nombre_user == "":
            st.warning("Por favor, escribe tu nombre.")
        else: 
            st.error("❌ Contraseña incorrecta")
    st.stop()

# --- BARRA LATERAL ---
usuario = st.session_state["usuario_actual"]

with st.sidebar:
    st.title("TVC System")
    st.write(f"👤 Bienvenido: *{usuario}*")
    opcion = st.radio("Navegar a:", ["📊 Stock Actual", "📥 Registrar Entrada", "📤 Retirar Producto", "💾 Reportes Excel"])
    
    st.markdown("<br><br>", unsafe_allow_html=True)
    
    # --- CHAT IA DINÁMICO (CUADRO NEGRO) ---
    st.markdown(f"""
        <div style="border: 2px solid black; padding: 10px; border-radius: 5px; background-color: #ffffff;">
            <p style="margin: 0; font-weight: bold; color: black;">🤖 Asistente IA (Hola {usuario})</p>
        </div>
    """, unsafe_allow_html=True)
    
    pregunta = st.text_input("¿Qué necesitas saber?", key="chat_ia", placeholder="Ej: ¿Dónde está el producto?")
    
    if pregunta:
        df = st.session_state.inventario_data
        p = pregunta.lower()
        
        if any(x in p for x in ["donde", "ubica", "esta"]):
            termino = p.replace("donde esta", "").replace("donde", "").replace("ubica", "").strip()
            res = df[(df['clave'].astype(str).str.contains(termino)) | (df['nombre'].str.lower().str.contains(termino))]
            if not res.empty:
                st.info(f"📍 {usuario}, el producto está en: *{res.iloc[0]['ubicacion']}*")
            else:
                st.warning(f"🔍 Lo siento {usuario}, no lo encuentro.")

        elif any(x in p for x in ["pedido", "mas sale"]):
            if not df.empty:
                freg = df.sort_values(by="cajas", ascending=True).iloc[0]
                st.info(f"🔥 {usuario}, el más pedido es: *{freg['nombre']}*.")

        elif any(x in p for x in ["rellenar", "acaba", "falta"]):
            bajos = df[df['cajas'].astype(int) <= 1]
            if not bajos.empty:
                st.error(f"⚠️ *{usuario}, falta rellenar:* {', '.join(bajos['nombre'].tolist())}")
            else:
                st.success(f"✅ Todo bien en stock, {usuario}.")
        else:
            st.write(f"🤖 Estoy a tus órdenes, {usuario}.")

# --- SECCIONES (STOCK, REGISTRO, RETIRO, REPORTES) ---
if opcion == "📊 Stock Actual":
    st.header("📋 Stock Actual")
    df = st.session_state.inventario_data
    editado = st.data_editor(df, use_container_width=True, num_rows="dynamic")
    if st.button("💾 Guardar Cambios"):
        st.session_state.inventario_data = editado
        guardar_datos(editado)
        st.success("✅ Datos guardados.")

elif opcion == "📥 Registrar Entrada":
    st.header("📥 Registrar Entrada")
    with st.form("form_reg", clear_on_submit=True):
        col1, col2 = st.columns(2)
        sku = col1.text_input("Clave (Scan)").strip()
        nom = col2.text_input("Nombre")
        c1, c2, c3 = st.columns(3)
        caj = c1.number_input("Cajas", min_value=0)
        pxc = c2.number_input("Piezas por caja", min_value=1)
        slt = c3.number_input("Piezas sueltas", min_value=0)
        ubi = st.text_input("Ubicación")
        if st.form_submit_button("✅ Guardar"):
            df = st.session_state.inventario_data
            mask = df['clave'].astype(str) == sku
            if mask.any():
                idx = df[mask].index[0]
                df.at[idx, 'cajas'] += caj
                df.at[idx, 'piezas_sueltas'] += slt
            else:
                nueva = pd.DataFrame([[sku, nom, caj, pxc, slt, ubi]], columns=df.columns)
                df = pd.concat([df, nueva], ignore_index=True)
            guardar_datos(df)
            st.session_state.inventario_data = df
            st.rerun()

elif opcion == "📤 Retirar Producto":
    st.header("📤 Retiro de Piezas")
    df = st.session_state.inventario_data
    sku_ret = st.text_input("Escanea Clave:").strip()
    if sku_ret:
        mask = df['clave'].astype(str) == sku_ret
        if mask.any():
            idx = df[mask].index[0]
            item = df.loc[idx]
            st.info(f"📦 {item['nombre']} | Disponibles: {item['piezas_sueltas']} piezas")
            with st.form("f_ret"):
                cant = st.number_input("Piezas a retirar", min_value=0, max_value=int(item['piezas_sueltas']))
                if st.form_submit_button("Confirmar"):
                    df.at[idx, 'piezas_sueltas'] -= cant
                    if df.at[idx, 'cajas'] <= 0 and df.at[idx, 'piezas_sueltas'] <= 0:
                        df = df.drop(idx)
                    guardar_datos(df)
                    st.session_state.inventario_data = df
                    st.rerun()
        else: st.error("No encontrada.")

elif opcion == "💾 Reportes Excel":
    st.header("💾 Gestión de Reportes")
    nombre_rep = f"Reporte_{datetime.now().strftime('%d-%m-%Y_%Hh%Mm')}.xlsx"
    if st.button("➕ Crear Reporte"):
        if nombre_rep not in st.session_state.historial:
            st.session_state.historial.append(nombre_rep)
            guardar_historial(st.session_state.historial)
            st.rerun()
    st.divider()
    if st.session_state.historial:
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            st.session_state.inventario_data.to_excel(writer, index=False)
        excel_bin = output.getvalue()
        for i, nombre in enumerate(st.session_state.historial):
            c1, c2, c3 = st.columns([3, 1, 1])
            c1.write(f"📄 {nombre}")
            c2.download_button("📥 Bajar", data=excel_bin, file_name=nombre, key=f"dl_{i}")
            if c3.button("🗑️ Borrar", key=f"br_{i}"):
                st.session_state.historial.pop(i)
                guardar_historial(st.session_state.historial)
                st.rerun()
