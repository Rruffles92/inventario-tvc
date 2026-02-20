import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
from io import BytesIO

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
    # Conexión forzando la limpieza de caché
    conn = st.connection("gsheets", type=GSheetsConnection)

    def cargar_datos():
        # Usamos ttl=0 para que siempre lea lo más nuevo de Google
        data = conn.read(ttl=0)
        data.columns = [str(c).strip().lower() for c in data.columns]
        return data

    df = cargar_datos()

    st.sidebar.title("☁️ TVC Menú Nube")
    opcion = st.sidebar.radio("Ir a:", ["📊 Stock", "📍 Ubicaciones", "📥 Registrar Entrada", "💾 Descargar"])

    # --- SECCIÓN REGISTRAR (Donde marca el error) ---
    if opcion == "📥 Registrar Entrada":
        st.header("📥 Nueva Entrada")
        with st.form("entrada_nueva", clear_on_submit=True):
            c = st.text_input("Clave").strip()
            n = st.text_input("Nombre")
            ca = st.number_input("Cantidad", min_value=1, value=1)
            u = st.text_input("Ubicación")
            
            if st.form_submit_button("🚀 Guardar en Nube"):
                if c and n:
                    # Lógica de actualización local
                    if c.lower() in df['clave'].astype(str).str.lower().values:
                        idx = df[df['clave'].astype(str).str.lower() == c.lower()].index[0]
                        df.at[idx, 'cantidad'] = (df.at[idx, 'cantidad'] or 0) + ca
                        if u: df.at[idx, 'ubicacion'] = u
                    else:
                        nueva_fila = pd.DataFrame([[c, n, ca, u]], columns=df.columns)
                        df = pd.concat([df, nueva_fila], ignore_index=True)
                    
                    # Intento de guardado con manejo de error detallado
                    try:
                        conn.update(data=df)
                        st.success("✅ ¡Guardado con éxito!")
                        st.balloons()
                    except Exception as e:
                        st.error(f"Error técnico: {e}")
                        st.info("💡 Si el error persiste, borra la app de Streamlit Cloud y vuelve a crearla (Create App).")

    # --- SECCIÓN DESCARGAR ---
    elif opcion == "💾 Descargar":
        st.header("💾 Descargar Respaldo")
        buffer = BytesIO()
        with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
            df.to_excel(writer, index=False)
        st.download_button("📥 Descargar Excel", buffer.getvalue(), "stock_tvc.xlsx")

    # --- RESTO DE SECCIONES ---
    elif opcion == "📊 Stock":
        st.header("📋 Inventario")
        st.dataframe(df, use_container_width=True)
    elif opcion == "📍 Ubicaciones":
        st.header("📍 Ubicaciones")
        bus = st.text_input("Buscar clave:").lower()
        res = df[df['clave'].astype(str).str.lower().str.contains(bus, na=False)] if bus else df
        st.dataframe(res[['clave', 'nombre', 'ubicacion']], use_container_width=True)
