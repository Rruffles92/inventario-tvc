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
    URL_HOJA = "https://docs.google.com/spreadsheets/d/127O0eWfgzWLk2JdwsbhVK1-ye3g161s1XH7u4DaSFy8/edit?usp=sharing"
    conn = st.connection("gsheets", type=GSheetsConnection)

    def cargar_datos():
        # Cargamos los datos y limpiamos nombres de columnas por si tienen espacios
        data = conn.read(spreadsheet=URL_HOJA, ttl=0)
        data.columns = [str(c).strip() for c in data.columns]
        return data

    try:
        df = cargar_datos()
    except Exception as e:
        st.error(f"⚠️ Error al leer la hoja: {e}")
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
        
        if not df.empty and 'Clave' in df.columns:
            with st.expander("📝 Editar Información de un Producto"):
                lista_prod = df['Clave'].astype(str) + " - " + df['Nombre'].astype(str)
                sel = st.selectbox("Selecciona para editar:", lista_prod)
                clave_sel = sel.split(" - ")[0]
                idx = df[df['Clave'].astype(str) == clave_sel].index[0]
                
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
        else:
            st.warning("No se encontraron columnas válidas o la hoja está vacía. Revisa los encabezados en Google Sheets.")

    # --- 4. SECCIÓN: UBICACIONES (CON BUSCADOR) ---
    elif opcion == "📍 Ubicaciones":
        st.header("📍 Localización de Mercancía")
        buscar_clave = st.text_input("🔍 Escribe o escanea la CLAVE:").upper()
        
        if 'Clave' in df.columns:
            df_visual = df[['Clave', 'Nombre', 'Ubicacion']]
            if buscar_clave:
                df_visual = df_visual[df_visual['Clave'].astype(str).str.contains(buscar_clave, na=False)]
                if df_visual.empty:
                    st.warning(f"No se encontró la clave: {buscar_clave}")
            st.dataframe(df_visual, use_container_width=True)

    # --- 5. SECCIÓN: REGISTRAR ENTRADA ---
    elif opcion == "📥 Registrar Entrada":
        st.header("📥 Entrada de Mercancía")
        with st.form("entrada_nube"):
            col_in1, col_in2 = st.columns(2)
            c = col_in1.text_input("Clave").upper()
            n = col_in2.text_input("Nombre")
            ca = col_in1.number_input("Cantidad a sumar", min_value=1, value=1)
            u = col_in2.text_input("Ubicación")
            
            if st.form_submit_button("Sincronizar con Nube"):
                if 'Clave' in df.columns and c in df['Clave'].astype(str).values:
                    idx = df[df['Clave'].astype(str) == c].index[0]
                    df.at[idx, 'Cantidad'] += ca
                    if u: df.at[idx, 'Ubicacion'] = u
                else:
                    nueva_fila = pd.DataFrame([[c, n, ca, u]], columns=df.columns)
                    df = pd.concat([df, nueva_fila], ignore_index=True)
                
                conn.update(spreadsheet=URL_HOJA, data=df)
                st.success("✅ ¡Mercancía guardada en la Nube!")
                st.rerun()

    # --- 6. SECCIÓN: DESCARGAR TODO ---
    elif opcion == "💾 Descargar Todo":
        st.header("💾 Exportar Stock Actual")
        out = BytesIO()
        with pd.ExcelWriter(out, engine='openpyxl') as w: 
            df.to_excel(w, index=False)
        st.download_button(
            label="📥 Descargar Excel",
            data=out.getvalue(),
            file_name=f"inventario_tvc_{datetime.now().strftime('%d_%m_%Y')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
