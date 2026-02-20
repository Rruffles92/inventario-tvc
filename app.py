import streamlit as st
import pandas as pd
from io import BytesIO
from datetime import datetime

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="TVC Control Inventario", layout="wide", page_icon="🤖")

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

# --- DATOS Y LOGS ---
if "inventario_data" not in st.session_state:
    st.session_state.inventario_data = pd.DataFrame(
        columns=["clave", "nombre", "cantidad", "ubicacion"]
    )
if "historial_descargas" not in st.session_state:
    st.session_state.historial_descargas = []

# --- BARRA LATERAL CON IA KAWAII ---
with st.sidebar:
    st.markdown("<h2 style='text-align: center;'>🤖</h2>", unsafe_allow_html=True)
    st.markdown("### <center>Gemini Mini-Bot</center>", unsafe_allow_html=True)
    st.caption("<center>✨ ¡Hola! Soy tu asistente kawaii de TVC ✨</center>", unsafe_allow_html=True)
    st.markdown("---")
    
    opcion = st.radio("Navegar a:", ["📊 Stock Actual", "📥 Registrar/Editar", "💾 Exportar Excel"])
    
    st.markdown("---")
    st.markdown("### 🛠️ *Consultas IA*")
    pregunta = st.text_input("Pregúntame algo:", placeholder="Ej: ¿Qué hay poco?")
    
    # Lógica de IA Kawaii
    df = st.session_state.inventario_data
    if pregunta:
        if "poco" in pregunta.lower() or "bajo" in pregunta.lower():
            bajos = df[df['cantidad'].astype(int) < 5]
            if not bajos.empty:
                st.warning("⚠️ ¡Atención! Estos productos se están agotando:")
                st.dataframe(bajos[['clave', 'cantidad']], hide_index=True)
            else:
                st.success("🤖 ¡Todo bien! Tienes buen stock de todo.")
        elif not df.empty:
            res = df[df.apply(lambda r: pregunta.lower() in str(r).lower(), axis=1)]
            if not res.empty:
                st.write("🔍 Encontré esto:")
                st.table(res[['clave', 'cantidad']])
            else:
                st.write("🤖 No veo nada con ese nombre...")
        else:
            st.error("🤖 ¡El inventario está vacío!")

# --- 💾 SECCIÓN: EXPORTAR Y GESTIONAR (ARRIBA) ---
if opcion == "💾 Exportar Excel":
    st.header("💾 Gestión de Documentos")
    
    # Gestión manual del historial en la parte superior
    if st.session_state.historial_descargas:
        st.subheader("🗑️ Historial de la sesión")
        df_hist = pd.DataFrame(st.session_state.historial_descargas, columns=["Archivo"])
        hist_edit = st.data_editor(df_hist, num_rows="dynamic", use_container_width=True, key="superior_del")
        
        if st.button("🗑️ Eliminar seleccionados del historial", type="primary"):
            st.session_state.historial_descargas = hist_edit["Archivo"].tolist()
            st.rerun()
    
    st.divider()

    # Botón de descarga con hora real
    if not st.session_state.inventario_data.empty:
        ahora = datetime.now().strftime("%d-%m-%Y_%Hh%Mm")
        nombre_file = f"Stock_TVC_{ahora}.xlsx"
        
        out = BytesIO()
        with pd.ExcelWriter(out, engine='openpyxl') as writer:
            st.session_state.inventario_data.to_excel(writer, index=False)
        
        if st.download_button(label=f"📥 Descargar ahora ({ahora})", data=out.getvalue(), file_name=nombre_file):
            if nombre_file not in st.session_state.historial_descargas:
                st.session_state.historial_descargas.append(nombre_file)
                st.rerun()

# --- 📊 STOCK ACTUAL ---
elif opcion == "📊 Stock Actual":
    st.header("📋 Inventario Editable")
    if st.session_state.inventario_data.empty:
        st.info("No hay productos.")
    else:
        # Edición directa
        edit = st.data_editor(st.session_state.inventario_data, use_container_width=True, num_rows="dynamic")
        if st.button("💾 Guardar cambios"):
            st.session_state.inventario_data = edit
            st.success("✅ ¡Actualizado!")

# --- 📥 REGISTRAR/EDITAR ---
elif opcion == "📥 Registrar/Editar":
    st.header("📥 Registro / Actualización")
    with st.form("form_tvc", clear_on_submit=True):
        c1, c2 = st.columns(2)
        with c1:
            sku = st.text_input("Clave").strip()
            nom = st.text_input("Nombre")
        with c2:
            cant = st.number_input("Cantidad a sumar", min_value=1)
            ubica = st.text_input("Ubicación")
        
        if st.form_submit_button("🚀 Guardar"):
            if sku and nom:
                df = st.session_state.inventario_data
                if sku.lower() in df['clave'].astype(str).str.lower().values:
                    idx = df[df['clave'].astype(str).str.lower() == sku.lower()].index[0]
                    df.at[idx, 'cantidad'] += cant
                    st.success(f"✅ Se sumaron {cant} unidades a {sku}.")
                else:
                    nueva = pd.DataFrame([[sku, nom, cant, ubica]], columns=df.columns)
                    st.session_state.inventario_data = pd.concat([df, nueva], ignore_index=True)
                    st.success(f"✅ {sku} registrado correctamente.")
            else:
                st.warning("Escribe Clave y Nombre.")
