import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
from io import BytesIO

# --- CONFIGURACIÓN DE PÁGINA ---
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
    # Conexión automática usando los Secrets que ya configuraste
    conn = st.connection("gsheets", type=GSheetsConnection)

    def cargar_datos():
        # Cargamos datos y normalizamos encabezados a minúsculas
        data = conn.read(ttl=0)
        data.columns = [str(c).strip().lower() for c in data.columns]
        return data

    try:
        df = cargar_datos()
    except Exception as e:
        st.error(f"⚠️ Error al conectar con Google Sheets: {e}")
        st.stop()

    # --- MENÚ LATERAL ---
    st.sidebar.title("☁️ TVC Menú Nube")
    opcion = st.sidebar.radio("Ir a:", ["📊 Stock y Edición", "📍 Ubicaciones", "📥 Registrar Entrada", "💾 Descargar"])

    # --- 1. STOCK Y EDICIÓN ---
    if opcion == "📊 Stock y Edición":
        st.header("📋 Inventario Sincronizado")
        st.dataframe(df, use_container_width=True)
        
        if not df.empty and 'clave' in df.columns:
            with st.expander("📝 Editar un Producto Existente"):
                # Selector de producto combinando clave y nombre
                lista_prod = df['clave'].astype(str) + " - " + df['nombre'].astype(str)
                sel = st.selectbox("Selecciona para editar:", lista_prod)
                clave_sel = sel.split(" - ")[0]
                idx = df[df['clave'].astype(str) == clave_sel].index[0]
                
                col_e1, col_e2 = st.columns(2)
                n_nom = col_e1.text_input("Editar Nombre", value=df.at[idx, 'nombre'])
                n_can = col_e2.number_input("Editar Cantidad", value=int(df.at[idx, 'cantidad']) if pd.notnull(df.at[idx, 'cantidad']) else 0)
                n_ubi = col_e1.text_input("Editar Ubicación", value=df.at[idx, 'ubicacion'])
                
                if st.button("💾 Guardar Cambios"):
                    df.at[idx, 'nombre'] = n_nom
                    df.at[idx, 'cantidad'] = n_can
                    df.at[idx, 'ubicacion'] = n_ubi
                    # Actualiza la hoja de Google Sheets
                    conn.update(data=df)
                    st.success("✅ ¡Actualizado en la nube!")
                    st.rerun()

    # --- 2. UBICACIONES ---
    elif opcion == "📍 Ubicaciones":
        st.header("📍 Localización de Mercancía")
        # Buscador por clave (mayúsculas/minúsculas no importan)
        buscar = st.text_input("🔍 Escribe o escanea la CLAVE:").lower()
        if 'clave' in df.columns:
            df_v = df[['clave', 'nombre', 'ubicacion']]
            if buscar:
                df_v = df_v[df_v['clave'].astype(str).str.lower().str.contains(buscar, na=False)]
            st.dataframe(df_v, use_container_width=True)

    # --- 3. REGISTRAR ENTRADA ---
    elif opcion == "📥 Registrar Entrada":
        st.header("📥 Entrada de Mercancía")
        with st.form("nueva_entrada"):
            col_in1, col_in2 = st.columns(2)
            c = col_in1.text_input("Clave").strip()
            n = col_in2.text_input("Nombre")
            ca = col_in1.number_input("Cantidad a sumar", min_value=1, value=1)
            u = col_in2.text_input("Ubicación")
            
            if st.form_submit_button("🚀 Sincronizar con Nube"):
                # Si el producto existe, sumamos cantidad; si no, creamos fila
                if c.lower() in df['clave'].astype(str).str.lower().values:
                    idx = df[df['clave'].astype(str).str.lower() == c.lower()].index[0]
                    df.at[idx, 'cantidad'] = (df.at[idx, 'cantidad'] or 0) + ca
                    if u: df.at[idx, 'ubicacion'] = u
                else:
                    nueva_fila = pd.DataFrame([[c, n, ca, u]], columns=df.columns)
                    df = pd.concat([df, nueva_fila], ignore_index=True)
                
                # Sincronización final
