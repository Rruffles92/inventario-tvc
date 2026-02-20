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

# Historial para rastrear los archivos generados
if "historial_descargas" not in st.session_state:
    st.session_state.historial_descargas = []

# --- MENÚ ---
opcion = st.sidebar.radio("Navegar a:", ["📊 Stock Actual", "📥 Registrar/Editar", "💾 Exportar Excel"])

# --- 📊 STOCK ACTUAL ---
if opcion == "📊 Stock Actual":
    st.header("📋 Inventario Actual")
    if st.session_state.inventario_data.empty:
        st.info("Inventario vacío.")
    else:
        busqueda = st.text_input("🔍 Buscar:").lower()
        df_base = st.session_state.inventario_data
        
        if busqueda:
            mask = (df_base['clave'].astype(str).str.lower().str.contains(busqueda)) | \
                   (df_base['nombre'].astype(str).str.lower().str.contains(busqueda))
            df_mostrar = df_base[mask]
        else:
            df_mostrar = df_base

        df_editado = st.data_editor(df_mostrar, use_container_width=True, num_rows="dynamic")
        if st.button("💾 Guardar cambios de la tabla"):
            st.session_state.inventario_data = df_editado
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

# --- 💾 EXPORTAR EXCEL CON BORRADO MANUAL DE HISTORIAL ---
elif opcion == "💾 Exportar Excel":
    st.header("💾 Descargar y Gestionar Documentos")
    
    if not st.session_state.inventario_data.empty:
        # Generar fecha y hora para el archivo en tiempo real
        ahora = datetime.now().strftime("%d-%m-%Y_%Hh%Mm")
        nombre_archivo = f"Inventario_TVC_{ahora}.xlsx"
        
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            st.session_state.inventario_data.to_excel(writer, index=False, sheet_name='Stock')
        
        # Al presionar el botón, se añade al historial visible
        if st.download_button(
            label=f"📥 Generar y Bajar Excel ({ahora})",
            data=output.getvalue(),
            file_name=nombre_archivo,
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        ):
            if nombre_archivo not in st.session_state.historial_descargas:
                st.session_state.historial_descargas.append(nombre_archivo)
                st.rerun()

        st.divider()
        
        # SECCIÓN PARA BORRAR MANUALMENTE REGISTROS
        st.subheader("📂 Historial de archivos (Selecciona para borrar)")
        if st.session_state.historial_descargas:
            # Crear tabla interactiva para que el usuario elija qué borrar
            df_hist = pd.DataFrame(st.session_state.historial_descargas, columns=["Archivo"])
            
            # El usuario puede borrar filas directamente en esta tabla
            hist_editado = st.data_editor(
                df_hist, 
                num_rows="dynamic", 
                use_container_width=True,
                key="editor_historial"
            )
            
            if st.button("🗑️ Borrar archivos seleccionados de la lista", type="primary"):
                st.session_state.historial_descargas = hist_editado["Archivo"].tolist()
                st.success("✅ Lista de descargas actualizada.")
                st.rerun()
        else:
            st.info("Aún no has generado descargas en esta sesión.")
    else:
        st.warning("El inventario está vacío, no hay nada que exportar.")
