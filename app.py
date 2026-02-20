import streamlit as st
import pandas as pd
from io import BytesIO
from datetime import datetime
import requests
from streamlit_lottie import st_lottie

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="TVC Control Inventario", layout="wide", page_icon="🤖")

# Función para cargar la animación del robot
def load_lottieurl(url: str):
    r = requests.get(url)
    if r.status_code != 200:
        return None
    return r.json()

# URL de un robot kawaii animado
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
        else:
            st.error("❌ Contraseña Incorrecta")
    st.stop()

# --- DATOS EN MEMORIA ---
if "inventario_data" not in st.session_state:
    st.session_state.inventario_data = pd.DataFrame(
        columns=["clave", "nombre", "cantidad", "ubicacion"]
    )
if "historial_descargas" not in st.session_state:
    st.session_state.historial_descargas = []

# --- BARRA LATERAL CON ROBOT MINIATURA ---
with st.sidebar:
    # Robot animado en miniatura
    if lottie_robot:
        st_lottie(lottie_robot, height=120, key="robot_animado")
    
    st.markdown("<h3 style='text-align: center;'>Asistente Virtual</h3>", unsafe_allow_html=True)
    st.markdown("---")
    
    opcion = st.radio("Navegar a:", ["📊 Stock Actual", "📥 Registrar/Editar", "💾 Exportar Excel"])
    
    st.markdown("---")
    st.markdown("### 🛠️ *Consultas IA*")
    pregunta = st.text_input("¿En qué puedo ayudarte?", placeholder="Ej: ¿Hay stock bajo?")
    
    df = st.session_state.inventario_data
    if pregunta:
        if "bajo" in pregunta.lower() or "poco" in pregunta.lower():
            bajos = df[df['cantidad'].astype(int) < 5]
            if not bajos.empty:
                st.warning("🤖 ¡Cuidado! Estos productos se agotan:")
                st.dataframe(bajos[['clave', 'cantidad']], hide_index=True)
            else:
                st.success("🤖 ¡Todo bien! Tienes suficiente stock.")
        elif not df.empty:
            res = df[df.apply(lambda r: pregunta.lower() in str(r).lower(), axis=1)]
            if not res.empty:
                st.write("🔍 Esto fue lo que encontré:")
                st.table(res[['clave', 'cantidad']])
            else:
                st.write("🤖 No encontré ese producto...")

# --- SECCIÓN: EXPORTAR EXCEL (CON GESTIÓN SUPERIOR) ---
if opcion == "💾 Exportar Excel":
    st.header("💾 Gestión de Documentos")
    
    # Gestión manual del historial arriba
    if st.session_state.historial_descargas:
        st.subheader("🗑️ Historial (Selecciona para borrar)")
        df_hist = pd.DataFrame(st.session_state.historial_descargas, columns=["Archivo"])
        hist_edit = st.data_editor(df_hist, num_rows="dynamic", use_container_width=True, key="del_hist")
        
        if st.button("🗑️ Borrar archivos seleccionados", type="primary"):
            st.session_state.historial_descargas = hist_edit["Archivo"].tolist()
            st.rerun()
    
    st.divider()

    # Botón de descarga con hora exacta
    if not st.session_state.inventario_data.empty:
        ahora = datetime.now().strftime("%d-%m-%Y_%Hh%Mm")
        nombre_archivo = f"Stock_TVC_{ahora}.xlsx"
        
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            st.session_state.inventario_data.to_excel(writer, index=False)
        
        if st.download_button(label=f"📥 Bajar Excel ({ahora})", data=output.getvalue(), file_name=nombre_archivo):
            if nombre_archivo not in st.session_state.historial_descargas:
                st.session_state.historial_descargas.append(nombre_archivo)
                st.rerun()

# --- SECCIÓN: STOCK ACTUAL ---
elif opcion == "📊 Stock Actual":
    st.header("📋 Inventario Editable")
    if st.session_state.inventario_data.empty:
        st.info("No hay productos registrados.")
    else:
        # Edición directa en tabla
        editado = st.data_editor(st.session_state.inventario_data, use_container_width=True, num_rows="dynamic")
        if st.button("💾 Guardar cambios"):
            st.session_state.inventario_data = editado
            st.success("✅ ¡Inventario actualizado!")

# --- SECCIÓN: REGISTRAR/EDITAR ---
elif opcion == "📥 Registrar/Editar":
    st.header("📥 Entrada de Mercancía")
    with st.form("tvc_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            sku = st.text_input("Clave").strip()
            nom = st.text_input("Nombre")
        with col2:
            cant = st.number_input("Cantidad", min_value=1, value=1)
            ubi = st.text_input("Ubicación")
        
        if st.form_submit_button("🚀 Guardar en Memoria"):
            if sku and
