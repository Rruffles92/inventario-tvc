import streamlit as st
import pandas as pd
import os
from io import BytesIO
from datetime import datetime

# --- 1. SEGURIDAD ---
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
    st.set_page_config(page_title="TVC Control Stock", layout="wide")
    FILE_NAME = 'inventario_tvc_master.xlsx'

    # --- 2. FUNCIONES DE BASE DE DATOS ---
    def cargar_inventario():
        if os.path.exists(FILE_NAME): 
            return pd.read_excel(FILE_NAME)
        # Se eliminó la columna 'Precio' de la estructura base
        return pd.DataFrame(columns=['Clave', 'Nombre', 'Cantidad', 'Ubicacion'])

    def guardar_inventario(df):
        df.to_excel(FILE_NAME, index=False)

    df = cargar_inventario()

    # --- 3. BARRA LATERAL ---
    st.sidebar.title("📺 TVC Menú")
    opcion = st.sidebar.radio("Ir a:", ["📊 Stock y Edición", "📍 Ubicaciones", "📥 Registrar Entrada", "💾 Descargar Stock"])

    if st.sidebar.button("🚪 Cerrar Sesión"):
        st.session_state["autenticado"] = False
        st.rerun()

    # --- 4. SECCIÓN: STOCK Y EDICIÓN ---
    if opcion == "📊 Stock y Edición":
        st.header("📋 Inventario de Mercancía")
        # Mostramos solo las columnas de interés
        st.dataframe(df[['Clave', 'Nombre', 'Cantidad', 'Ubicacion']], use_container_width=True)
        
        if not df.empty:
            with st.expander("📝 Editar Información de Producto"):
                sel = st.selectbox("Selecciona Producto:", df['Clave'] + " - " + df['Nombre'])
                idx = df[df['Clave'] == sel.split(" - ")[0]].index[0]
                
                col_e1, col_e2 = st.columns(2)
                n_nom = col_e1.text_input("Nombre", value=df.at[idx, 'Nombre'])
                n_can = col_e2.number_input("Cantidad Actual", value=int(df.at[idx, 'Cantidad']))
                n_ubi = col_e1.text_input("Ubicación", value=df.at[idx, 'Ubicacion'])
                
                if st.button("💾 Guardar Cambios"):
                    df.at[idx, 'Nombre'] = n_nom
                    df.at[idx, 'Cantidad'] = n_can
                    df.at[idx, 'Ubicacion'] = n_ubi
                    guardar_inventario(df)
                    st.success("¡Información actualizada!")
                    st.rerun()

    # --- 5. SECCIÓN: UBICACIONES ---
    elif opcion == "📍 Ubicaciones":
        st.header("📍 Localización de Mercancía")
        buscar_clave = st.text_input("🔍 Buscar por número de CLAVE:", placeholder="Escribe o escanea...").upper()
        
        df_visual = df[['Clave', 'Nombre', 'Ubicacion']]
        if buscar_clave:
            df_visual = df_visual[df_visual['Clave'].str.contains(buscar_clave, na=False)]
            if df_visual.empty:
                st.warning(f"No se encontró la clave: {buscar_clave}")
        
        st.dataframe(df_visual, use_container_width=True)

    # --- 6. SECCIÓN: REGISTRAR ENTRADA ---
    elif opcion == "📥 Registrar Entrada":
        st.header("📥 Entrada de Mercancía")
        with st.form("in"):
            col_in1, col_in2 = st.columns(2)
            c = col_in1.text_input("Clave").upper()
            n = col_in2.text_input("Nombre")
            ca = col_in1.number_input("Cantidad a sumar", min_value=1, value=1)
            u = col_in2.text_input("Ubicación")
            
            if st.form_submit_button("Añadir al Inventario"):
                if c in df['Clave'].values:
                    idx = df[df['Clave'] == c].index[0]
                    df.at[idx, 'Cantidad'] += ca
                    if u: df.at[idx, 'Ubicacion'] = u
                else:
                    nueva_fila = pd.DataFrame([[c, n, ca, u]], columns=df.columns)
                    df = pd.concat([df, nueva_fila], ignore_index=True)
                guardar_inventario(df)
                st.success("Inventario actualizado")
                st.rerun()

    # --- 7. SECCIÓN: DESCARGAR STOCK ---
    elif opcion == "💾 Descargar Stock":
        st.header("💾 Exportar Inventario")
        st.write("Genera un archivo Excel con el stock y ubicaciones actuales.")
        
        out = BytesIO()
        with pd.ExcelWriter(out, engine='openpyxl') as w: 
            df.to_excel(w, index=False)
        
        st.download_button(
            label="📥 Descargar Excel de Stock",
            data=out.getvalue(),
            file_name=f"inventario_tvc_{datetime.now().strftime('%d_%m_%Y')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
