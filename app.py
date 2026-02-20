import streamlit as st
import pandas as pd
from io import BytesIO
from datetime import datetime
import requests
from streamlit_lottie import st_lottie

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="TVC Control Inventario", layout="wide", page_icon="🤖")

def load_lottieurl(url: str):
    try:
        r = requests.get(url)
        return r.json() if r.status_code == 200 else None
    except:
        return None

lottie_robot = load_lottieurl("https://lottie.host/8026131b-789d-4899-b903-f09d84656041/7zH665M5K1.json")

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
    st.session_state.inventario_data = pd.DataFrame(columns=["clave", "nombre", "cantidad", "ubicacion"])
if "historial_descargas" not in st.session_state:
    st.session_state.historial_descargas = []

# --- BARRA LATERAL ---
with st.sidebar:
    if lottie_robot:
        st_lottie(lottie_robot, height=120, key="robot_animado")
    st.markdown("<h3 style='text-align: center;'>Asistente Virtual</h3>", unsafe_allow_html=True)
    st.markdown("---")
    
    opcion = st.sidebar.radio("Navegar a:", ["📊 Stock Actual", "📥 Registrar/Editar", "📤 Retirar Producto", "💾 Exportar Excel"])
    
    st.markdown("---")
    st.markdown("### 🛠️ *Consultas IA*")
    pregunta = st.text_input("¿En qué puedo ayudarte?")
    df = st.session_state.inventario_data
    if pregunta:
        if "bajo" in pregunta.lower() or "poco" in pregunta.lower():
            bajos = df[df['cantidad'].astype(int) < 5]
            if not bajos.empty:
                st.warning("🤖 Stock bajo en:")
                st.dataframe(bajos[['clave', 'cantidad']], hide_index=True)
            else:
                st.success("🤖 Stock saludable.")
        elif not df.empty:
            res = df[df.apply(lambda r: pregunta.lower() in str(r).lower(), axis=1)]
            if not res.empty:
                st.table(res[['clave', 'cantidad']])
            else:
                st.write("🤖 No encontrado.")

# --- SECCIÓN: RETIRAR PRODUCTO ---
if opcion == "📤 Retirar Producto":
    st.header("📤 Retirar Producto (Escáner o Manual)")
    with st.form("form_retirar", clear_on_submit=True):
        sku_retirar = st.text_input("Escanear Código de Barras o ingresar Clave").strip()
        cant_retirar = st.number_input("Cantidad a retirar", min_value=1, value=1)
        
        if st.form_submit_button("✅ Confirmar Salida"):
            df = st.session_state.inventario_data
            if sku_retirar.lower() in df['clave'].astype(str).str.lower().values:
                idx = df[df['clave'].astype(str).str.lower() == sku_retirar.lower()].index[0]
                nombre_prod = df.at[idx, 'nombre']
                nueva_cant = int(df.at[idx, 'cantidad']) - cant_retirar
                
                if nueva_cant > 0:
                    df.at[idx, 'cantidad'] = nueva_cant
                    st.success(f"📦 Retiro exitoso. Quedan {nueva_cant} unidades de {sku_retirar}.")
                else:
                    # Alerta visual extra y eliminación automática
                    st.session_state.inventario_data = df.drop(idx).reset_index(drop=True)
                    st.error(f"🚨 PRODUCTO ELIMINADO: '{nombre_prod}' ({sku_retirar}) llegó a 0 y se quitó de la ubicación.")
                st.toast(f"Actualizando inventario...", icon="🤖")
            else:
                st.error("❌ La clave no existe en el inventario.")

# --- SECCIÓN: REGISTRAR/EDITAR ---
elif opcion == "📥 Registrar/Editar":
    st.header("📥 Entrada de Mercancía")
    with st.form("tvc_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            sku = st.text_input("Clave").strip()
            nom = st.text_input("Nombre")
        with col2:
            cant = st.number_input("Cantidad a sumar", min_value=1, value=1)
            ubi = st.text_input("Ubicación")
        
        if st.form_submit_button("🚀 Guardar"):
            if sku and nom: # Sintaxis corregida
                df = st.session_state.inventario_data
                if sku.lower() in df['clave'].astype(str).str.lower().values:
                    idx = df[df['clave'].astype(str).str.lower() == sku.lower()].index[0]
                    df.at[idx, 'cantidad'] += cant
                    st.success(f"✅ Stock aumentado para {sku}.")
                else:
                    nueva = pd.DataFrame([[sku, nom, cant, ubi]], columns=df.columns)
                    st.session_state.inventario_data = pd.concat([df, nueva], ignore_index=True)
                    st.success(f"✅ Nuevo registro: {sku}.")
            else:
                st.warning("⚠️ Ingresa Clave y Nombre.")

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
    st.header("💾 Gestión de Documentos")
    if st.session_state.historial_descargas:
        st.subheader("🗑️ Historial de archivos generados")
        df_hist = pd.DataFrame(st.session_state.historial_descargas, columns=["Archivo"])
        hist_edit = st.data_editor(df_hist, num_rows="dynamic", use_container_width=True, key="del_hist")
        if st.button("🗑️ Borrar archivos seleccionados"):
            st.session_state.historial_descargas = hist_edit["Archivo"].tolist()
            st.rerun()
    st.divider()
    if not st.session_state.inventario_data.empty:
        ahora = datetime.now().strftime("%d-%m-%Y_%Hh%Mm")
        nombre_archivo = f"Stock_TVC_{ahora}.xlsx"
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            st.session_state.inventario_data.to_excel(writer, index=False)
        if st.download_button(label=f"📥 Bajar Excel ({ahora})", data=output.getvalue(), file_name=nombre_archivo):
            if nombre_archivo not in st.session_state.historial_descargas:
                st.session_state.historial_descargas.append(nombre_archivo)
                st.rerun()
