import streamlit as st
import pandas as pd
from io import BytesIO
from datetime import datetime

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="TVC Control Inventario", layout="wide")

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
            st.error("❌ Contraseña Incorrecta")
    st.stop()

# --- GESTIÓN DE DATOS EN MEMORIA ---
if "inventario_data" not in st.session_state:
    st.session_state.inventario_data = pd.DataFrame(
        columns=["clave", "nombre", "cantidad", "ubicacion"]
    )

# --- MENÚ LATERAL ---
st.sidebar.title("Menú TVC")
opcion = st.sidebar.radio("Navegar a:", ["📊 Stock Actual", "📥 Registrar Nuevo", "💾 Exportar Excel"])

# --- SECCIÓN: REGISTRAR ---
if opcion == "📥 Registrar Nuevo":
    st.header("📥 Registro de Producto")
    with st.form("tvc_form", clear_on_submit=True):
        clave = st.text_input("SKU / Clave").strip()
        nombre = st.text_input("Nombre / Descripción")
        cantidad = st.number_input("Cantidad inicial", min_value=1, value=1)
        ubicacion = st.text_input("Ubicación")
        
        if st.form_submit_button("🚀 Registrar"):
            if clave and nombre:
                df = st.session_state.inventario_data
                if clave.lower() in df['clave'].astype(str).str.lower().values:
                    st.warning(f"⚠️ La clave '{clave}' ya existe. Ve a 'Stock Actual' para editarla.")
                else:
                    nueva_fila = pd.DataFrame([[clave, nombre, cantidad, ubicacion]], columns=df.columns)
                    st.session_state.inventario_data = pd.concat([df, nueva_fila], ignore_index=True)
                    st.success(f"✅ '{clave}' registrado.")
                    st.balloons()
            else:
                st.warning("⚠️ Llena los campos obligatorios.")

# --- SECCIÓN: STOCK ACTUAL (CON EDICIÓN DIRECTA) ---
elif opcion == "📊 Stock Actual":
    st.header("📋 Inventario (Edición habilitada)")
    st.info("💡 Puedes editar cualquier celda haciendo doble clic directamente en la tabla.")
    
    if st.session_state.inventario_data.empty:
        st.info("No hay productos.")
    else:
        # Buscador
        busqueda = st.text_input("🔍 Buscar:").lower()
        df_base = st.session_state.inventario_data
        
        if busqueda:
            mask = (df_base['clave'].astype(str).str.lower().str.contains(busqueda)) | \
                   (df_base['nombre'].astype(str).str.lower().str.contains(busqueda))
            df_mostrar = df_base[mask]
        else:
            df_mostrar = df_base

        # Tabla editable
        df_editado = st.data_editor(df_mostrar, use_container_width=True, num_rows="dynamic")
        
        if st.button("💾 Guardar cambios de la tabla"):
            st.session_state.inventario_data.update(df_editado)
            st.success("✅ Cambios guardados en la memoria.")

# --- SECCIÓN: EXPORTAR EXCEL ---
elif opcion == "💾 Exportar Excel":
    st.header("💾 Descargar Stock Completo")
    if not st.session_state.inventario_data.empty:
        # Fecha y hora real
        ahora = datetime.now().strftime("%d-%m-%Y_%Hh%Mm")
        nombre_archivo = f"Inventario_TVC_{ahora}.xlsx"
        
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            st.session_state.inventario_data.to_excel(writer, index=False, sheet_name='Stock')
        
        st.download_button(
            label=f"📥 Bajar Excel ({ahora})",
            data=output.getvalue(),
            file_name=nombre_archivo,
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
