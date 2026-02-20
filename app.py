import streamlit as st
import pandas as pd
from io import BytesIO
from datetime import datetime

# --- CONFIGURACIÓN ---
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

# --- DATOS EN MEMORIA ---
if "inventario_data" not in st.session_state:
    st.session_state.inventario_data = pd.DataFrame(
        columns=["clave", "nombre", "cantidad", "ubicacion"]
    )

# --- MENÚ ---
opcion = st.sidebar.radio("Navegar a:", ["📊 Stock Actual", "📥 Registrar/Editar", "💾 Exportar Excel", "🗑️ Borrar Seleccionados"])

# --- 📊 STOCK ACTUAL (TABLA EDITABLE) ---
if opcion == "📊 Stock Actual":
    st.header("📋 Inventario Actual")
    if st.session_state.inventario_data.empty:
        st.info("Inventario vacío.")
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
            st.success("✅ Cambios guardados.")

# --- 📥 REGISTRAR/EDITAR ---
elif opcion == "📥 Registrar/Editar":
    st.header("📥 Registrar o Sumar Stock")
    with st.form("tvc_form", clear_on_submit=True):
        clave = st.text_input("SKU / Clave").strip()
        nombre = st.text_input("Nombre / Descripción")
        cantidad = st.number_input("Cantidad a sumar", min_value=1, value=1)
        ubicacion = st.text_input("Ubicación")
        
        if st.form_submit_button("🚀 Guardar"):
            if clave and nombre:
                df = st.session_state.inventario_data
                if clave.lower() in df['clave'].astype(str).str.lower().values:
                    idx = df[df['clave'].astype(str).str.lower() == clave.lower()].index[0]
                    df.at[idx, 'cantidad'] = int(df.at[idx, 'cantidad']) + cantidad
                    df.at[idx, 'nombre'] = nombre
                    if ubicacion: df.at[idx, 'ubicacion'] = ubicacion
                    st.success(f"✅ Stock de '{clave}' actualizado.")
                else:
                    nueva_fila = pd.DataFrame([[clave, nombre, cantidad, ubicacion]], columns=df.columns)
                    st.session_state.inventario_data = pd.concat([df, nueva_fila], ignore_index=True)
                    st.success(f"✅ '{clave}' registrado.")
            else:
                st.warning("⚠️ Falta Clave o Nombre.")

# --- 💾 EXPORTAR EXCEL ---
elif opcion == "💾 Exportar Excel":
    st.header("💾 Descargar Excel")
    if not st.session_state.inventario_data.empty:
        ahora = datetime.now().strftime("%d-%m-%Y_%Hh%Mm") # Tiempo real
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            st.session_state.inventario_data.to_excel(writer, index=False, sheet_name='Stock')
        
        st.download_button(
            label=f"📥 Bajar Excel ({ahora})",
            data=output.getvalue(),
            file_name=f"Inventario_TVC_{ahora}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    else:
        st.warning("No hay nada que descargar.")

# --- 🗑️ BORRAR SELECCIONADOS (NUEVA FUNCIÓN) ---
elif opcion == "🗑️ Borrar Seleccionados":
    st.header("🗑️ Eliminar productos específicos")
    if st.session_state.inventario_data.empty:
        st.info("El inventario está vacío.")
    else:
        st.write("Selecciona las filas que deseas eliminar y presiona el botón rojo.")
        # Usamos data_editor con num_rows="dynamic" para permitir selección y borrado
        df_actualizado = st.data_editor(
            st.session_state.inventario_data, 
            num_rows="dynamic", 
            use_container_width=True,
            key="borrador_editor"
        )
        
        if st.button("🔥 Aplicar cambios (Borrar o Editar)", type="primary"):
            st.session_state.inventario_data = df_actualizado
            st.success("✅ El inventario se ha actualizado correctamente.")
            st.rerun()
