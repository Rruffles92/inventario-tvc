import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
from io import BytesIO

# --- 1. CONFIGURACIÓN Y ACCESO ---
st.set_page_config(page_title="TVC Control Nube", layout="wide")

if "autenticado" not in st.session_state:
    st.session_state["autenticado"] = False

if not st.session_state["autenticado"]:
    st.title("🔐 Acceso TVC San Nicolás")
    pwd = st.text_input("Contraseña:", type="password")
    if st.button("Entrar"):
        if pwd == "TVCsanicolas":
            st.session_state["autenticado"] = True
            st.rerun()
        else:
            st.error("❌ Contraseña incorrecta")
    st.stop()

# --- 2. CONEXIÓN CON GOOGLE DRIVE (SHEETS) ---
# Esta conexión usa los "Secrets" que configuraste
conn = st.connection("gsheets", type=GSheetsConnection)

def cargar_datos_nube():
    # ttl=0 obliga a la app a traer lo más nuevo del Drive siempre
    data = conn.read(ttl=0)
    data.columns = [str(c).strip().lower() for c in data.columns]
    return data

df = cargar_datos_nube()

# --- 3. MENÚ LATERAL ---
st.sidebar.title("☁️ Menú TVC Nube")
opcion = st.sidebar.radio("Selecciona:", ["📊 Stock Actual", "📥 Registrar Entrada", "📍 Ubicaciones", "💾 Descargar"])

# --- 4. ACCIÓN: REGISTRAR ENTRADA Y GUARDAR EN DRIVE ---
if opcion == "📥 Registrar Entrada":
    st.header("📥 Nueva Entrada a Google Drive")
    with st.form("form_registro", clear_on_submit=True):
        col1, col2 = st.columns(2)
        c = col1.text_input("Clave del Producto").strip()
        n = col2.text_input("Nombre / Descripción")
        ca = col1.number_input("Cantidad a sumar", min_value=1, value=1)
        u = col2.text_input("Ubicación en Bodega")
        
        if st.form_submit_button("🚀 Guardar en Google Drive"):
            if c and n:
                # Lógica: Si existe, suma; si no, crea
                if c.lower() in df['clave'].astype(str).str.lower().values:
                    idx = df[df['clave'].astype(str).str.lower() == c.lower()].index[0]
                    df.at[idx, 'cantidad'] = (df.at[idx, 'cantidad'] or 0) + ca
                    if u: df.at[idx, 'ubicacion'] = u
                else:
                    nueva_fila = pd.DataFrame([[c, n, ca, u]], columns=df.columns)
                    df = pd.concat([df, nueva_fila], ignore_index=True)
                
                # ENVÍO REAL AL DRIVE
                try:
                    conn.update(data=df)
                    st.success(f"✅ ¡Producto {c} guardado exitosamente en la nube!")
                    st.balloons()
                except Exception as e:
                    st.error(f"❌ Error de conexión con Drive: {e}")
            else:
                st.warning("⚠️ Por favor completa Clave y Nombre.")

# --- 5. SECCIÓN: STOCK ---
elif opcion == "📊 Stock Actual":
    st.header("📋 Inventario Sincronizado")
    st.dataframe(df, use_container_width=True)

# --- 6. SECCIÓN: UBICACIONES ---
elif opcion == "📍 Ubicaciones":
    st.header("📍 Localizador de Mercancía")
    bus = st.text_input("🔍 Escribe la CLAVE para buscar:").lower()
    if bus:
        res = df[df['clave'].astype(str).lower().str.contains(bus, na=False)]
        st.dataframe(res[['clave', 'nombre', 'ubicacion']], use_container_width=True)
    else:
        st.dataframe(df[['clave', 'nombre', 'ubicacion']], use_container_width=True)

# --- 7. SECCIÓN: DESCARGAR ---
elif opcion == "💾 Descargar":
    st.header("💾 Exportar copia local")
    buffer = BytesIO()
    with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
        df.to_excel(writer, index=False)
    st.download_button("📥 Descargar Excel", buffer.getvalue(), "inventario_tvc.xlsx")
