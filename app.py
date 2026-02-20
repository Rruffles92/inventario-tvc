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
    st.title("TVC System")
    opcion = st.radio("Navegar a:", ["📊 Stock Actual", "📥 Registrar Entrada", "📤 Retirar Producto", "💾 Reportes Excel"])
    
    st.markdown("---")
    # CHAT PEQUEÑO (Bordes negros) al final
    st.subheader("💬 Consultas IA")
    with st.container():
        st.markdown('<div style="border: 2px solid black; padding: 10px; border-radius: 5px; background-color: #f0f2f6;">', unsafe_allow_html=True)
        user_msg = st.text_input("Pregúntame algo:", key="chat_input", label_visibility="collapsed", placeholder="Escribe aquí...")
        if user_msg:
            if "stock" in user_msg.lower():
                st.write(f"🤖 Hay {len(st.session_state.inventario_data)} productos en stock.")
            else:
                st.write("🤖 Estoy listo para ayudarte con el inventario.")
        st.markdown('</div>', unsafe_allow_html=True)

# --- SECCIÓN: STOCK ACTUAL ---
if opcion == "📊 Stock Actual":
    st.header("📋 Inventario Actual")
    df = st.session_state.inventario_data
    if not df.empty and any(df['cajas'].astype(int) < 2):
        st.warning("⚠️ Atención: Pocas cajas en stock.")
    
    editado = st.data_editor(df, use_container_width=True, num_rows="dynamic")
    if st.button("💾 Guardar Cambios"):
        st.session_state.inventario_data = editado
        guardar_datos(editado)
        st.success("✅ Datos actualizados.")

# --- SECCIÓN: REGISTRAR (Con todas tus opciones) ---
elif opcion == "📥 Registrar Entrada":
    st.header("📥 Registrar Producto")
    with st.form("form_registro", clear_on_submit=True):
        col1, col2 = st.columns(2)
        sku = col1.text_input("Clave (Scan)").strip()
        nom = col2.text_input("Nombre")
        
        c1, c2, c3 = st.columns(3)
        caj = c1.number_input("Cajas", min_value=0, value=1)
        pxc = c2.number_input("Piezas por Caja", min_value=1, value=10)
        slt = c3.number_input("Piezas Sueltas", min_value=0, value=0)
        
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

# --- SECCIÓN: RETIRAR (Clave, Cajas y Sueltas) ---
elif opcion == "📤 Retirar Producto":
    st.header("📤 Retiro de Mercancía")
    df = st.session_state.inventario_data
    sku_ret = st.text_input("Escanea Clave para retirar:").strip()
    
    if sku_ret:
        mask = df['clave'].astype(str) == sku_ret
        if mask.any():
            idx = df[mask].index[0]
            prod = df.loc[idx]
            st.info(f"Producto: {prod['nombre']} | Stock: {prod['cajas']} cajas y {prod['piezas_sueltas']} sueltas.")
            
            with st.form("form_retiro"):
                r_caj = st.number_input("Cajas a retirar", min_value=0, max_value=int(prod['cajas']))
                r_slt = st.number_input("Piezas sueltas a retirar", min_value=0, max_value=int(prod['piezas_sueltas']))
                
                if st.form_submit_button("Confirmar Retiro"):
                    df.at[idx, 'cajas'] -= r_caj
                    df.at[idx, 'piezas_sueltas'] -= r_slt
                    
                    # Auto-eliminar si llega a 0
                    if df.at[idx, 'cajas'] <= 0 and df.at[idx, 'piezas_sueltas'] <= 0:
                        df = df.drop(idx)
                        st.warning("Producto agotado y eliminado del stock.")
                    
                    guardar_datos(df)
                    st.session_state.inventario_data = df
                    st.rerun()
        else:
            st.error("Clave no encontrada.")

# --- SECCIÓN: REPORTES (Con borrado individual) ---
elif opcion == "💾 Reportes Excel":
    st.header("💾 Gestión de Reportes")
    ahora = datetime.now().strftime("%d-%m-%Y_%Hh%Mm")
    nombre_r = f"Reporte_{ahora}.xlsx"
    
    if st.button("➕ Crear y Guardar Reporte en Historial"):
        if nombre_r not in st.session_state.historial:
            st.session_state.historial.append(nombre_r)
            guardar_historial(st.session_state.historial)
            st.rerun()

    st.divider()
    st.subheader("🗑️ Eliminar Reportes del Historial")
    if st.session_state.historial:
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            st.session_state.inventario_data.to_excel(writer, index=False)
        excel_bin = output.getvalue()

        for i, nombre in enumerate(st.session_state.historial):
            c1, c2, c3 = st.columns([3, 1, 1])
            c1.write(f"📄 {nombre}")
            c2.download_button("📥 Bajar", data=excel_bin, file_name=nombre, key=f"d_{i}")
            if c3.button("🗑️ Borrar", key=f"b_{i}"):
                st.session_state.historial.pop(i)
                guardar_historial(st.session_state.historial)
                st.rerun()
    else:
        st.info("No hay reportes en la lista.")
