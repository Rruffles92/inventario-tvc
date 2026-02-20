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
# Se guarda localmente para evitar errores de conexión con Drive
if "inventario_data" not in st.session_state:
    st.session_state.inventario_data = pd.DataFrame(
        columns=["clave", "nombre", "cantidad", "ubicacion"]
    )

# --- MENÚ LATERAL ---
st.sidebar.title("Menú TVC")
opcion = st.sidebar.radio("Navegar a:", ["📊 Stock Actual", "📥 Registrar/Editar", "💾 Exportar Excel"])

# --- SECCIÓN: REGISTRAR O EDITAR ---
if opcion == "📥 Registrar/Editar":
    st.header("Registrar o Modificar Producto")
    with st.form("tvc_form", clear_on_submit=True):
        clave = st.text_input("SKU / Clave del Producto").strip()
        nombre = st.text_input("Nombre / Descripción del Producto")
        cantidad = st.number_input("Cantidad a sumar", min_value=1, value=1)
        ubicacion = st.text_input("Ubicación de Almacenamiento")
        
        if st.form_submit_button("🚀 Guardar en Memoria"):
            if clave and nombre:
                df = st.session_state.inventario_data
                # Lógica: Actualizar si existe, agregar si es nuevo
                if clave.lower() in df['clave'].astype(str).str.lower().values:
                    idx = df[df['clave'].astype(str).str.lower() == clave.lower()].index[0]
                    df.at[idx, 'cantidad'] = (df.at[idx, 'cantidad'] or 0) + cantidad
                    df.at[idx, 'nombre'] = nombre
                    if ubicacion: df.at[idx, 'ubicacion'] = ubicacion
                    st.success(f"✅ ¡Stock de {clave} actualizado!")
                else:
                    nueva_fila = pd.DataFrame([[clave, nombre, cantidad, ubicacion]], columns=df.columns)
                    st.session_state.inventario_data = pd.concat([df, nueva_fila], ignore_index=True)
                    st.success(f"✅ ¡Producto {clave} registrado!")
                st.balloons()
            else:
                st.warning("⚠️ Completa Clave y Nombre.")

# --- SECCIÓN: STOCK ACTUAL (CON BUSCADOR) ---
elif opcion == "📊 Stock Actual":
    st.header("📋 Inventario y Buscador")
    
    if st.session_state.inventario_data.empty:
        st.info("El inventario está vacío.")
    else:
        # Buscador inteligente
        busqueda = st.text_input("🔍 Buscar por Clave o Nombre:").lower()
        
        df_ver = st.session_state.inventario_data
        # Filtrar datos en tiempo real
        if busqueda:
            mask = (df_ver['clave'].astype(str).str.lower().str.contains(busqueda)) | \
                   (df_ver['nombre'].astype(str).str.lower().str.contains(busqueda))
            df_ver = df_ver[mask]
            
        st.dataframe(df_ver, use_container_width=True)

# --- SECCIÓN: EXPORTAR EXCEL ---
elif opcion == "💾 Exportar Excel":
    st.header("💾 Descargar Todo el Stock")
    if st.session_state.inventario_data.empty:
        st.warning("No hay datos para exportar.")
    else:
        st.write("Genera un archivo Excel con todo lo registrado actualmente.")
        
        # Obtener fecha y hora para el nombre del archivo
        ahora = datetime.now().strftime("%Y-%m-%d_%H-%M")
        nombre_archivo = f"inventario_tvc_{ahora}.xlsx"
        
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            st.session_state.inventario_data.to_excel(writer, index=False, sheet_name='Stock_TVC')
        
        st.download_button(
            label=f"📥 Descargar Excel ({ahora})",
            data=output.getvalue(),
            file_name=nombre_archivo,
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
