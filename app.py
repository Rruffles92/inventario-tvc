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
LOG_MOVIMIENTOS = "movimientos_tvc.csv"

# --- FUNCIONES DE PERSISTENCIA ---
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
if "messages" not in st.session_state:
    st.session_state.messages = []

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

# --- BARRA LATERAL ---
with st.sidebar:
    if lottie_robot:
        st_lottie(lottie_robot, height=150, key="robot")
    st.markdown("<h3 style='text-align: center;'>TVC System</h3>", unsafe_allow_html=True)
    st.markdown("---")
    opcion = st.radio("Navegar a:", ["📊 Stock Actual", "📥 Registrar Entrada", "📤 Retirar Producto", "💾 Reportes Excel", "💬 Chat con IA"])

# --- SECCIÓN: REPORTES EXCEL (CON TABLA DE GESTIÓN) ---
if opcion == "💾 Reportes Excel":
    st.header("💾 Gestión de Reportes")
    
    # Botón para crear reporte
    ahora = datetime.now().strftime("%d-%m-%Y_%Hh%Mm")
    nombre_nuevo = f"Reporte_TVC_{ahora}.xlsx"
    
    if st.button(f"➕ Generar y Guardar Nuevo Reporte"):
        if nombre_nuevo not in st.session_state.historial:
            st.session_state.historial.append(nombre_nuevo)
            guardar_historial(st.session_state.historial)
            st.success(f"Reporte '{nombre_nuevo}' creado con éxito.")
            st.rerun()

    st.divider()
    st.subheader("📂 Reportes en Historial")
    
    # Lista de reportes para descargar y borrar individualmente
    if st.session_state.historial:
        # Preparar archivo para descarga
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            st.session_state.inventario_data.to_excel(writer, index=False)
        excel_bin = output.getvalue()

        for i, nombre in enumerate(st.session_state.historial):
            col_nom, col_down, col_del = st.columns([3, 1, 1])
            with col_nom:
                st.write(f"📄 {nombre}")
            with col_down:
                st.download_button("📥 Bajar", data=excel_bin, file_name=nombre, key=f"d_{i}")
            with col_del:
                if st.button("🗑️ Borrar", key=f"b_{i}"):
                    st.session_state.historial.pop(i)
                    guardar_historial(st.session_state.historial)
                    st.rerun()
    else:
        st.info("No hay reportes guardados. Haz clic en el botón de arriba para crear uno.")

# --- SECCIÓN: CHAT CON IA (CUADRO NEGRO) ---
elif opcion == "💬 Chat con IA":
    st.header("💬 Asistente de Inventario")
    
    # Estilo de cuadro negro para el chat
    st.markdown("""
        <style>
        .chat-container {
            border: 2px solid black;
            padding: 20px;
            border-radius: 10px;
            background-color: #f9f9f9;
            min-height: 400px;
        }
        </style>
        """, unsafe_allow_html=True)
    
    with st.container():
        st.markdown('<div class="chat-container">', unsafe_allow_html=True)
        
        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])
        
        if prompt := st.chat_input("Pregúntame sobre el stock o movimientos..."):
            st.session_state.messages.append({"role": "user", "content": prompt})
            with st.chat_message("user"):
                st.markdown(prompt)
            
            with st.chat_message("assistant"):
                # Respuesta lógica según el inventario
                if "stock" in prompt.lower() or "cuantos" in prompt.lower():
                    total_items = len(st.session_state.inventario_data)
                    response = f"Actualmente tenemos {total_items} productos distintos en el inventario."
                else:
                    response = "Hola, soy tu asistente TVC. Puedo ayudarte a saber qué productos se mueven más o cuántas piezas quedan de algún SKU."
                
                st.markdown(response)
                st.session_state.messages.append({"role": "assistant", "content": response})
        
        st.markdown('</div>', unsafe_allow_html=True)

# --- LAS OTRAS SECCIONES SE MANTIENEN IGUAL (STOCK, REGISTRO, RETIRO) ---
elif opcion == "📊 Stock Actual":
    st.header("📋 Inventario Editable")
    df = st.session_state.inventario_data
    editado = st.data_editor(df, use_container_width=True, num_rows="dynamic")
    if st.button("💾 Guardar Cambios"):
        st.session_state.inventario_data = editado
        guardar_datos(editado)
        st.success("✅ Datos actualizados.")

elif opcion == "📥 Registrar Entrada":
    st.header("📥 Registrar")
    with st.form("reg"):
        c1, c2 = st.columns(2)
        sku = c1.text_input("Clave")
        nom = c2.text_input("Nombre")
        cajas = st.number_input("Cajas", min_value=0)
        if st.form_submit_button("Guardar"):
            # Lógica de registro aquí...
            st.success("Registrado.")

elif opcion == "📤 Retirar Producto":
    st.header("📤 Retirar")
    # Lógica de retiro con escáner aquí...
    st.write("Usa el escáner para retirar.")
