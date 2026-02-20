import streamlit as st
import pandas as pd
import requests
from streamlit_gsheets import GSheetsConnection

st.set_page_config(page_title="TVC Control Nube", layout="wide")

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
    data = conn.read(ttl=0)
    data.columns = [str(c).strip().lower() for c in data.columns]
    return data

df = cargar_datos()

st.sidebar.title("☁️ Menú TVC")
opcion = st.sidebar.radio("Ir a:", ["📊 Stock Actual", "📥 Registrar/Editar", "📍 Ubicaciones"])

# --- SECCIÓN: REGISTRAR O MODIFICAR ---
if opcion == "📥 Registrar/Editar":
    st.header("📥 Registrar o Modificar Producto")
    
    with st.form("form_edicion", clear_on_submit=True):
        c = st.text_input("Clave del Producto").strip()
        n = st.text_input("Nombre / Descripción")
        ca = st.number_input("Cantidad a sumar", min_value=1, value=1)
        u = st.text_input("Nueva Ubicación (Opcional)")
        
        # Nota para el usuario
        st.info("💡 Si la clave ya existe, se sumará la cantidad y se actualizará el nombre/ubicación.")
        
        if st.form_submit_button("🚀 Guardar Cambios en Drive"):
            if c and n:
                # LÓGICA DE MODIFICACIÓN
                if c.lower() in df['clave'].astype(str).str.lower().values:
                    idx = df[df['clave'].astype(str).str.lower() == c.lower()].index[0]
                    # Sumamos cantidad
                    df.at[idx, 'cantidad'] = (df.at[idx, 'cantidad'] or 0) + ca
                    # MODIFICAMOS nombre y ubicación con lo nuevo
                    df.at[idx, 'nombre'] = n
                    if u: df.at[idx, 'ubicacion'] = u
                    msg = f"✅ Producto {c} actualizado exitosamente."
                else:
                    # Crear nuevo si no existe
                    nueva_fila = pd.DataFrame([[c, n, ca, u]], columns=df.columns)
                    df = pd.concat([df, nueva_fila], ignore_index=True)
                    msg = f"✅ Nuevo producto {c} registrado."
                
                # ENVÍO AL DRIVE
                try:
                    js_data = df.to_json(orient='records')
                    res = requests.post(URL_APPS_SCRIPT, data=js_data)
                    if res.status_code == 200:
                        st.success(msg)
                        st.balloons()
                    else:
                        st.error("❌ Error al sincronizar con Drive.")
                except Exception as e:
                    st.error(f"❌ Fallo de red: {e}")
            else:
                st.warning("⚠️ Debes poner al menos Clave y Nombre.")

# --- SECCIÓN: UBICACIONES (Buscador) ---
elif opcion == "📍 Ubicaciones":
    st.header("📍 Localizador de Stock")
    bus = st.text_input("🔍 Escribe la clave para buscar:").lower()
    # Filtramos la tabla para mostrar ubicación
    if bus:
        res = df[df['clave'].astype(str).str.lower().str.contains(bus, na=False)]
        st.dataframe(res[['clave', 'nombre', 'ubicacion']], use_container_width=True)
    else:
        st.dataframe(df[['clave', 'nombre', 'ubicacion']], use_container_width=True)

# --- SECCIÓN: STOCK ---
elif opcion == "📊 Stock Actual":
    st.header("📋 Inventario Completo")
    st.dataframe(df, use_container_width=True)
