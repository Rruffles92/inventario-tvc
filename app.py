import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
from io import BytesIO

# --- 1. CONFIGURACIÓN ---
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
        data = conn.read(spreadsheet=URL_HOJA, ttl=0)
        # Convertimos todos los encabezados a minúsculas para que siempre funcionen
        data.columns = [str(c).strip().lower() for c in data.columns]
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
        
        # Verificamos si existe la columna clave (en minúsculas ahora)
        if not df.empty and 'clave' in df.columns:
            with st.expander("📝 Editar Información de un Producto"):
                # Creamos la lista para el selector
                lista_prod = df['clave'].astype(str) + " - " + df['nombre'].astype(str)
                sel = st.selectbox("Selecciona para editar:", lista_prod)
                clave_sel = sel.split(" - ")[0]
                idx = df[df['clave'].astype(str) == clave_sel].index[0]
                
                col_e1, col_e2 = st.columns(2)
                n_nom = col_e1.text_input("Editar Nombre", value=df.at[idx, 'nombre'])
                n_can = col_e2.number_input("Editar Cantidad", value=int(df.at[idx, 'cantidad']) if pd.notnull(df.at[idx, 'cantidad']) else 0)
                n_ubi = col_e1.text_input("Editar Ubicación", value=df.at[idx, 'ubicacion'])
                
                if st.button("💾 Guardar Cambios en la Nube"):
                    df.at[idx, 'nombre'] = n_nom
                    df.at[idx, 'cantidad'] = n_can
                    df.at[idx, 'ubicacion'] = n_ubi
                    conn.update(spreadsheet=URL_HOJA, data=df)
                    st.success("✅ ¡Cambios sincronizados!")
                    st.rerun()
        else:
            st.warning("⚠️ Revisa que tu Google Sheets tenga los encabezados: clave, nombre, cantidad, ubicacion")

    # --- 4. SECCIÓN: UBICACIONES ---
    elif opcion == "📍 Ubicaciones":
        st.header("📍 Localización de Mercancía")
        buscar_clave = st.text_input("🔍 Escribe o escanea la CLAVE:").upper()
        
        if 'clave' in df.columns:
            df_visual = df[['clave', 'nombre', 'ubicacion']]
            if buscar_clave:
                df_visual = df_visual[df_visual['clave'].astype(str).str.contains(buscar_clave, case=False, na=False)]
            st.dataframe(df_visual, use_container_width=True)

    # --- 5. SECCIÓN: REGISTRAR ENTRADA ---
    elif opcion == "📥 Registrar Entrada":
        st.header("📥 Entrada de Mercancía")
        with st.form("entrada_nube"):
            col_in1, col_in2 = st.columns(2)
            c = col_in1.text_input("Clave").strip()
            n = col_in2.text_input("Nombre")
            ca = col_in1.number_input("Cantidad a sumar", min_value=1, value=1)
            u = col_in2.text_input("Ubicación")
            
            if st.form_submit_button("Sincronizar con Nube"):
                if 'clave' in df.columns and c.lower() in df['clave'].astype(str).str.lower().values:
                    # Si existe, sumamos
                    idx = df[df['clave'].astype(str).str.lower() == c.lower()].index[0]
                    df.at[idx, 'cantidad'] = (df.at[idx, 'cantidad'] if pd.notnull(df.at[idx, 'cantidad']) else 0) + ca
                    if u: df.at[idx, 'ubicacion'] = u
                else:
                    # Si no existe, creamos fila nueva
                    nueva_fila = pd.DataFrame([[c, n, ca, u]], columns=df.columns)
                    df = pd.concat([df, nueva_fila], ignore_index=True)
                
                conn.update(spreadsheet=URL_HOJA, data=df)
                st.success("✅ ¡Guardado en Google Sheets!")
                st.rerun()

    # --- 6. SECCIÓN: DESCARGAR ---
    elif opcion == "💾 Descargar Todo":
        st.header("💾 Exportar Stock")
        out = BytesIO()
        with pd.ExcelWriter(out, engine='openpyxl') as w: 
            df.to_excel(w, index=False)
        st.download_button("📥 Descargar Excel", out.getvalue(), f"stock_{datetime.now().strftime('%d_%m')}.xlsx")
