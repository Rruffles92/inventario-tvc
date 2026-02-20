import streamlit as st
import pandas as pd
import requests
from streamlit_gsheets import GSheetsConnection

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="TVC Movil", layout="wide")

# --- ESTILO PARA LETRAS GRANDES (CELULAR) ---
st.markdown("""
    <style>
    /* Agranda el texto de toda la página */
    html, body, [class*="css"] {
        font-size: 22px !important;
    }
    /* Agranda los títulos */
    h1 {
        font-size: 40px !important;
        color: #1E88E5 !important;
    }
    /* Agranda las etiquetas de los cuadros de texto (Clave, Nombre, etc.) */
    .stTextInput label, .stNumberInput label {
        font-size: 26px !important;
        font-weight: bold !important;
        color: #333 !important;
    }
    /* Agranda los cuadros donde escribes */
    input {
        font-size: 24px !important;
        height: 50px !important;
    }
    /* Agranda MUCHO el botón de Guardar */
    .stButton>button {
        font-size: 30px !important;
        font-weight: bold !important;
        height: 80px !important;
        width: 100% !important;
        background-color: #2e7d32 !important;
        color: white !important;
        border-radius: 15px !important;
    }
    /* Agranda las letras de la tabla de inventario */
    .stDataFrame {
        font-size: 20px !important;
    }
    </style>
    """, unsafe_allow_html=True)

# --- TU ENLACE DE DRIVE ---
URL_APPS_SCRIPT = "https://script.google.com/macros/s/AKfycbzpQPwrLR0Zey9hW8b85RsbWvHQlX6DuNu_UVowm-U2IiAIxFXIj61E2zX_GUqnG8yk/exec"

# --- SEGURIDAD ---
if "autenticado" not in st.session_state:
    st.session_state["autenticado"] = False

if not st.session_state["autenticado"]:
    st.markdown("<h1>🔐 Acceso TVC</h1>", unsafe_allow_html=True)
    password = st.text_input("Contraseña:", type="password")
    if st.button("ENTRAR"):
        if password == "TVCsanicolas":
            st.session_state["autenticado"] = True
            st.rerun()
        else:
            st.error("❌ Clave incorrecta")
    st.stop()

# --- CARGA DE DATOS ---
conn = st.connection("gsheets", type=GSheetsConnection)
def cargar_datos():
    data = conn.read(ttl=0)
    data.columns = [str(c).strip().lower() for c in data.columns]
    return data

df = cargar_datos()

# --- MENÚ ---
st.sidebar.title("MENU")
opcion = st.sidebar.radio("Ir a:", ["📊 Stock", "📥 Registrar/Editar", "📍 Ubicaciones"])

if opcion == "📥 Registrar/Editar":
    st.markdown("<h1>📥 Registro</h1>", unsafe_allow_html=True)
    with st.form("form_tvc"):
        c = st.text_input("Clave del Producto")
        n = st.text_input("Nombre / Descripción")
        ca = st.number_input("Cantidad a sumar", min_value=1, value=1)
        u = st.text_input("Ubicación")
        
        if st.form_submit_button("🚀 GUARDAR EN DRIVE"):
            if c and n:
                if c.lower() in df['clave'].astype(str).str.lower().values:
                    idx = df[df['clave'].astype(str).str.lower() == c.lower()].index[0]
                    df.at[idx, 'cantidad'] = (df.at[idx, 'cantidad'] or 0) + ca
                    df.at[idx, 'nombre'] = n
                    if u: df.at[idx, 'ubicacion'] = u
                else:
                    nueva_fila = pd.DataFrame([[c, n, ca, u]], columns=df.columns)
                    df = pd.concat([df, nueva_fila], ignore_index=True)
                
                try:
                    js_data = df.to_json(orient='records')
                    res = requests.post(URL_APPS_SCRIPT, data=js_data)
                    if res.status_code == 200:
                        st.success("✅ ¡GUARDADO!")
                        st.balloons()
                    else:
                        st.error("❌ Error de conexión")
                except:
                    st.error("❌ Error de red")

elif opcion == "📍 Ubicaciones":
    st.markdown("<h1>📍 Localizador</h1>", unsafe_allow_html=True)
    bus = st.text_input("🔎 Buscar clave:").lower()
    res = df[df['clave'].astype(str).str.lower().str.contains(bus, na=False)] if bus else df
    st.dataframe(res[['clave', 'nombre', 'ubicacion']], use_container_width=True)

elif opcion == "📊 Stock":
    st.markdown("<h1>📊 Stock Actual</h1>", unsafe_allow_html=True)
    st.dataframe(df, use_container_width=True)
