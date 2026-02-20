import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
from io import BytesIO

# --- 1. CONFIGURACIÓN DE PÁGINA Y SEGURIDAD ---
st.set_page_config(page_title="TVC Control Nube", layout="wide")

def verificar_password():
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
        return False
    return True

if verificar_password():
    # LINK DE TU HOJA CONFIGURADO
    URL_HOJA = "https://docs.google.com/spreadsheets/d/127O0eWfgzWLk2JdwsbhVK1-ye3g161s1XH7u4DaSFy8/edit?usp=sharing"

    # Conexión con Google Sheets
    conn = st.connection("gsheets", type=GSheetsConnection)

    def cargar_datos():
        return conn.read(spreadsheet=URL_HOJA, usecols=[0,1,2,3], ttl=0)

    try:
        df = cargar_datos()
    except:
        st.error("⚠️ Error de conexión. Revisa los permisos de Editor en tu Google Sheet.")
        st.stop()

    # --- 2. BARRA LATERAL ---
    st.sidebar.title("☁️ TVC Menú Nube")
    opcion = st.sidebar.radio("Ir a:", ["📊 Stock y Edición", "📍 Ubicaciones", "📥 Registrar Entrada", "💾 Descargar Todo"])

    if st.sidebar.button("🚪 Cerrar Sesión"):
        st.session_state["autenticado"] = False
        st.rerun()

    # --- 3. SECCIÓN: STOCK Y EDICIÓN ---
    if opcion == "📊 Stock y Edición":
        st.header("📋 Inventario General (Sincronizado)")
        st.dataframe(df, use_container_width=True)
        
        if not df.empty:
            with st.expander("📝 Editar Información de un Producto"):
                lista_prod = df['Clave'].astype(str) + " - " + df['Nombre'].astype(str)
                sel = st.selectbox("Selecciona para editar:", lista_prod)
                clave_sel = sel.split(" - ")[0]
                idx = df[df['Clave'].astype(str) == clave_sel].index[0]
                
                # AQUÍ ESTABA EL ERROR, YA CORREGIDO:
                col_e1, col_e2 = st.columns(2)
                n_nom = col_e1.text_input("Editar Nombre", value=df.at[idx, 'Nombre'])
                n_can = col_e2.number_input("Editar Cantidad", value=int(df.at[idx, 'Cantidad']))
                n_ubi = col_e1.text_input("Editar Ubicación", value=df.at[idx, 'Ubicacion'])
                
                if st.button("💾 Guardar Cambios en la Nube"):
                    df.at[idx, 'Nombre'] = n_nom
                    df.at[idx, 'Cantidad'] = n_can
                    df.at[idx, 'Ubicacion'] = n_ubi
                    conn.update(spreadsheet=URL_HOJA, data=df)
                    st.success("✅ ¡Cambios sincronizados!")
                    st.rerun()

    # --- 4. SECCIÓN: UBICACIONES (CON BUSCADOR) ---
    elif opcion == "📍 Ubicaciones":
        st.header("📍 Localización de Mercancía")
        buscar_clave = st.text_input("🔍 Escribe o escanea la CLAVE:").upper()
        
        df_visual = df[['Clave', 'Nombre', 'Ubicacion']]
        if buscar_clave:
            df_visual = df_visual[df_visual['Clave'].astype(str).str.contains(buscar_clave, na=False)]
            if df_visual.empty:
                st.warning(f"No se encontró la clave: {buscar_clave}")
        
        st.dataframe(df_visual, use_container_width=True
