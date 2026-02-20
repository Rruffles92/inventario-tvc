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

    def guardar_en_historial(folio, productos_texto, total):
        historial = cargar_historial()
        nueva_venta = pd.DataFrame([[datetime.now().strftime('%d/%m/%Y %H:%M:%S'), folio, productos_texto, total]], 
                                   columns=['Fecha', 'Folio', 'Productos', 'Total'])
        historial = pd.concat([historial, nueva_venta], ignore_index=True)
        historial.to_excel(HISTORIAL_FILE, index=False)

    # --- GENERADOR DE FOLIOS PERSONALIZADO ---
    def generar_folio_corto():
        tipo = random.choice([4, 6]) # Decide si será de 4 o 6 números
        if tipo == 4:
            fijo = random.randint(10, 99) # Primeros 2 fijos
            variable = random.randint(10, 99) # Últimos 2 cambian
            return f"{fijo}{variable}"
        else:
            fijo = random.randint(100, 999) # Primeros 3 fijos
            variable = random.randint(100, 999) # Últimos 3 cambian
            return f"{fijo}{variable}"

    df = cargar_inventario()
    if 'carrito' not in st.session_state: st.session_state.carrito = []

    st.sidebar.title("Menú Principal")
    opcion = st.sidebar.radio("Ir a:", ["📊 Stock y Edición", "📍 Ubicaciones", "📥 Registrar Entrada", "🛒 Punto de Venta", "📜 Historial", "💾 Descargar"])

    if st.sidebar.button("🚪 Cerrar Sesión"):
        st.session_state["autenticado"] = False
        st.rerun()

    # --- PUNTO DE VENTA ---
    if opcion == "🛒 Punto de Venta":
        st.header("🛒 Punto de Venta")
        col1, col2 = st.columns([1, 1.5])
        
        with col1:
            st.subheader("Agregar al Carrito")
            cod = st.text_input("Escanea o escribe Clave:", key="scanner").upper()
            if cod:
                if cod in df['Clave'].values:
                    p = df[df['Clave'] == cod].iloc[0]
                    st.info(f"Producto: *{p['Nombre']}* | Stock: {p['Cantidad']}")
                    cant_pedida = st.number_input("Cantidad:", min_value=1, max_value=int(p['Cantidad']), value=1)
                    if st.button("➕ Agregar"):
                        for _ in range(int(cant_pedida)):
                            st.session_state.carrito.append({'Clave': p['Clave'], 'Nombre': p['Nombre'], 'Precio': p['Precio']})
                        st.success(f"Añadido {p['Nombre']}")
                        st.rerun()
                else: st.error("No encontrado")

        with col2:
            st.subheader("Detalle de Venta")
            if st.session_state.carrito:
                res = pd.DataFrame(st.session_state.carrito).groupby(['Clave', 'Nombre', 'Precio']).size().reset_index(name='Cant')
                res['Subtotal'] = res['Cant'] * res['Precio']
                st.table(res.style.format({"Precio": "${:,.2f}", "Subtotal": "${:,.2f}"}))
                total = res['Subtotal'].sum()
                st.write(f"## TOTAL: ${total:,.2f} MXN")
                
                if st.button("🚀 Finalizar y Generar Factura"):
                    fol = generar_folio_corto()
                    txt_imprimir = ""
                    for _, r in res.iterrows():
                        df.loc[df['Clave'] == r['Clave'], 'Cantidad'] -= r['Cant']
                        txt_imprimir += f"{r['Cant']}x {r['Nombre']} - ${r['Subtotal']:,.2f}<br>"
                    
                    guardar_inventario(df)
                    guardar_en_historial(fol, txt_imprimir.replace("<br>", " | "), total)
                    
                    # HTML PARA IMPRESIÓN DIRECTA
                    ticket_html = f"""
                    <div id="ticket" style="font-family: Arial, sans-serif; width: 300px; padding: 10px; border: 1px solid #000;">
                        <h2 style="text-align: center;">TVC SAN NICOLÁS</h2>
                        <p><strong>FOLIO:</strong> {fol}</p>
                        <p><strong>FECHA:</strong> {datetime.now().strftime('%d/%m/%Y %H:%M')}</p>
                        <hr>
                        <p>{txt_imprimir}</p>
                        <hr>
                        <h3>TOTAL: ${total:,.2f} MXN</h3>
                        <p style="text-align: center;">¡Gracias por su compra!</p>
                    </div>
                    <button onclick="window.print();" style="padding: 10px; background: #2ecc71; color: white; border: none; cursor: pointer;">🖨️ IMPRIMIR AHORA</button>
                    """
                    components.html(ticket_html, height=400)
                    st.session_state.carrito = []
                    st.success(f"Venta registrada. Folio generado: {fol}")
            else: st.info("Carrito vacío")

    # --- MANTENIMIENTO DE OTROS MENÚS ---
    elif opcion == "📊 Stock y Edición":
        st.header("📋 Inventario Actual")
        st.dataframe(df.style.format({"Precio": "${:,.2f} MXN"}), use_container_width=True)
        with st.expander("📝 Editar un producto"):
            sel = st.selectbox("Clave:", df['Clave'] + " - " + df['Nombre'])
            idx = df[df['Clave'] == sel.split(" - ")[0]].index[0]
            n_nom = st.text_input("Nombre", value=df.at[idx, 'Nombre'])
            n_can = st.number_input("Cantidad", value=int(df.at[idx, 'Cantidad']))
            n_pre = st.number_input("Precio", value=float(df.at[idx, 'Precio']))
            if st.button("Guardar Cambios"):
                df.at[idx, 'Nombre'], df.at[idx, 'Cantidad'], df.at[idx, 'Precio'] = n_nom, n_can, n_pre
                guardar_inventario(df); st.success("Actualizado"); st.rerun()

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
                guardar_inventario(df); st.success("Listo")

    elif opcion == "📜 Historial":
        st.header("📜 Historial de Ventas")
        st.dataframe(cargar_historial().sort_values(by='Fecha', ascending=False), use_container_width=True)

    elif opcion == "💾 Descargar":
        out = BytesIO()
        with pd.ExcelWriter(out, engine='openpyxl') as w: df.to_excel(w, index=False)
        st.download_button("📥 Descargar Inventario Excel", out.getvalue(), "inventario_tvc.xlsx")
