import streamlit as st
import pandas as pd
import requests
from streamlit_gsheets import GSheetsConnection
from datetime import datetime
from io import BytesIO

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="TVC Control Nube", layout="wide")

# --- ENLACE DE CONEXIÓN (APPS SCRIPT) ---
# Este es el túnel que permite guardar en Drive sin errores
URL_APPS_SCRIPT = "https://script.google.com/macros/s/AKfycbzpQPwrLR0Zey9hW8b85RsbWvHQlX6DuNu_UVowm-U2IiAIxFXIj61E2zX_GUqnG8yk/exec"

# --- ACCESO CON CONTRASEÑA ---
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
            st.error("❌ Clave incorrecta")
    st.stop()

# --- CONEXIÓN A GOOGLE SHEETS ---
conn = st.connection("gsheets", type=GSheetsConnection)

def cargar_datos():
    # Leemos la hoja de Google con caché desactivada para ver cambios reales
    data = conn.read(ttl=0)
    # Convertimos encabezados a minúsculas para evitar fallos de lectura
    data.columns = [str(c).strip().lower() for c in data.columns]
    return data

df = cargar_datos()

# --- MENÚ DE NAVEGACIÓN ---
st.sidebar.title("☁️ TVC Menú Nube")
opcion = st.sidebar.radio("Ir a:", ["📊 Stock Actual", "📥 Registrar Entrada", "📍 Ubicaciones", "💾 Descargar Excel"])

# --- SECCIÓN: REGISTRAR ENTRADA ---
if opcion == "📥 Registrar Entrada":
    st.header("📥 Registro de Mercancía")
    with st.form("form_tvc", clear_on_submit=True):
        col1, col2 = st.columns(2)
        c = col1.text_input("Clave del Producto").strip()
        n = col2.text_input("Nombre / Descripción")
        ca = col1.number_input("Cantidad a sumar", min_value=1, value=1)
        u = col2.text_input("Ubicación en Bodega")
        
        if st.form_submit_button("🚀 Guardar en Google Drive"):
            if c and n:
                # Sumamos si la clave existe, o creamos fila nueva
                if c.lower() in df['clave'].astype(str).str.lower().values:
                    idx = df[df['clave'].astype(str).str.lower() == c.lower()].index[0]
                    df.at[idx, 'cantidad'] = (df.at[idx, 'cantidad'] or 0) + ca
                    if u: df.at[idx, 'ubicacion'] = u
                else:
                    nueva_fila = pd.DataFrame([[c, n, ca, u]], columns=df.columns)
                    df = pd.concat([df, nueva_fila], ignore_index=True)
                
                # ENVÍO AL DRIVE POR EL TÚNEL
                try:
                    js_data = df.to_json(orient='records')
                    res = requests.post(URL_APPS_SCRIPT, data=js_data)
                    if res.status_code == 200:
                        st.success(f"✅ ¡{c} guardado en Google Drive y actualizado en App!")
                        st.balloons()
                    else:
                        st.error("❌ Error: El túnel de Google no respondió.")
                except Exception as e:
                    st.error(f"❌ Fallo de conexión: {e}")
            else:
                st.warning("⚠️ Completa Clave y Nombre.")

# --- SECCIÓN: UBICACIONES ---
elif opcion == "📍 Ubicaciones":
    st.header("📍 Localizador de Stock")
    bus = st.text_input("🔍 Escribe la clave para buscar:").lower()
    if 'clave' in df.columns:
        res = df[df['clave'].astype(str).str.lower().str.contains(bus, na=False)] if bus else df
        st.dataframe(res[['clave', 'nombre', 'ubicacion']], use_container_width=True)

# --- SECCIÓN: STOCK COMPLETO ---
elif opcion == "📊 Stock Actual":
    st.header("📋 Inventario Sincronizado")
    st.dataframe(df, use_container_width=True)

# --- SECCIÓN: DESCARGAR ---
elif opcion == "💾 Descargar Excel":
    st.header("💾 Generar Copia de Seguridad")
    buffer = BytesIO()
    with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
        df.to_excel(writer, index=False)
    st.download_button("📥 Descargar Archivo", buffer.getvalue(), "inventario_tvc.xlsx")
