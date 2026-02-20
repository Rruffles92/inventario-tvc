import streamlit as st
import pandas as pd
from io import BytesIO
from datetime import datetime
import requests
from streamlit_lottie import st_lottie

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="TVC Control Inventario", layout="wide", page_icon="🤖")

# Función robusta para cargar la animación
def load_lottieurl(url: str):
    try:
        r = requests.get(url, timeout=5)
        if r.status_code != 200:
            return None
        return r.json()
    except Exception as e:
        # Esto te ayudará a saber si hay un error de conexión
        st.sidebar.error(f"Error cargando robot: {e}")
        return None

# URL verificada de un robot animado (Lottie)
url_robot = "https://lottie.host/8026131b-789d-4899-b903-f09d84656041/7zH665M5K1.json"
lottie_robot = load_lottieurl(url_robot)

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
        columns=["clave", "nombre", "cajas", "piezas_por_caja", "piezas_sueltas", "ubicacion"]
    )
if "historial_descargas" not in st.session_state:
    st.session_state.historial_descargas = []

# --- BARRA LATERAL (Donde aparece el robot) ---
with st.sidebar:
    # Si la animación cargó correctamente, se muestra aquí
    if lottie_robot:
        st_lottie(lottie_robot, height=150, key="robot_sidebar")
    else:
        # Si no aparece, mostramos un emoji grande como respaldo
        st.markdown("<h1 style='text-align: center;'>🤖</h1>", unsafe_allow_html=True)
        st.caption("No se pudo cargar la animación (revisa tu conexión)")

    st.markdown("<h3 style='text-align: center;'>Asistente Virtual</h3>", unsafe_allow_html=True)
    st.markdown("---")
    
    opcion = st.radio("Navegar a:", ["📊 Stock Actual", "📥 Registrar Entrada", "📤 Retirar Producto", "💾 Exportar Excel"])
    
    st.markdown("---")
    st.markdown("### 🛠️ *Consultas IA*")
    pregunta = st.text_input("¿En qué puedo ayudarte?")
    # ... (lógica de consultas IA igual que antes)

# --- SECCIÓN: REGISTRAR ENTRADA ---
if opcion == "📥 Registrar Entrada":
    st.header("📥 Entrada de Mercancía")
    with st.form("tvc_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            sku = st.text_input("Clave").strip()
            nom = st.text_input("Nombre / Descripción")
        with col2:
            ubi = st.text_input("Ubicación")
        
        st.markdown("---")
        c1, c2, c3 = st.columns(3)
        with c1:
            cant_cajas = st.number_input("Número de Cajas", min_value=0, value=1)
        with c2:
            capacidad = st.number_input("Piezas por Caja (Capacidad)", min_value=1, value=1)
        with c3:
            cant_piezas = st.number_input("Piezas Sueltas extras", min_value=0, value=0)
        
        if st.form_submit_button("🚀 Guardar"):
            if sku and nom:
                df = st.session_state.inventario_data
                if sku.lower() in df['clave'].astype(str).str.lower().values:
                    idx = df[df['clave'].astype(str).str.lower() == sku.lower()].index[0]
                    df.at[idx, 'cajas'] += cant_cajas
                    df.at[idx, 'piezas_sueltas'] += cant_piezas
                    st.success(f"✅ Stock actualizado para {sku}.")
                else:
                    nueva = pd.DataFrame([[sku, nom, cant_cajas, capacidad, cant_piezas, ubi]], columns=df.columns)
                    st.session_state.inventario_data = pd.concat([df, nueva], ignore_index=True)
                    st.success(f"✅ Registro creado: {sku}.")
                st.rerun()

# --- SECCIÓN: RETIRAR PRODUCTO ---
elif opcion == "📤 Retirar Producto":
    st.header("📤 Retirar Producto")
    with st.form("form_retirar", clear_on_submit=True):
        sku_retirar = st.text_input("Escanear Código o ingresar Clave").strip()
        c1, c2 = st.columns(2)
        with c1:
            cajas_out = st.number_input("Cajas a retirar", min_value=0, value=0)
        with c2:
            piezas_out = st.number_input("Piezas sueltas a retirar", min_value=0, value=0)
        
        if st.form_submit_button("✅ Confirmar Salida"):
            df = st.session_state.inventario_data
            if sku_retirar.lower() in df['clave'].astype(str).str.lower().values:
                idx = df[df['clave'].astype(str).str.lower() == sku_retirar.lower()].index[0]
                
                nueva_cajas = int(df.at[idx, 'cajas']) - cajas_out
                nueva_piezas = int(df.at[idx, 'piezas_sueltas']) - piezas_out
                
                if nueva_cajas <= 0 and nueva_piezas <= 0:
                    nombre_prod = df.at[idx, 'nombre']
                    st.session_state.inventario_data = df.drop(idx).reset_index(drop=True)
                    st.error(f"🚨 PRODUCTO ELIMINADO: '{nombre_prod}' se agotó y se quitó de la ubicación.")
                else:
                    df.at[idx, 'cajas'] = max(0, nueva_cajas)
                    df.at[idx, 'piezas_sueltas'] = max(0, nueva_piezas)
                    st.success(f"📦 Retiro exitoso. Quedan {df.at[idx, 'cajas']} cajas.")
                st.rerun()
            else:
                st.error("❌ Clave no encontrada.")

# --- SECCIÓN: STOCK ACTUAL ---
elif opcion == "📊 Stock Actual":
    st.header("📋 Inventario Editable")
    if st.session_state.inventario_data.empty:
        st.info("Inventario vacío.")
    else:
        editado = st.data_editor(st.session_state.inventario_data, use_container_width=True, num_rows="dynamic")
        if st.button("💾 Guardar cambios"):
            st.session_state.inventario_data = editado
            st.success("✅ Cambios guardados.")

# --- SECCIÓN: EXPORTAR EXCEL ---
elif opcion == "💾 Exportar Excel":
    st.header("💾 Generar Reporte")
    if not st.session_state.inventario_data.empty:
        df_excel = st.session_state.inventario_data.copy()
        df_excel['TOTAL_PIEZAS'] = (df_excel['cajas'] * df_excel['piezas_por_caja']) + df_excel['piezas_sueltas']
        
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df_excel.to_excel(writer, index=False)
        
        ahora = datetime.now().strftime("%d-%m-%Y_%Hh%Mm")
        st.download_button(label=f"📥 Bajar Excel ({ahora})", data=output.getvalue(), file_name=f"Reporte_TVC_{ahora}.xlsx")
