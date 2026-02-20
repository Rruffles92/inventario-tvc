import streamlit as st
import pandas as pd
import os
from io import BytesIO
from datetime import datetime

# --- SEGURIDAD ---
def verificar_password():
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
                st.error("❌ Clave incorrecta")
        return False
    return True

if verificar_password():
    st.set_page_config(page_title="TVC Sistema Pro", layout="wide")
    FILE_NAME = 'inventario_tvc_master.xlsx'
    HISTORIAL_FILE = 'historial_ventas.xlsx'

    # --- FUNCIONES DE CARGA ---
    def cargar_inventario():
        if os.path.exists(FILE_NAME): return pd.read_excel(FILE_NAME)
        return pd.DataFrame(columns=['Clave', 'Nombre', 'Cantidad', 'Ubicacion', 'Precio'])

    def guardar_inventario(df):
        df.to_excel(FILE_NAME, index=False)

    df = cargar_inventario()

    # --- MENÚ LATERAL ---
    st.sidebar.title("Menú Principal")
    opcion = st.sidebar.radio("Ir a:", [
        "📊 Stock y Modificaciones", 
        "📥 Registrar Entrada", 
        "🛒 Punto de Venta",
        "📜 Historial de Ventas",
        "💾 Descargar Inventario"
    ])

    st.sidebar.markdown("---")
    if st.sidebar.button("🚪 Cerrar Sesión"):
        st.session_state["autenticado"] = False
        st.rerun()

    # --- 1. STOCK Y MODIFICACIONES ---
    if opcion == "📊 Stock y Modificaciones":
        st.header("📋 Stock Actual")
        if not df.empty:
            st.dataframe(df.style.format({"Precio": "${:,.2f} MXN"}), use_container_width=True)
            
            with st.expander("🛠️ Haz clic aquí para MODIFICAR o ELIMINAR un producto"):
                seleccion = st.selectbox("Busca el producto por Clave/Nombre:", df['Clave'] + " - " + df['Nombre'])
                clave_sel = seleccion.split(" - ")[0]
                idx = df[df['Clave'] == clave_sel].index[0]
                
                with st.form("form_edicion", clear_on_submit=True):
                    col1, col2 = st.columns(2)
                    n_nom = col1.text_input("Nuevo Nombre", value=df.at[idx, 'Nombre'])
                    n_cant = col1.number_input("Corregir Cantidad", value=int(df.at[idx, 'Cantidad']))
                    n_ub = col2.text_input("Nueva Ubicación", value=str(df.at[idx, 'Ubicacion']))
                    n_pre = col2.number_input("Nuevo Precio MXN", value=float(df.at[idx, 'Precio']))
                    
                    c_edit, c_del = st.columns(2)
                    if c_edit.form_submit_button("💾 Guardar Cambios"):
                        df.at[idx, 'Nombre'], df.at[idx, 'Cantidad'] = n_nom, n_cant
                        df.at[idx, 'Ubicacion'], df.at[idx, 'Precio'] = n_ub, n_pre
                        guardar_inventario(df)
                        st.success("✅ ¡Cambios guardados! Formulario limpio.")
                        st.rerun()
                    
                    if c_del.form_submit_button("🗑️ ELIMINAR PRODUCTO"):
                        df = df.drop(idx)
                        guardar_inventario(df)
                        st.warning("🗑️ Producto borrado.")
                        st.rerun()
        else: st.info("Inventario vacío.")

    # --- 2. REGISTRAR ENTRADA (CON LIMPIEZA AUTOMÁTICA) ---
    elif opcion == "📥 Registrar Entrada":
        st.header("📥 Cargar Nueva Mercancía")
        # El parámetro clear_on_submit=True hace que al picarle a Guardar, todo quede en blanco
        with st.form("entrada_nueva", clear_on_submit=True):
            c1, c2 = st.columns(2)
            f_clave = c1.text_input("Clave del Producto").upper()
            f_nom = c1.text_input("Nombre")
            f_cant = c2.number_input("Cantidad", min_value=1)
            f_ub = c2.text_input("Ubicación")
            f_pre = c2.number_input("Precio Unitario MXN", min_value=0.0)
            
            if st.form_submit_button("➕ Guardar en Inventario"):
                if f_clave in df['Clave'].values:
                    i = df[df['Clave'] == f_clave].index[0]
                    df.at[i, 'Cantidad'] += f_cant
                    df.at[i, 'Precio'] = f_pre
                else:
                    nuevo = pd.DataFrame([[f_clave, f_nom, f_cant, f_ub, f_pre]], columns=df.columns)
                    df = pd.concat([df, nuevo], ignore_index=True)
                guardar_inventario(df)
                st.success(f"✅ ¡{f_nom} guardado! Puedes ingresar el siguiente.")

    # --- 3. PUNTO DE VENTA ---
    elif opcion == "🛒 Punto de Venta":
        st.header("🛒 Punto de Venta")
        if 'carrito' not in st.session_state: st.session_state.carrito = []
        
        scan = st.text_input("Escanear o Escribir Clave:", placeholder="Listo para recibir código...").upper()
        if scan:
            if scan in df['Clave'].values:
                p = df[df['Clave'] == scan].iloc[0]
                if p['Cantidad'] > 0:
                    st.session_state.carrito.append({'Clave': p['Clave'], 'Nombre': p['Nombre'], 'Precio': p['Precio']})
                    st.toast(f"Añadido: {p['Nombre']}") # Notificación pequeña
                else: st.error("Sin stock")
            else: st.error("No existe")

        if st.session_state.carrito:
            cart_df = pd.DataFrame(st.session_state.carrito)
