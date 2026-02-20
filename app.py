import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
from io import BytesIO

st.set_page_config(page_title="TVC Control Nube", layout="wide")

# --- SEGURIDAD ---
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
    # Conexión con los Secrets configurados
    conn = st.connection("gsheets", type=GSheetsConnection)

    def cargar_datos():
        data = conn.read(ttl=0)
        data.columns = [str(c).strip().lower() for c in data.columns]
        return data

    df = cargar_datos()

    st.sidebar.title("☁️ TVC Menú Nube")
    opcion = st.sidebar.radio("Ir a:", ["📊 Stock y Edición", "📍 Ubicaciones", "📥 Registrar Entrada", "💾 Descargar"])

    # --- 1. STOCK Y EDICIÓN ---
    if opcion == "📊 Stock y Edición":
        st.header("📋 Inventario Sincronizado")
        st.dataframe(df, use_container_width=True)
        
        if not df.empty and 'clave' in df.columns:
            with st.expander("📝 Editar un Producto"):
                lista_prod = df['clave'].astype(str) + " - " + df['nombre'].astype(str)
                sel = st.selectbox("Selecciona:", lista_prod)
                clave_sel = sel.split(" - ")[0]
                idx = df[df['clave'].astype(str) == clave_sel].index[0]
                
                col1, col2 = st.columns(2)
                n_nom = col1.text_input("Nombre", value=df.at[idx, 'nombre'])
                n_can = col2.number_input("Cantidad", value=int(df.at[idx, 'cantidad']) if pd.notnull(df.at[idx, 'cantidad']) else 0)
                n_ubi = col1.text_input("Ubicación", value=df.at[idx, 'ubicacion'])
                
                if st.button("💾 Guardar Cambios"):
                    df.at[idx, 'nombre'] = n_nom
                    df.at[idx, 'cantidad'] = n_can
                    df.at[idx, 'ubicacion'] = n_ubi
                    conn.update(data=df)
                    st.success("✅ Actualizado!")
                    st.rerun()

    # --- 2. UBICACIONES ---
    elif opcion == "📍 Ubicaciones":
        st.header("📍 Localización")
        buscar = st.text_input("🔍 Buscar Clave:").lower()
        if 'clave' in df.columns:
            df_v = df[['clave', 'nombre', 'ubicacion']]
            if buscar:
                df_v = df_v[df_v['clave'].astype(str).lower().str.contains(buscar, na=False)]
            st.dataframe(df_v, use_container_width=True)

    # --- 3. REGISTRAR ENTRADA ---
    elif opcion == "📥 Registrar Entrada":
        st.header("📥 Nueva Entrada")
        with st.form("entrada_form", clear_on_submit=True):
            c = st.text_input("Clave").strip()
            n = st.text_input("Nombre")
            ca = st.number_input("Cantidad a sumar", min_value=1, value=1)
            u = st.text_input("Ubicación")
            
            if st.form_submit_button("🚀 Sincronizar con Nube"):
                if c and n:
                    if c.lower() in df['clave'].astype(str).str.lower().values:
                        idx = df[df['clave'].astype(str).str.lower() == c.lower()].index[0]
                        df.at[idx, 'cantidad'] = (df.at[idx, 'cantidad'] or 0) + ca
                        if u: df.at[idx, 'ubicacion'] = u
                    else:
                        nueva_fila = pd.DataFrame([[c, n, ca, u]], columns=df.columns)
                        df = pd.concat([df, nueva_fila], ignore_index=True)
                    
                    conn.update(data=df)
                    st.success(f"✅ ¡{c} guardado correctamente!")
                    st.balloons()
                else:
                    st.error("Debes llenar Clave y Nombre")

    # --- 4. DESCARGAR ---
    elif opcion == "💾 Descargar":
        st.header("💾 Generar Respaldo")
        # Forzamos la creación del buffer de descarga
        buffer = BytesIO()
        with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
            df.to_excel(writer, index=False)
        
        st.download_button(
            label="📥 Descargar Inventario en Excel",
            data=buffer.getvalue(),
            file_name=f"inventario_tvc_{datetime.now().strftime('%d_%m')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
