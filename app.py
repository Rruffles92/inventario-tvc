import streamlit as st
import pandas as pd
import os
from io import BytesIO
from datetime import datetime
import random
import streamlit.components.v1 as components

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

    # --- FUNCIONES DE BASE DE DATOS ---
    def cargar_inventario():
        if os.path.exists(FILE_NAME): return pd.read_excel(FILE_NAME)
        return pd.DataFrame(columns=['Clave', 'Nombre', 'Cantidad', 'Ubicacion', 'Precio'])

    def guardar_inventario(df):
        df.to_excel(FILE_NAME, index=False)

    def cargar_historial():
        if os.path.exists(HISTORIAL_FILE): return pd.read_excel(HISTORIAL_FILE)
        return pd.DataFrame(columns=['Fecha', 'Folio', 'Productos', 'Total'])

    def guardar_en_historial(df_historial):
        df_historial.to_excel(HISTORIAL_FILE, index=False)

    def registrar_venta_historial(folio, productos_texto, total):
        historial = cargar_historial()
        nueva_venta = pd.DataFrame([[datetime.now().strftime('%d/%m/%Y %H:%M:%S'), folio, productos_texto, total]], 
                                   columns=['Fecha', 'Folio', 'Productos', 'Total'])
        historial = pd.concat([historial, nueva_venta], ignore_index=True)
        guardar_en_historial(historial)

    def generar_folio_corto():
        tipo = random.choice([4, 6])
        if tipo == 4:
            return f"{random.randint(10, 99)}{random.randint(10, 99)}"
        else:
            return f"{random.randint(100, 999)}{random.randint(100, 999)}"

    df = cargar_inventario()
    if 'carrito' not in st.session_state: st.session_state.carrito = []

    st.sidebar.title("Menú Principal")
    opcion = st.sidebar.radio("Ir a:", ["📊 Stock y Edición", "📍 Ubicaciones", "📥 Registrar Entrada", "🛒 Punto de Venta", "📜 Historial", "💾 Descargar"])

    if st.sidebar.button("🚪 Cerrar Sesión"):
        st.session_state["autenticado"] = False
        st.rerun()

    # --- PUNTO DE VENTA CON BORRADO INDIVIDUAL ---
    if opcion == "🛒 Punto de Venta":
        st.header("🛒 Punto de Venta")
        col1, col2 = st.columns([1, 1.8])
        
        with col1:
            st.subheader("Búsqueda")
            cod = st.text_input("Escanea o escribe Clave:", key="scanner").upper()
            if cod:
                if cod in df['Clave'].values:
                    p = df[df['Clave'] == cod].iloc[0]
                    st.info(f"*{p['Nombre']}*\n\nDisponible: {p['Cantidad']}")
                    cant_pedida = st.number_input("Cantidad:", min_value=1, max_value=int(p['Cantidad']), value=1)
                    if st.button("➕ Agregar"):
                        # Se guarda como lista de diccionarios para facilitar manejo
                        st.session_state.carrito.append({'Clave': p['Clave'], 'Nombre': p['Nombre'], 'Precio': p['Precio'], 'Cant': int(cant_pedida)})
                        st.rerun()
                else: st.error("No encontrado")

        with col2:
            st.subheader("🛒 Carrito (Producto, Cantidad, Precio)")
            if st.session_state.carrito:
                # Procesar carrito para mostrar en tabla
                res = pd.DataFrame(st.session_state.carrito)
                # Agrupar por si se agregó el mismo producto varias veces
                res = res.groupby(['Clave', 'Nombre', 'Precio'])['Cant'].sum().reset_index()
                res['Subtotal'] = res['Cant'] * res['Precio']
                
                tabla_visual = res[['Nombre', 'Cant', 'Precio']].rename(columns={'Nombre': 'Producto', 'Cant': 'Cantidad'})
                tabla_visual['Precio'] = tabla_visual['Precio'].map('${:,.2f} MXN'.format)
                st.table(tabla_visual)
                
                total = res['Subtotal'].sum()
                st.markdown(f"### TOTAL: :green[${total:,.2f} MXN]")
                
                # --- NUEVA OPCIÓN: BORRAR PRODUCTO ESPECÍFICO ---
                with st.expander("🗑️ Editar Carrito (Quitar productos)"):
                    prod_eliminar = st.selectbox("Selecciona el producto a quitar:", res['Nombre'])
                    if st.button("❌ Eliminar del Carrito"):
                        # Filtrar la lista del carrito para quitar el seleccionado
                        st.session_state.carrito = [item for item in st.session_state.carrito if item['Nombre'] != prod_eliminar]
                        st.warning(f"Se quitó {prod_eliminar} del carrito.")
                        st.rerun()

                c1, c2 = st.columns(2)
                if c1.button("🧹 Vaciar Todo"):
                    st.session_state.carrito = []
                    st.rerun()
                
                if c2.button("🚀 Realizar Factura e Imprimir"):
                    fol = generar_folio_corto()
                    txt_imprimir = ""
                    for _, r in res.iterrows():
                        df.loc[df['Clave'] == r['Clave'], 'Cantidad'] -= r['Cant']
                        txt_imprimir += f"{r['Cant']}x {r['Nombre']} - ${r['Subtotal']:,.2f}<br>"
                    
                    guardar_inventario(df)
                    registrar_venta_historial(fol, txt_imprimir.replace("<br>", " | "), total)
                    
                    ticket_html = f"""
                    <div style="font-family: monospace; width: 280px; padding: 15px; border: 1px dashed #000; background: #fff; color: #000;">
                        <h2 style="text-align: center;">TVC SAN NICOLÁS</h2>
                        <hr><p><strong>FOLIO:</strong> {fol}</p>
                        <p><strong>FECHA:</strong> {datetime.now().strftime('%d/%m/%Y %H:%M')}</p><hr>
                        <div style="font-size: 13px;">{txt_imprimir}</div><hr>
                        <h3 style="text-align: right;">TOTAL: ${total:,.2f} MXN</h3>
                    </div>
                    <br><button onclick="window.print();" style="width: 100%; padding: 10px; background: #2ecc71; color: white; border: none; cursor: pointer; font-weight: bold;">🖨️ IMPRIMIR TICKET</button>
                    """
                    components.html(ticket_html, height=450)
                    st.session_state.carrito = []
            else: st.info("Carrito vacío")

    # --- HISTORIAL ---
    elif opcion == "📜 Historial":
        st.header("📜 Historial de Facturación")
        hist = cargar_historial()
        if not hist.empty:
            st.dataframe(hist.sort_values(by='Fecha', ascending=False), use_container_width=True)
            st.markdown("---")
            folio_a_borrar = st.selectbox("Selecciona Folio para eliminar del historial:", hist['Folio'].astype(str))
            if st.button("⚠️ Borrar del Historial"):
                nuevo_historial = hist[hist['Folio'].astype(str) != folio_a_borrar]
                guardar_en_historial(nuevo_historial)
                st.rerun()
        else: st.warning("No hay registros.")

    # --- OTROS MENÚS ---
    elif opcion == "📊 Stock y Edición":
        st.header("📋 Stock Actual")
        st.dataframe(df.style.format({"Precio": "${:,.2f} MXN"}), use_container_width=True)

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
                guardar_inventario(df); st.success("Guardado"); st.rerun()

    elif opcion == "💾 Descargar":
        out = BytesIO()
        with pd.ExcelWriter(out, engine='openpyxl') as w: df.to_excel(w, index=False)
        st.download_button("📥 Bajar Excel", out.getvalue(), "inventario_tvc.xlsx")
