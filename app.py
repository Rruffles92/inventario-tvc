import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
from io import BytesIO

st.set_page_config(page_title="TVC Control Nube", layout="wide")

# --- ACCESO ---
if "autenticado" not in st.session_state:
    st.session_state["autenticado"] = False

if not st.session_state["autenticado"]:
    st.title("🔐 Acceso TVC")
    pwd = st.text_input("Contraseña:", type="password")
    if st.button("Entrar"):
        if pwd == "TVCsanicolas":
            st.session_state["autenticado"] = True
            st.rerun()
        else:
            st.error("Incorrecta")
    st.stop()

# --- CONEXIÓN ---
# Conexión directa usando los Secrets configurados
conn = st.connection("gsheets", type=GSheetsConnection)

def obtener_inventario():
    # ttl=0 obliga a leer siempre lo más nuevo de la nube
    data = conn.read(ttl=0)
    data.columns = [str(c).strip().lower() for c in data.columns]
    return data

df = obtener_inventario()

# --- MENÚ ---
st.sidebar.title("☁️ Menú Nube")
opcion = st.sidebar.radio("Ir a:", ["📊 Ver Inventario", "📥 Nueva Entrada", "📍 Ubicaciones", "💾 Descargar"])

# --- ACCIÓN: NUEVA ENTRADA (Sincronización en tiempo real) ---
if opcion == "📥 Nueva Entrada":
    st.header("📥 Registro de Mercancía")
    with st.form("form_registro", clear_on_submit=True):
        c = st.text_input("Clave").strip()
        n = st.text_input("Nombre")
        ca = st.number_input("Cantidad", min_value=1, value=1)
        u = st.text_input("Ubicación")
        
        if st.form_submit_button("🚀 Guardar en Nube"):
            if c and n:
                # 1. Buscamos si ya existe para sumar
                if c.lower() in df['clave'].astype(str).str.lower().values:
                    idx = df[df['clave'].astype(str).str.lower() == c.lower()].index[0]
                    df.at[idx, 'cantidad'] = (df.at[idx, 'cantidad'] or 0) + ca
                    if u: df.at[idx, 'ubicacion'] = u
                else:
                    # 2. Si es nuevo, lo agregamos al final
                    nueva_fila = pd.DataFrame([[c, n, ca, u]], columns=df.columns)
                    df = pd.concat([df, nueva_fila], ignore_index=True)
                
                # 3. ENVIAR A GOOGLE SHEETS
                try:
                    conn.update(data=df)
                    st.success(f"✅ ¡{c} guardado en Google y en la App!")
                    st.balloons()
                    # No hacemos rerun inmediato para dejar ver el mensaje de éxito
                except Exception as e:
                    st.error(f"Error al conectar: {e}")
            else:
                st.warning("Escribe Clave y Nombre.")

# --- SECCIÓN: VER INVENTARIO ---
elif opcion == "📊 Ver Inventario":
    st.header("📋 Stock Actualizado")
    st.dataframe(df, use_container_width=True)

# --- SECCIÓN: UBICACIONES ---
elif opcion == "📍 Ubicaciones":
    st.header("📍 Localizador")
    busqueda = st.text_input("🔍 Buscar Clave:").lower()
    if busqueda:
        resultado = df[df['clave'].astype(str).lower().str.contains(busqueda, na=False)]
        st.dataframe(resultado[['clave', 'nombre', 'ubicacion']], use_container_width=True)
    else:
        st.dataframe(df[['clave', 'nombre', 'ubicacion']], use_container_width=True)

# --- SECCIÓN: DESCARGAR ---
elif opcion == "💾 Descargar":
    st.header("💾 Respaldo Excel")
    buffer = BytesIO()
    with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
        df.to_excel(writer, index=False)
    st.download_button("📥 Descargar Archivo", buffer.getvalue(), "inventario.xlsx")
