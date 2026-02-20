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
    if 'carrito' not in st.session_state: st.session_state.carrito = []

    st.sidebar.title("Menú Principal")
    opcion = st.sidebar.radio("Ir a:", ["📊 Stock y Edición", "📍 Ubicaciones", "📥 Registrar Entrada", "🛒 Punto de Venta", "📜 Historial", "💾 Descargar"])

    if st.sidebar.button("🚪 Cerrar Sesión"):
        st.session_state["autenticado"] = False
        st.rerun()

    # --- PUNTO DE VENTA (CON CANTIDAD PERSONALIZADA) ---
    if opcion == "🛒 Punto de Venta":
        st.header("🛒 Punto de Venta")
        col1, col2 = st.columns([1, 1.5])
        
        with col1:
            st.subheader("Agregar al Carrito")
            cod = st.text_input("Escanea o escribe Clave:").upper()
            
            if cod:
                if cod in df['Clave'].values:
                    p = df[df['Clave'] == cod].iloc[0]
                    st.info(f"Producto: *{p['Nombre']}*\n\nStock disponible: {p['Cantidad']}")
                    
                    # El cliente ahora puede elegir cuántos llevar
                    cant_pedida = st.number_input("Cantidad que pide el cliente:", min_value=1, max_value=int(p['Cantidad']), value=1)
                    
                    if st.button("➕ Agregar al Carrito"):
                        # Agregamos la cantidad de veces que pidió el cliente
                        for _ in range(int(cant_pedida)):
                            st.session_state.carrito.append({'Clave': p['Clave'], 'Nombre': p['Nombre'], 'Precio': p['Precio']})
                        st.success(f"✅ Agregadas {cant_pedida} unidades de {p['Nombre']}")
                        st.rerun()
                else:
                    st.error("❌ Clave no encontrada")

        with col2:
            st.subheader("Detalle de la Venta")
            if st.session_state.carrito:
                res = pd.DataFrame(st.session_state.carrito).groupby(['Clave', 'Nombre', 'Precio']).size().reset_index(name='Cant')
                res['Subtotal'] = res['Cant'] * res['Precio']
                
                # Mostrar tabla con formato MXN
                res_visual = res.copy()
                res_visual['Precio'] = res_visual['Precio'].map('${:,.2f} MXN'.format)
                res_visual['Subtotal'] = res_visual['Subtotal'].map('${:,.2f} MXN'.format)
                st.table(res_visual)
                
                total = res['Subtotal'].sum()
                st.write(f"## TOTAL A COBRAR: ${total:,.2f} MXN")
                
                c1, c2 = st.columns(2)
                if c1.button("❌ Vaciar Carrito"):
                    st.session_state.carrito = []
                    st.rerun()
                
                if c2.button("🚀 Realizar Factura"):
                    fol = datetime.now().strftime("%Y%m%d%H%M%S")
                    txt = ""
                    for _, r in res.iterrows():
                        df.loc[df['Clave'] == r['Clave'], 'Cantidad'] -= r['Cant']
                        txt += f"{r['Cant']}x {r['Nombre']} | "
                    
                    guardar_inventario(df)
                    guardar_en_historial(fol, txt, total)
                    
                    ticket = f"--- TVC SAN NICOLÁS ---\nFOLIO: {fol}\nFECHA: {datetime.now().strftime('%d/%m/%Y %H:%M')}\n"
                    ticket += "------------------------\n"
                    ticket += f"PRODUCTOS:\n{txt.replace('|', '\n')}"
                    ticket += "------------------------\n"
                    ticket += f"TOTAL: ${total:,.2f} MXN\n"
                    ticket += "¡Gracias por su compra!"
                    
                    st.text_area("📋 TICKET PARA IMPRIMIR:", ticket, height=250)
                    st.session_state.carrito = []
                    st.success(f"Venta finalizada. Folio: {fol}")
            else:
                st.info("El carrito está vacío.")

    # --- RESTO DE MENÚS (STOCK, UBICACIONES, ENTRADAS, ETC.) ---
    elif opcion == "📊 Stock y Edición":
        st.header("📋 Inventario Actual")
        st.dataframe(df.style.format({"Precio": "${:,.2f} MXN"}), use_container_width=True)
        with st.expander("📝 Editar o Eliminar"):
            sel = st.selectbox("Clave:", df['Clave'] + " - " + df['Nombre'])
            idx = df[df['Clave'] == sel.split(" - ")[0]].index[0]
            n_nom = st.text_input("Nombre", value=df.at[idx, 'Nombre'])
            n_can = st.number_input("Cantidad", value=int(df.at[idx, 'Cantidad']))
            n_pre = st.number_input("Precio", value=float(df.at[idx, 'Precio']))
            if st.button("Guardar Cambios"):
                df.at[idx, 'Nombre'], df.at[idx, 'Cantidad'], df.at[idx, 'Precio'] = n_nom, n_can, n_pre
                guardar_inventario(df); st.success("¡Listo!"); st.rerun()

    elif opcion == "📍 Ubicaciones":
        st.header("📍 Ubicaciones")
        st.dataframe(df[['Clave', 'Nombre', 'Ubicacion']], use_container_width=True)

    elif opcion == "📥 Registrar Entrada":
        st.header("📥 Entrada de Mercancía")
        with st.form("in"):
            c, n = st.text_input("Clave").upper(), st.text_input("Nombre")
            ca, u, p = st.number_input("Cantidad", 1), st.text_input("Ubicación"), st.number_input("Precio MXN")
            if st.form_submit_button("Guardar"):
                if c in df['Clave'].values:
                    idx = df[df['Clave'] == c].index[0]
                    df.at[idx, 'Cantidad'] += ca; df.at[idx, 'Precio'] = p
                else:
                    df = pd.concat([df, pd.DataFrame([[c, n, ca, u, p]], columns=df.columns)], ignore_index=True)
                guardar_inventario(df); st.success("Inventario actualizado")

    elif opcion == "📜 Historial":
        st.header("📜 Historial de Ventas")
        st.dataframe(cargar_historial().sort_values(by='Fecha', ascending=False), use_container_width=True)

    elif opcion == "💾 Descargar":
        out = BytesIO()
        with pd.ExcelWriter(out, engine='openpyxl') as w: df.to_excel(w, index=False)
        st.download_button("📥 Descargar Inventario Excel", out.getvalue(), "inventario_tvc.xlsx")
