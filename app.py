import streamlit as st
import pandas as pd
import requests
from streamlit_gsheets import GSheetsConnection
from io import BytesIO

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Control de Inventario TVC", layout="wide")

# --- CONEXIÓN A GOOGLE DRIVE (LINK DE APP WEB ACTUALIZADO) ---
# He colocado el link que me acabas de pasar
URL_APPS_SCRIPT = "https://script.google.com/macros/s/AKfycbz3ps94lzy2HnVX_r4m4oeD-HgxDefZUyX_TRNk6QsHEwgzYjbPVFmzuS9I7xcK99fB/exec"

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
    # ttl=0 asegura que Streamlit siempre busque la versión más nueva en Drive
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
                # Lógica: Sumar si existe o agregar si es nuevo
                if clave.lower() in df['clave'].astype(str).str.lower().values:
                    idx = df[df['clave'].astype(str).str.lower() == clave.lower()].index[0]
                    df.at[idx, 'cantidad'] = (df.at[idx, 'cantidad'] or 0) + cantidad
                    df.at[idx, 'nombre'] = nombre
                    if ubicacion: df.at[idx, 'ubicacion'] = ubicacion
                else:
                    nueva_fila = pd.DataFrame([[clave, nombre, cantidad, ubicacion]], columns=df.columns)
                    df = pd.concat([df, nueva_fila], ignore_index=True)
                
                # Envío de datos al Apps Script
                try:
                    js_data = df.to_json(orient='records')
                    res = requests.post(URL_APPS_SCRIPT, data=js_data)
                    if res.status_code == 200:
                        st.success("✅ ¡Guardado exitosamente en Drive!")
                        st.balloons()
                    else:
                        st.error("❌ El link de Google no respondió (Verifica permisos en Drive).")
                except Exception as e:
                    st.error(f"❌ Error de conexión: {e}")
            else:
                st.warning("⚠️ Por favor, llena Clave y Nombre.")

# --- SECCIÓN: UBICACIONES ---
elif opcion == "📍 Ubicaciones":
    st.header("📍 Localizador de Stock")
    busqueda = st.text_input("🔍 Buscar por SKU/Clave:").lower()
    res = df[df['clave'].astype(str).str.lower().str.contains(busqueda, na=False)] if busqueda else df
    st.dataframe(res[['clave', 'nombre', 'ubicacion']], use_container_width=True)

# --- SECCIÓN: STOCK ACTUAL ---
elif opcion == "📊 Stock Actual":
    st.header("📋 Inventario de Stock Completo")
    st.dataframe(df, use_container_width=True)

# --- SECCIÓN: EXPORTAR EXCEL (CORREGIDA) ---
elif opcion == "💾 Exportar Excel":
    st.header("💾 Descargar Respaldo")
    # He corregido la comilla faltante en esta línea
    st.write("Haz clic en el botón de abajo para bajar el inventario a tu laptop.")
    
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Inventario')
    
    st.download_button(
        label="📥 Descargar Archivo Excel",
        data=output.getvalue(),
        file_name="inventario_tvc_final.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
