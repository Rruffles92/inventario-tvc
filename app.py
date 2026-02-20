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

    # --- MENÚ DE STOCK CON EDICIÓN ---
    if opcion == "📊 Stock y Edición":
        st.header("📋 Inventario (Consulta y Modificación)")
        if not df.empty:
            st.dataframe(df.style.format({"Precio": "${:,.2f} MXN"}), use_container_width=True)
            
            with st.expander("📝 Editar o Eliminar un producto"):
                sel = st.selectbox("Busca el producto por Clave:", df['Clave'] + " - " + df['Nombre'])
                idx = df[df['Clave'] == sel.split(" - ")[0]].index[0]
                
                c1, c2 = st.columns(2)
                n_nom = c1.text_input("Nuevo Nombre", value=df.at[idx, 'Nombre'])
                n_can = c1.number_input("Nueva Cantidad", value=int(df.at[idx, 'Cantidad']))
                n_ubi = c2.text_input("Nueva Ubicación", value=str(df.at[idx, 'Ubicacion']))
                n_pre = c2.number_input("Nuevo Precio MXN", value=float(df.at[idx, 'Precio']))
                
                if st.button("💾 Guardar Cambios"):
                    df.at[idx, 'Nombre'], df.at[idx, 'Cantidad'], df.at[idx, 'Ubicacion'], df.at[idx, 'Precio'] = n_nom, n_can, n_ubi, n_pre
                    guardar_inventario(df); st.success("¡Actualizado!"); st.rerun()
                if st.button("🗑️ Eliminar"):
                    df = df.drop(idx); guardar_inventario(df); st.error("Eliminado"); st.rerun()
        else: st.info("Vacío")

    # --- UBICACIONES CON EDICIÓN ---
    elif opcion == "📍 Ubicaciones":
        st.header("📍 Ubicaciones")
        st.dataframe(df[['Clave', 'Nombre', 'Ubicacion']], use_container_width=True)
        with st.expander("📍 Cambiar ubicación rápido"):
            sel_u = st.selectbox("Producto:", df['Clave'] + " - " + df['Nombre'], key="ubi_edit")
            idx_u = df[df['Clave'] == sel_u.split(" - ")[0]].index[0]
            nueva_u = st.text_input("Mover a:", value=df.at[idx_u, 'Ubicacion'])
            if st.button("Actualizar Lugar"):
                df.at[idx_u, 'Ubicacion'] = nueva_u
                guardar_inventario(df); st.success("Movido"); st.rerun()

    # --- PUNTO DE VENTA (FACTURACIÓN AUTO) ---
    elif opcion == "🛒 Punto de Venta":
        st.header("🛒 Venta")
        col1, col2 = st.columns([1, 2])
        with col1:
            cod = st.text_input("Escanea o escribe Clave:").upper()
            if cod and cod in df['Clave'].values:
                p = df[df['Clave'] == cod].iloc[0]
                if p['Cantidad'] > 0:
                    st.session_state.carrito.append({'Clave': p['Clave'], 'Nombre': p['Nombre'], 'Precio': p['Precio']})
                    st.success(f"Añadido: {p['Nombre']}")
                else: st.error("Sin Stock")
        with col2:
            if st.session_state.carrito:
                res = pd.DataFrame(st.session_state.carrito).groupby(['Clave', 'Nombre', 'Precio']).size().reset_index(name='Cant')
                res['Sub'] = res['Cant'] * res['Precio']
                st.table(res)
                total = res['Sub'].sum()
                st.write(f"### Total: ${total:,.2f} MXN")
                if st.button("🚀 Realizar Factura"):
                    fol = datetime.now().strftime("%Y%m%d%H%M%S")
                    txt = ""
                    for _, r in res.iterrows():
                        df.loc[df['Clave'] == r['Clave'], 'Cantidad'] -= r['Cant']
                        txt += f"{r['Cant']}x {r['Nombre']} | "
                    guardar_inventario(df); guardar_en_historial(fol, txt, total)
                    st.text_area("Ticket:", f"FOLIO: {fol}\nTOTAL: ${total}\nPRODUCTOS: {txt}")
                    st.session_state.carrito = []; st.success("Venta Guardada")

    # --- ENTRADA ---
    elif opcion == "📥 Registrar Entrada":
        st.header("📥 Entrada")
        with st.form("in"):
            c, n = st.text_input("Clave").upper(), st.text_input("Nombre")
            ca, u, p = st.number_input("Cantidad", 1), st.text_input("Ubicación"), st.number_input("Precio MXN")
            if st.form_submit_button("Guardar"):
                if c in df['Clave'].values:
                    idx = df[df['Clave'] == c].index[0]
                    df.at[idx, 'Cantidad'] += ca; df.at[idx, 'Precio'] = p
                else:
                    df = pd.concat([df, pd.DataFrame([[c, n, ca, u, p]], columns=df.columns)], ignore_index=True)
                guardar_inventario(df); st.success("Listo")

    # --- HISTORIAL Y DESCARGA ---
    elif opcion == "📜 Historial":
        st.header("📜 Ventas")
        st.dataframe(cargar_historial().sort_values(by='Fecha', ascending=False), use_container_width=True)

    elif opcion == "💾 Descargar":
        out = BytesIO()
        with pd.ExcelWriter(out, engine='openpyxl') as w: df.to_excel(w, index=False)
        st.download_button("📥 Bajar Excel", out.getvalue(), "inventario.xlsx")
