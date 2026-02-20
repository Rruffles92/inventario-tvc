import streamlit as st
import pandas as pd
import requests
from streamlit_gsheets import GSheetsConnection
from io import BytesIO

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="TVC Control Inventario", layout="wide")

# --- CONEXIÓN AL DRIVE ---
URL_APPS_SCRIPT = "https://script.google.com/macros/s/AKfycbzpQPwrLR0Zey9hW8b85RsbWvHQlX6DuNu_UVowm-U2IiAIxFXIj61E2zX_GUqnG8yk/exec"

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
            st.error("❌ Clave incorrecta")
    st.stop()

# --- CARGA DE DATOS ---
conn = st.connection("gsheets", type=GSheetsConnection)

def cargar_datos():
    # Leemos la hoja sin caché para ver lo más nuevo
    data = conn.read(ttl=0)
    data.columns = [str(c).strip().lower() for c in data.columns]
    return data

df = cargar_datos()

# --- MENÚ LATERAL ---
st.sidebar.title("Menú TVC")
opcion = st.sidebar.radio("Ir a:", ["📊 Stock Actual", "📥 Registrar/Editar", "📍 Ubicaciones", "💾 Descargar Excel"])

# --- SECCIÓN: REGISTRAR O MODIFICAR ---
if opcion == "📥 Registrar/Editar":
    st.header("Registrar o Modificar Producto")
    with st.form("form_tvc", clear_on_submit=True):
        c = st.text_input("Clave del Producto").strip()
        n = st.text_input("Nombre / Descripción")
        ca = st.number_input("Cantidad a sumar", min_value=1, value=1)
        u = st.text_input("Ubicación")
        
        if st.form_submit_button("🚀 Guardar en Google Drive"):
            if c and n:
                # Si existe, sumamos; si no, creamos
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
                        st.success("✅ ¡Sincronizado con Drive!")
                        st.balloons()
                    else:
                        st.error("❌ Error de conexión con Drive.")
                except:
                    st.error("❌ Error de red.")
            else:
                st.warning("⚠️ Completa Clave y Nombre.")

# --- SECCIÓN: UBICACIONES ---
elif opcion == "📍 Ubicaciones":
    st.header("📍 Localizador de Stock")
    bus = st.text_input("🔍 Escribe la clave para buscar:").lower()
    res = df[df['clave'].astype(str).str.lower().str.contains(bus, na=False)] if bus else df
    st.dataframe(res[['clave', 'nombre', 'ubicacion']], use_container_width=True)

# --- SECCIÓN: STOCK ACTUAL ---
elif opcion == "📊 Stock Actual":
    st.header("📋 Inventario Completo")
    st.dataframe(df, use_container_width=True)

# --- NUEVA SECCIÓN: DESCARGAR EXCEL ---
elif opcion == "💾 Descargar Excel":
    st.header("💾 Exportar Inventario")
    st.write("Haz clic en el botón de abajo para descargar una copia en Excel de todo el stock.")
    
    # Creamos el archivo en memoria
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Stock')
    
    st.download_button(
        label="📥 Descargar Archivo Excel",
        data=output.getvalue(),
        file_name="inventario_tvc_actual.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
