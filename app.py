import streamlit as st
import pandas as pd
import os

# --- SEGURIDAD ---
def verificar_password():
    if "autenticado" not in st.session_state:
        st.session_state["autenticado"] = False
    
    if not st.session_state["autenticado"]:
        st.title("🔐 Acceso TVC San Nicolás")
        st.write("Por favor, introduce la clave para gestionar el inventario.")
        
        password = st.text_input("Contraseña:", type="password")
        
        if st.button("Entrar al Sistema"):
            if password == "TVCsanicolas":
                st.session_state["autenticado"] = True
                st.rerun()
            else:
                st.error("❌ Clave incorrecta. Acceso denegado.")
        return False
    return True

# --- PROGRAMA PRINCIPAL ---
if verificar_password():
    st.set_page_config(page_title="TVC Inventario", layout="wide")
    
    # Nombre del archivo para guardar datos
    FILE_NAME = 'datos_inventario_tvc.xlsx'

    def cargar_datos():
        if os.path.exists(FILE_NAME):
            return pd.read_excel(FILE_NAME)
        return pd.DataFrame(columns=['Clave', 'Nombre', 'Cantidad', 'Precio'])

    def guardar_datos(df):
        df.to_excel(FILE_NAME, index=False)

    df = cargar_datos()

    st.sidebar.title("Menú TVC")
    menu = st.sidebar.radio("Selecciona una opción:", ["📋 Ver Stock", "📥 Registrar Entrada", "🛒 Registrar Venta"])

    if st.sidebar.button("Cerrar Sesión"):
        st.session_state["autenticado"] = False
        st.rerun()

    if menu == "📋 Ver Stock":
        st.header("Inventario Actual")
        st.dataframe(df, use_container_width=True)

    elif menu == "📥 Registrar Entrada":
        st.header("Cargar Nueva Mercancía")
        with st.form("registro"):
            c1, c2 = st.columns(2)
            cl = c1.text_input("Clave/Código").upper()
            no = c1.text_input("Nombre del Producto")
            ca = c2.number_input("Cantidad de Cajas", min_value=1)
            pr = c2.number_input("Precio de Venta", min_value=0.0)
            if st.form_submit_button("Guardar en Almacén"):
                if cl in df['Clave'].values:
                    df.loc[df['Clave'] == cl, 'Cantidad'] += ca
                else:
                    nuevo = pd.DataFrame([[cl, no, ca, pr]], columns=df.columns)
                    df = pd.concat([df, nuevo], ignore_index=True)
                guardar_datos(df)
                st.success("¡Inventario actualizado correctamente!")

    elif menu == "🛒 Registrar Venta":
        st.header("Salida de Productos")
        cl_v = st.text_input("Escanear o escribir Clave:").upper()
        cant_v = st.number_input("Cantidad a vender:", min_value=1, value=1)
        if st.button("Confirmar Venta"):
            if cl_v in df['Clave'].values:
                idx = df[df['Clave'] == cl_v].index[0]
                if df.at[idx, 'Cantidad'] >= cant_v:
                    df.at[idx, 'Cantidad'] -= cant_v
                    guardar_datos(df)
                    st.success(f"Venta registrada: {df.at[idx, 'Nombre']}")
                else:
                    st.error("No hay stock suficiente.")
            else:
                st.error("Esa clave no está registrada.")
