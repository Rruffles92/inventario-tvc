import streamlit as st
import pandas as pd
import os
from io import BytesIO
from datetime import datetime

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="TVC Control Inventario", layout="wide", page_icon="🤖")
DB_FILE = "inventario_tvc.csv"
HISTORIAL_FILE = "historial_reportes.txt"

def cargar_datos():
    if os.path.exists(DB_FILE):
        return pd.read_csv(DB_FILE)
    return pd.DataFrame(columns=["clave", "nombre", "cajas", "piezas_por_caja", "piezas_sueltas", "ubicacion"])

def guardar_datos(df):
    df.to_csv(DB_FILE, index=False)

def cargar_historial():
    if os.path.exists(HISTORIAL_FILE):
        with open(HISTORIAL_FILE, "r") as f:
            return [line.strip() for line in f.readlines()]
    return []

def guardar_historial(lista):
    with open(HISTORIAL_FILE, "w") as f:
        for item in lista:
            f.write(f"{item}\n")

if "inventario_data" not in st.session_state:
    st.session_state.inventario_data = cargar_datos()
if "historial" not in st.session_state:
    st.session_state.historial = cargar_historial()

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
        else: st.error("❌ Incorrecta")
    st.stop()

# --- BARRA LATERAL ---
with st.sidebar:
    st.title("TVC System")
    opcion = st.radio("Navegar a:", ["📊 Stock Actual", "📥 Registrar Entrada", "📤 Retirar Producto", "💾 Reportes Excel"])
    
    st.markdown("---")
    # CHAT PEQUEÑO CON BORDES NEGROS AL FINAL
    st.markdown('<div style="border: 2px solid black; padding: 10px; border-radius: 5px; background-color: #ffffff;">', unsafe_allow_html=True)
    st.caption("🤖 Asistente IA")
    user_msg = st.text_input("Consultar:", key="chat_min", placeholder="Escribe aquí...")
    if user_msg:
        if "stock" in user_msg.lower():
            st.write(f"Respuesta: Tenemos {len(st.session_state.inventario_data)} productos.")
        else:
            st.write("Respuesta: ¿En qué puedo ayudarte?")
    st.markdown('</div>', unsafe_allow_html=True)

# --- SECCIÓN: STOCK ACTUAL ---
if opcion == "📊 Stock Actual":
    st.header("📋 Inventario Editable")
    df = st.session_state.inventario_data
    editado = st.data_editor(df, use_container_width=True, num_rows="dynamic")
    if st.button("💾 Guardar Cambios"):
        st.session_state.inventario_data = editado
        guardar_datos(editado)
        st.success("✅ Datos guardados.")

# --- SECCIÓN: REGISTRAR (CON TODAS LAS OPCIONES) ---
elif opcion == "📥 Registrar Entrada":
    st.header("📥 Registrar Producto")
    with st.form("form_reg", clear_on_submit=True):
        col1, col2 = st.columns(2)
        sku = col1.text_input("Clave (Scan)").strip()
        nom = col2.text_input("Nombre")
        
        c1, c2, c3 = st.columns(3)
        caj = c1.number_input("Cajas", min_value=0, value=0)
        pxc = c2.number_input("Piezas por caja", min_value=1, value=1)
        slt = c3.number_input("Piezas sueltas", min_value=0, value=0)
        
        ubi = st.text_input("Ubicación")
        
        if st.form_submit_button("✅ Guardar"):
            df = st.session_state.inventario_data
            mask = df['clave'].astype(str) == sku
            if mask.any():
                idx = df[mask].index[0]
                df.at[idx, 'cajas'] += caj
                df.at[idx, 'piezas_sueltas'] += slt
            else:
                nueva = pd.DataFrame([[sku, nom, caj, pxc, slt, ubi]], columns=df.columns)
                df = pd.concat([df, nueva], ignore_index=True)
            guardar_datos(df)
            st.session_state.inventario_data = df
            st.rerun()

# --- SECCIÓN: RETIRAR (SOLO DESCUENTO DE PIEZAS) ---
elif opcion == "📤 Retirar Producto":
    st.header("📤 Retirar Piezas")
    df = st.session_state.inventario_data
    sku_ret = st.text_input("Escanea Clave para retirar piezas:").strip()
    
    if sku_ret:
        mask = df['clave'].astype(str) == sku_ret
        if mask.any():
            idx = df[mask].index[0]
            item = df.loc[idx]
            # Calculamos piezas totales disponibles para el usuario
            st.info(f"📦 Producto: {item['nombre']} | Piezas sueltas actuales: {item['piezas_sueltas']}")
            
            with st.form("f_ret_piezas"):
                cant_piezas = st.number_input("Cantidad de piezas a descontar", min_value=0, max_value=int(item['piezas_sueltas']))
                
                if st.form_submit_button("Confirmar Descuento"):
                    df.at[idx, 'piezas_sueltas'] -= cant_piezas
                    
                    # Si ya no quedan piezas sueltas ni cajas, se puede borrar o dejar en 0
                    if df.at[idx, 'piezas_sueltas'] < 0:
                        df.at[idx, 'piezas_sueltas'] = 0
                    
                    guardar_datos(df)
                    st.session_state.inventario_data = df
                    st.success(f"Se descontaron {cant_piezas} piezas de la clave {sku_ret}")
                    st.rerun()
        else:
            st.error("No se encontró la clave en el inventario.")

# --- SECCIÓN: REPORTES ---
elif opcion == "💾 Reportes Excel":
    st.header("💾 Gestión de Reportes")
    nombre_rep = f"Reporte_{datetime.now().strftime('%d-%m-%Y_%Hh%Mm')}.xlsx"
    
    if st.button(f"➕ Crear Reporte: {nombre_rep}"):
        if nombre_rep not in st.session_state.historial:
            st.session_state.historial.append(nombre_rep)
            guardar_historial(st.session_state.historial)
            st.rerun()

    st.divider()
    if st.session_state.historial:
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            st.session_state.inventario_data.to_excel(writer, index=False)
        excel_bin = output.getvalue()

        for i, nombre in enumerate(st.session_state.historial):
            c1, c2, c3 = st.columns([3, 1, 1])
            c1.write(f"📄 {nombre}")
            c2.download_button("📥 Bajar", data=excel_bin, file_name=nombre, key=f"dl_{i}")
            if c3.button("🗑️ Borrar", key=f"br_{i}"):
                st.session_state.historial.pop(i)
                guardar_historial(st.session_state.historial)
                st.rerun()
