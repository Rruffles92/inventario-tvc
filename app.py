import streamlit as st
import pandas as pd
import os
from io import BytesIO
from datetime import datetime
import random
import streamlit.components.v1 as components

# --- 1. SEGURIDAD ---
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

    # --- 2. FUNCIONES DE BASE DE DATOS ---
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

    def generar_folio_corto():
        tipo = random.choice([4, 6])
        if tipo == 4:
            return f"{random.randint(10, 99)}{random.randint(10, 99)}"
        else:
            return f"{random.randint(100, 999)}{random.randint(100, 999)}"

    df = cargar_inventario()
    if 'carrito' not in st.session_state: st.session_state.carrito = []

    # --- 3. BARRA LATERAL ---
    st.sidebar.title("📺 TVC Menú")
    opcion = st.sidebar.radio("Ir a:", ["📊 Stock y Edición", "📍 Ubicaciones", "📥 Registrar Entrada", "🛒 Punto de Venta", "📜 Historial", "💾 Descargar"])

    if st.sidebar.button("🚪 Cerrar Sesión"):
        st.session_state["autenticado"] = False
        st.rerun()

    # --- 4. SECCIÓN: STOCK Y EDICIÓN ---
    if opcion == "📊 Stock y Edición":
        st.header("📋 Inventario General")
        st.dataframe(df.style.format({"Precio": "${:,.2f} MXN"}), use_container_width=True)
        with st.expander("📝 Editar Producto"):
            sel = st.selectbox("Producto:", df['Clave'] + " - " + df['Nombre'])
            idx = df[df['Clave'] == sel.split(" - ")[0]].index[0]
            n_nom = st.text_input("Nombre", value=df.at[idx, 'Nombre'])
            n_can = st.number_input("Cantidad", value=int(df.at[idx, 'Cantidad']))
            n_pre = st.number_input("Precio", value=float(df.at[idx, 'Precio']))
            if st.button("Guardar Cambios"):
                df.at[idx, 'Nombre'], df.at[idx, 'Cantidad'], df.at[idx, 'Precio'] = n_nom, n_can, n_pre
                guardar_inventario(df); st.success("¡Actualizado!"); st.rerun()

    # --- 5. SECCIÓN: UBICACIONES (CORREGIDO) ---
    elif opcion == "📍 Ubicaciones":
        st.header("📍 Localización de Mercancía")
        if not df.empty:
            st.dataframe(df[['Clave', 'Nombre', 'Ubicacion']], use_container_width=True)
            with st.expander("📝 Cambiar Ubicación Manual"):
                sel_u = st.selectbox("Selecciona Producto:", df['Clave'] + " - " + df['Nombre'])
                idx_u = df[df['Clave'] == sel_u.split(" - ")[0]].index[0]
                nueva_u = st.text_input("Nueva Ubicación:", value=df.at[idx_u, 'Ubicacion'])
                if st.button("💾 Actualizar"):
                    df.at[idx_u, 'Ubicacion'] = nueva_u
                    guardar_inventario(df); st.success("Ubicación cambiada"); st.rerun()
        else: st.warning("Inventario vacío.")

    # --- 6. SECCIÓN: PUNTO DE VENTA ---
    elif opcion == "🛒 Punto de Venta":
        st.header("🛒 Venta Nueva")
        col1, col2 = st.columns([1, 1.8])
        with col1:
            cod = st.text_input("Escanea o escribe Clave:").upper()
            if cod and cod in df['Clave'].values:
                p = df[df['Clave'] == cod].iloc[0]
                st.info(f"*{p['Nombre']}*\n\nStock: {p['Cantidad']}")
                cant = st.number_input("Cantidad:", min_value=1, max_value=int(p['Cantidad']), value=1)
                if st.button("➕ Agregar"):
                    encontrado = False
                    for i in st.session_state.carrito:
                        if i['Clave'] == p['Clave']: i['Cant'] += int(cant); encontrado = True; break
                    if not encontrado:
                        st.session_state.carrito.append({'Clave': p['Clave'], 'Nombre': p['Nombre'], 'Precio': p['Precio'], 'Cant': int(cant)})
                    st.rerun()
        
        with col2:
            if st.session_state.carrito:
                res = pd.DataFrame(st.session_state.carrito)
                res['Subtotal'] = res['Cant'] * res['Precio']
                st.table(res[['Nombre', 'Cant', 'Precio']].rename(columns={'Nombre': 'Producto', 'Cant': 'Cantidad'}))
                total = res['Subtotal'].sum()
                st.markdown(f"### TOTAL: :green[${total:,.2f} MXN]")
                
                with st.expander("🛠️ Corregir Carrito"):
                    prod_sel = st.selectbox("Producto a editar:", res['Nombre'])
                    item_edit = next(i for i in st.session_state.carrito if i['Nombre'] == prod_sel)
                    n_cant = st.number_input("Nueva Cantidad:", min_value=0, value=item_edit['Cant'])
                    if st.button("✅ Actualizar"):
                        if n_cant == 0: st.session_state.carrito = [i for i in st.session_state.carrito if i['Nombre'] != prod_sel]
                        else: item_edit['Cant'] = int(n_cant)
                        st.rerun()

                if st.button("🚀 Finalizar Factura e Imprimir"):
                    fol = generar_folio_corto()
                    txt = ""
                    for i in st.session_state.carrito:
                        df.loc[df['Clave'] == i['Clave'], 'Cantidad'] -= i['Cant']
                        txt += f"{i['Cant']}x {i['Nombre']} - ${i['Cant']*i['Precio']:,.2f}<br>"
                    guardar_inventario(df)
                    hist = cargar_historial()
                    hist = pd.concat([hist, pd.DataFrame([[datetime.now().strftime('%d/%m/%Y %H:%M'), fol, txt.replace("<br>", " | "), total]], columns=hist.columns)], ignore_index=True)
                    guardar_en_historial(hist)
                    ticket = f"""<div style="font-family:monospace; width:280px; padding:10px; border:1px dashed #000;">
                    <h2 style="text-align:center;">TVC SAN NICOLÁS</h2><hr><p>FOLIO: {fol}</p><p>{txt}</p><hr><h3>TOTAL: ${total:,.2f}</h3></div>
                    <button onclick="window.print();" style="width:100%; padding:10px; background:#2ecc71; color:white; border:none; cursor:pointer;">IMPRIMIR</button>"""
                    components.html(ticket, height=400)
                    st.session_state.carrito = []
            else: st.info("Carrito vacío")

    # --- 7. REGISTRAR ENTRADA ---
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
                guardar_inventario(df); st.success("Guardado exitoso"); st.rerun()

    # --- 8. HISTORIAL ---
    elif opcion == "📜 Historial":
        st.header("📜 Ventas Pasadas")
        h = cargar_historial()
        if not h.empty:
            st.dataframe(h.sort_values(by='Fecha', ascending=False), use_container_width=True)
            f_borrar = st.selectbox("Borrar Factura:", h['Folio'].astype(str))
            if st.button("⚠️ Eliminar Registro"):
                h = h[h['Folio'].astype(str) != f_borrar]
                guardar_en_historial(h); st.rerun()
        else: st.info("Sin registros.")

    # --- 9. DESCARGAR ---
    elif opcion == "💾 Descargar":
        out = BytesIO()
        with pd.ExcelWriter(out, engine='openpyxl') as w: df.to_excel(w, index=False)
        st.download_button("📥 Descargar Excel", out.getvalue(), "inventario_tvc.xlsx")
