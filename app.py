import streamlit as st
import pandas as pd
import requests
from streamlit_gsheets import GSheetsConnection
from io import BytesIO

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Control de Inventario TVC", layout="wide")

# --- CONEXIÓN A GOOGLE DRIVE (APPS SCRIPT) ---
# Asegúrate de reemplazar esto con tu último enlace de implementación
URL_APPS_SCRIPT = "https://docs.google.com/spreadsheets/d/1a-N5oH8IJ3ouqOUv-2iHjjUMzuadHIFJJJVhnGD_Hgc/edit?gid=0#gid=0"

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

# --- CARGA DE DATOS ---
conn = st.connection("gsheets", type=GSheetsConnection)

def cargar_datos():
    # ttl=0 asegura que siempre traigamos los datos más recientes
    data = conn.read(ttl=0)
    data.columns = [str(c).strip().lower() for c in data.columns]
    return data

df = cargar_datos()

# --- MENÚ LATERAL ---
st.sidebar.title("Menú TVC")
opcion = st.sidebar.radio("Navegar a:", ["📊 Stock Actual", "📥 Registrar/Editar", "📍 Ubicaciones", "💾 Exportar Excel"])

# --- SECCIÓN: REGISTRAR O EDITAR ---
if opcion == "📥 Registrar/Editar":
    st.header("Registrar o Modificar Producto")
    with st.form("tvc_form", clear_on_submit=True):
        clave = st.text_input("SKU / Clave del Producto").strip()
        nombre = st.text_input("Nombre / Descripción del Producto")
        cantidad = st.number_input("Cantidad a sumar", min_value=1, value=1)
        ubicacion = st.text_input("Ubicación de Almacenamiento")
        
        if st.form_submit_button("🚀 Guardar en Google Drive"):
            if clave and nombre:
                # Lógica: Actualizar si existe, de lo contrario agregar
                if clave.lower() in df['clave'].astype(str).str.lower().values:
                    idx = df[df['clave'].astype(str).str.lower() == clave.lower()].index[0]
                    df.at[idx, 'cantidad'] = (df.at[idx, 'cantidad'] or 0) + cantidad
                    df.at[idx, 'nombre'] = nombre
                    if ubicacion: df.at[idx, 'ubicacion'] = ubicacion
                else:
                    nueva_fila = pd.DataFrame([[clave, nombre, cantidad, ubicacion]], columns=df.columns)
                    df = pd.concat([df, nueva_fila], ignore_index=True)
                
                # Enviando datos a Apps Script
                try:
                    js_data = df.to_json(orient='records')
                    res = requests.post(URL_APPS_SCRIPT, data=js_data)
                    if res.status_code == 200:
                        st.success("✅ ¡Guardado exitosamente en Drive!")
                        st.balloons()
                    else:
                        st.error("❌ Error: El enlace de Google no respondió correctamente.")
                except Exception as e:
                    st.error(f"❌ Error de conexión: {e}")
            else:
                st.warning("⚠️ Por favor, completa tanto la Clave como el Nombre.")

# --- SECCIÓN: UBICACIONES ---
elif opcion == "📍 Ubicaciones":
    st.header("📍 Localizador de Stock")
    busqueda = st.text_input("🔍 Buscar por SKU/Clave:").lower()
    resultados = df[df['clave'].astype(str).str.lower().str.contains(busqueda, na=False)] if busqueda else df
    st.dataframe(resultados[['clave', 'nombre', 'ubicacion']], use_container_width=True)

# --- SECCIÓN: STOCK ACTUAL ---
elif opcion == "📊 Stock Actual":
    st.header("📋 Inventario de Stock Completo")
    st.dataframe(df, use_container_width=True)

# --- SECCIÓN: EXPORTAR EXCEL ---
elif opcion == "💾 Exportar Excel":
    st.header("💾 Descargar Respaldo")
    st.write("Haz clic en el botón de abajo para descargar el stock actual como un archivo de Excel.")
    
    # Generar Excel en memoria
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Inventario')
    
    st.download_button(
        label="📥 Descargar Archivo Excel",
        data=output.getvalue(),
        file_name="respaldo_inventario_tvc.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
