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

    def cargar_inventario():
        if os.path.exists(FILE_NAME): return pd.read_excel(FILE_NAME)
        return pd.DataFrame(columns=['Clave', 'Nombre', 'Cantidad', 'Ubicacion', 'Precio'])

    def guardar_inventario(df):
        df.to_excel(FILE_NAME, index=False)

    def cargar_historial():
        if os.path.exists(HISTORIAL_FILE): return pd.read_excel(HISTORIAL_FILE)
        return pd.DataFrame(columns=['Fecha', 'Folio', 'Productos', 'Total'])

    def guardar_en_historial(folio, productos_texto, total):
        historial = cargar_historial()
        nueva_venta = pd.DataFrame([[datetime.now().strftime('%d/%m/%Y %H:%M:%S'), folio, productos_texto, total]], 
                                   columns=['Fecha', 'Folio', 'Productos', 'Total'])
        historial = pd.concat([historial, nueva_venta], ignore_index=True)
        historial.to_excel(HISTORIAL_FILE, index=False)

    df = cargar_inventario()

    if 'carrito' not in st.session_state:
        st.session_state.carrito = []

    # --- FUNCIÓN REUTILIZABLE PARA MODIFICAR ---
    def panel_edicion(df_actual, titulo_seccion):
        st.divider()
        st.subheader(f"🛠️ Modificar o Eliminar desde {titulo_seccion}")
        with st.expander("Haz clic aquí para editar un producto"):
            busqueda = st.selectbox("Selecciona el producto:", df_actual['Clave'] + " - " + df_actual['Nombre'], key=f"edit_{titulo_seccion}")
            clave_sel = busqueda.split(" - ")[0]
            idx = df_actual[df_actual['Clave'] == clave_sel].index[0]
            
            c1, c2 = st.columns(2)
            n_nom = c1.text_input("Nombre:", value=df_actual.at[idx, 'Nombre'], key=f"n1_{titulo_seccion}")
            n_can = c1.number_input("Cantidad:", value=int(df_actual.at[idx, 'Cantidad']), key=f"n2_{titulo_seccion}")
            n_ubi = c2.text_input("Ubicación:", value=str(df_actual.at[idx, 'Ubicacion']), key=f"n3_{titulo_seccion}")
            n_pre = c2.number_input("Precio MXN:", value=float(df_actual.at[idx, 'Precio']), key=f"n4_{titulo_seccion}")
            
            b1, b2 = st.columns(2)
            if b1.button("💾 Guardar Cambios", key=f"btn_g_{titulo_seccion}"):
                df_actual.at[idx, 'Nombre'] = n_nom
                df_actual.at[idx, 'Cantidad'] = n_can
                df_actual.at[idx, 'Ubicacion'] = n_ubi
                df_actual.at[idx, 'Precio'] = n_pre
                guardar_inventario(df_actual)
                st.success("✅ Actualizado")
                st.rerun()
            if b2.button("🗑️ Eliminar Producto", key=f"btn_e_{titulo_seccion}"):
                df_actual = df_actual.drop(idx)
                guardar_inventario(df_actual)
                st.error("🗑️ Eliminado")
                st.rerun()

    st.sidebar.title("Menú Principal")
    opcion = st.sidebar.radio("Ir a:", [
        "📊 Ver Stock", 
        "📍 Ubicaciones", 
        "📥 Registrar Entrada", 
        "🛒 Punto de Venta",
        "📜 Historial de Ventas",
        "💾 Descargar Inventario"
    ])

    st.sidebar.markdown("---")
    if st.sidebar.button("🚪 Cerrar Sesión"):
        st.session_state["autenticado"] = False
        st.rerun()

    # --- VISTA STOCK ---
    if opcion == "📊 Ver Stock":
        st.header("📋 Stock Actual")
        st.dataframe(df[['Clave', 'Nombre', 'Cantidad', 'Precio']].assign(Precio=df['Precio'].map('${:,.2f} MXN'.format)), use_container_width=True)
        if not df.empty: panel_edicion(df, "Ver Stock")

    # --- VISTA UBICACIONES ---
    elif opcion == "📍 Ubicaciones":
        st.header("📍 Ubicaciones")
        st.dataframe(df[['Clave', 'Nombre', 'Ubicacion']], use_container_width=True)
        if not df.empty: panel_edicion(df, "Ubicaciones")

    # --- REGISTRAR ENTRADA ---
    elif opcion == "📥 Registrar Entrada":
        st.header("📥 Entrada de Mercancía")
        with st.form("entrada"):
            cl = st.text_input("Clave").upper()
            no = st.text_input("Nombre")
            cj = st.number_input("Cantidad", min_value=1)
            ub = st.text_input("Ubicación")
            pr = st.number_input("Precio Unitario MXN", min_value=0.0)
            if st.form_submit_button("Guardar"):
                if cl in df['Clave'].values:
                    idx = df[df['Clave'] == cl].index[0]
                    df.at[idx, 'Cantidad'] += cj
                    df.at[idx, 'Precio'] = pr
                else:
                    nuevo = pd.DataFrame([[cl, no, cj, ub, pr]], columns=df.columns)
                    df = pd.concat([df, nuevo], ignore_index=True)
                guardar_inventario(df)
                st.success("✅ Guardado")
                st.rerun()
        if not df.empty: panel_edicion(df, "Entradas")

    # --- PUNTO DE VENTA ---
    elif opcion == "🛒 Punto de Venta":
        st.header("🛒 Punto de Venta")
        col_scan, col_cart = st.columns([1, 2])
        with col_scan:
            codigo_input = st.text_input("Escanear o Escribir Clave:", key="scanner_input").upper()
            if codigo_input:
                if codigo_input in df['Clave'].values:
                    prod = df[df['Clave'] == codigo_input].iloc[0]
                    if prod['Cantidad'] > 0:
                        st.session_state.carrito.append({'Clave': prod['Clave'], 'Nombre': prod['Nombre'], 'Precio': prod['Precio']})
                        st.success(f"✅ {prod['Nombre']}")
                    else: st.error("❌ Sin stock")
                else: st.error("❌ No existe")

        with col_cart:
            if st.session_state.carrito:
                df_cart = pd.DataFrame(st.session_state.carrito)
                resumen = df_cart.groupby(['Clave', 'Nombre', 'Precio']).size().reset_index(name='Cant')
                resumen['Subtotal'] = resumen['Cant'] * resumen['Precio']
                st.table(resumen)
                total_v = resumen['Subtotal'].sum()
                st.write(f"## TOTAL: ${total_v:,.2f} MXN")
                
                if st.button("🚀 Realizar Factura"):
                    folio_gen = datetime.now().strftime("%Y%m%d-%H%M%S")
                    prod_txt = ""
                    for _, r in resumen.iterrows():
                        idx = df[df['Clave'] == r['Clave']].index[0]
                        df.at[idx, 'Cantidad'] -= r['Cant']
                        prod_txt += f"{r['Cant']}x {r['Nombre']} | "
                    guardar_inventario(df)
                    guardar_en_historial(folio_gen, prod_txt, total_v)
                    st.text_area("📋 TICKET:", f"FOLIO: {folio_gen}\nFECHA: {datetime.now()}\nTOTAL: ${total_v}\n{prod_txt}")
                    st.session_state.carrito = []
                    st.success("✅ Venta Realizada")
            else: st.info("Escanea productos para empezar")

    # --- HISTORIAL Y DESCARGA ---
    elif opcion == "📜 Historial de Ventas":
        st.header("📜 Historial de Ventas")
        st.dataframe(cargar_historial().sort_values(by='Fecha', ascending=False), use_container_width=True)

    elif opcion == "💾 Descargar Inventario":
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False)
        st.download_button("📥 Descargar Excel", output.getvalue(), "inventario_tvc.xlsx")
