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

    def cargar():
        if os.path.exists(FILE_NAME): return pd.read_excel(FILE_NAME)
        return pd.DataFrame(columns=['Clave', 'Nombre', 'Cantidad', 'Ubicacion', 'Precio'])

    def guardar(df):
        df.to_excel(FILE_NAME, index=False)
        return df

    df = cargar()

    if 'carrito' not in st.session_state:
        st.session_state.carrito = []

    st.sidebar.title("Menú Principal")
    opcion = st.sidebar.radio("Ir a:", [
        "📊 Ver Stock", 
        "📍 Ubicaciones", 
        "📥 Registrar Entrada", 
        "🛒 Punto de Venta (Escáner/Manual)",
        "💾 Descargar Inventario"
    ])

    if st.sidebar.button("Cerrar Sesión"):
        st.session_state["autenticado"] = False
        st.rerun()

    # --- PUNTO DE VENTA (ESCÁNER Y MANUAL) ---
    if opcion == "🛒 Punto de Venta (Escáner/Manual)":
        st.header("🛒 Punto de Venta")
        
        folio = st.text_input("🔢 Número de Folio:", value=datetime.now().strftime("%Y%m%d%H%M"))
        
        col_scan, col_cart = st.columns([1, 2])
        
        with col_scan:
            st.subheader("Entrada de Producto")
            # Este cuadro sirve para el Escáner O para escribir manualmente y dar Enter
            codigo_input = st.text_input("Escanear o Escribir Clave Manual:", key="scanner_input").upper()
            
            if codigo_input:
                if codigo_input in df['Clave'].values:
                    prod = df[df['Clave'] == codigo_input].iloc[0]
                    # Verificar si hay stock antes de agregar
                    if prod['Cantidad'] > 0:
                        st.session_state.carrito.append({
                            'Clave': prod['Clave'],
                            'Nombre': prod['Nombre'],
                            'Precio': prod['Precio']
                        })
                        st.success(f"✅ Añadido: {prod['Nombre']}")
                    else:
                        st.error("❌ Sin stock disponible")
                else:
                    st.error("❌ Código no encontrado")

        with col_cart:
            st.subheader("Lista de Venta / Folio: " + folio)
            if st.session_state.carrito:
                df_carrito = pd.DataFrame(st.session_state.carrito)
                resumen = df_carrito.groupby(['Clave', 'Nombre', 'Precio']).size().reset_index(name='Cant')
                resumen['Subtotal'] = resumen['Cant'] * resumen['Precio']
                st.table(resumen)
                
                total_venta = resumen['Subtotal'].sum()
                st.write(f"## TOTAL A COBRAR: ${total_venta:,.2f}")
                
                c1, c2 = st.columns(2)
                if c1.button("❌ Vaciar Carrito"):
                    st.session_state.carrito = []
                    st.rerun()
                
                if c2.button("🚀 Finalizar e Imprimir Ticket"):
                    # Descontar del inventario
                    for _, row in resumen.iterrows():
                        idx = df[df['Clave'] == row['Clave']].index[0]
                        df.at[idx, 'Cantidad'] -= row['Cant']
                    
                    guardar(df)
                    
                    # Formato de Ticket
                    ticket = f"--- TVC SAN NICOLÁS ---\n"
                    ticket += f"FOLIO: {folio}\n"
                    ticket += f"FECHA: {datetime.now().strftime('%d/%m/%Y %H:%M')}\n"
                    ticket += "------------------------\n"
                    for _, r in resumen.iterrows():
                        ticket += f"{r['Nombre']}\n"
                        ticket += f"{r['Cant']} x ${r['Precio']:,.2f} = ${r['Subtotal']:,.2f}\n"
                    ticket += "------------------------\n"
                    ticket += f"TOTAL: ${total_venta:,.2f}\n"
                    ticket += "------------------------\n"
                    ticket += "¡Gracias por su compra!"
                    
                    st.text_area("📋 TICKET GENERADO (Listo para imprimir):", ticket, height=350)
                    st.success("Venta finalizada con éxito.")
                    st.session_state.carrito = [] 
            else:
                st.info("El carrito está vacío. Escanee o escriba un código.")

    # --- OTRAS SECCIONES (STOCK, UBICACIONES, ENTRADA) ---
    elif opcion == "📊 Ver Stock":
        st.header("📋 Stock Actual")
        st.dataframe(df[['Clave', 'Nombre', 'Cantidad', 'Precio']], use_container_width=True)

    elif opcion == "📍 Ubicaciones":
        st.header("📍 Ubicaciones en Almacén")
        st.dataframe(df[['Clave', 'Nombre', 'Ubicacion']], use_container_width=True)

    elif opcion == "📥 Registrar Entrada":
        st.header("📥 Entrada de Mercancía")
        with st.form("entrada"):
            c1, c2 = st.columns(2)
            cl = c1.text_input("Clave").upper()
            no = c1.text_input("Nombre")
            cj = c2.number_input("Cantidad", min_value=1)
            ub = c2.text_input("Ubicación")
            pr = c2.number_input("Precio Unitario", min_value=0.0)
            if st.form_submit_button("Guardar en Inventario"):
                if cl in df['Clave'].values:
                    idx = df[df['Clave'] == cl].index[0]
                    df.at[idx, 'Cantidad'] += cj
                    if ub: df.at[idx, 'Ubicacion'] = ub
                else:
                    nuevo = pd.DataFrame([[cl, no, cj, ub, pr]], columns=df.columns)
                    df = pd.concat([df, nuevo], ignore_index=True)
                guardar(df)
                st.success("✅ Inventario actualizado")

    elif opcion == "💾 Descargar Inventario":
        st.header("💾 Exportar a Excel")
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False)
        st.download_button("📥 Descargar Archivo Excel", output.getvalue(), "inventario_tvc.xlsx")
