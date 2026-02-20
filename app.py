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

    # Funciones de carga y guardado
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

    st.sidebar.title("Menú Principal")
    opcion = st.sidebar.radio("Ir a:", [
        "📊 Ver Stock", 
        "📍 Ubicaciones", 
        "📥 Registrar Entrada", 
        "🛒 Punto de Venta",
        "📜 Historial de Ventas",
        "💾 Descargar Inventario"
    ])

    if st.sidebar.button("Cerrar Sesión"):
        st.session_state["autenticado"] = False
        st.rerun()

    # --- PUNTO DE VENTA ---
    if opcion == "🛒 Punto de Venta":
        st.header("🛒 Punto de Venta")
        col_scan, col_cart = st.columns([1, 2])
        
        with col_scan:
            st.subheader("Entrada de Producto")
            codigo_input = st.text_input("Escanear o Escribir Clave:", key="scanner_input").upper()
            if codigo_input:
                if codigo_input in df['Clave'].values:
                    prod = df[df['Clave'] == codigo_input].iloc[0]
                    if prod['Cantidad'] > 0:
                        st.session_state.carrito.append({'Clave': prod['Clave'], 'Nombre': prod['Nombre'], 'Precio': prod['Precio']})
                        st.success(f"✅ Añadido: {prod['Nombre']}")
                    else: st.error("❌ Sin stock")
                else: st.error("❌ No encontrado")

        with col_cart:
            st.subheader("Carrito Actual")
            if st.session_state.carrito:
                df_cart = pd.DataFrame(st.session_state.carrito)
                resumen = df_cart.groupby(['Clave', 'Nombre', 'Precio']).size().reset_index(name='Cant')
                resumen['Subtotal'] = resumen['Cant'] * resumen['Precio']
                st.table(resumen)
                total_venta = resumen['Subtotal'].sum()
                st.write(f"## TOTAL: ${total_venta:,.2f}")
                
                if st.button("🚀 Realizar Factura"):
                    folio_gen = datetime.now().strftime("%Y%m%d-%H%M%S")
                    prod_list_txt = ""
                    for _, r in resumen.iterrows():
                        idx = df[df['Clave'] == r['Clave']].index[0]
                        df.at[idx, 'Cantidad'] -= r['Cant']
                        prod_list_txt += f"{r['Cant']}x {r['Nombre']} | "
                    
                    guardar_inventario(df)
                    guardar_en_historial(folio_gen, prod_list_txt, total_venta)
                    
                    ticket = f"FOLIO: {folio_gen}\nFECHA: {datetime.now()}\nTOTAL: ${total_venta}\nPRODUCTOS: {prod_list_txt}"
                    st.text_area("📋 TICKET GENERADO:", ticket, height=200)
                    st.success(f"✅ Guardado en historial con folio {folio_gen}")
                    st.session_state.carrito = []
            else: st.info("Carrito vacío")

    # --- HISTORIAL DE VENTAS ---
    elif opcion == "📜 Historial de Ventas":
        st.header("📜 Historial de Folios y Ventas")
        hist = cargar_historial()
        if hist.empty:
            st.warning("No hay ventas registradas todavía.")
        else:
            st.write("Aquí puedes consultar todos los folios generados anteriormente:")
            st.dataframe(hist.sort_values(by='Fecha', ascending=False), use_container_width=True)
            
            # Opción para descargar el historial completo
            output_h = BytesIO()
            with pd.ExcelWriter(output_h, engine='openpyxl') as writer:
                hist.to_excel(writer, index=False)
            st.download_button("📥 Descargar Historial Completo (Excel)", output_h.getvalue(), "historial_tvc.xlsx")

    # --- OTRAS SECCIONES ---
    elif opcion == "📊 Ver Stock":
        st.header("📋 Stock Actual")
        st.dataframe(df[['Clave', 'Nombre', 'Cantidad', 'Precio']], use_container_width=True)

    elif opcion == "📍 Ubicaciones":
        st.header("📍 Ubicaciones")
        st.dataframe(df[['Clave', 'Nombre', 'Ubicacion']], use_container_width=True)

    elif opcion == "📥 Registrar Entrada":
        st.header("📥 Entrada de Mercancía")
        with st.form("entrada"):
            c1, c2 = st.columns(2)
            cl = c1.text_input("Clave").upper(); no = c1.text_input("Nombre")
            cj = c2.number_input("Cantidad", min_value=1); ub = c2.text_input("Ubicación")
            pr = c2.number_input("Precio Unitario", min_value=0.0)
            if st.form_submit_button("Guardar"):
                if cl in df['Clave'].values:
                    idx = df[df['Clave'] == cl].index[0]
                    df.at[idx, 'Cantidad'] += cj; df.at[idx, 'Precio'] = pr
                else:
                    nuevo = pd.DataFrame([[cl, no, cj, ub, pr]], columns=df.columns)
                    df = pd.concat([df, nuevo], ignore_index=True)
                guardar_inventario(df)
                st.success("✅ Actualizado")

    elif opcion == "💾 Descargar Inventario":
        st.header("💾 Exportar Inventario")
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False)
        st.download_button("📥 Descargar Excel", output.getvalue(), "inventario_tvc.xlsx")
