import streamlit as st
import pandas as pd
import os

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
    st.set_page_config(page_title="TVC Inventario Pro", layout="wide")
    FILE_NAME = 'inventario_tvc_ubicaciones.xlsx'

    def cargar():
        if os.path.exists(FILE_NAME): return pd.read_excel(FILE_NAME)
        # Agregamos la columna 'Ubicacion'
        return pd.DataFrame(columns=['Clave', 'Nombre', 'Cantidad', 'Ubicacion', 'Precio'])

    def guardar(df):
        df.to_excel(FILE_NAME, index=False)
        return df

    df = cargar()
    st.sidebar.title("Menú TVC")
    opcion = st.sidebar.radio("Ir a:", ["📊 Ver Stock y Ubicaciones", "📥 Registrar Entrada", "📤 Registrar Salida"])

    if st.sidebar.button("Cerrar Sesión"):
        st.session_state["autenticado"] = False
        st.rerun()

    # --- VISTA DE STOCK ---
    if opcion == "📊 Ver Stock y Ubicaciones":
        st.header("📋 Inventario Actual con Ubicaciones")
        if df.empty:
            st.warning("El inventario está vacío.")
        else:
            st.dataframe(df, use_container_width=True)

    # --- ENTRADA CON UBICACIÓN ---
    elif opcion == "📥 Registrar Entrada":
        st.header("📥 Cargar Mercancía al Estante")
        with st.form("entrada_pro"):
            col1, col2 = st.columns(2)
            cl = col1.text_input("Clave").upper()
            no = col1.text_input("Nombre del Producto")
            cj = col2.number_input("Cantidad", min_value=1)
            ub = col2.text_input("Ubicación (Ej: Pasillo A-4, Estante 2)")
            pr = col2.number_input("Precio", min_value=0.0)
            
            if st.form_submit_button("Guardar en Inventario"):
                if cl in df['Clave'].values:
                    idx = df[df['Clave'] == cl].index[0]
                    df.at[idx, 'Cantidad'] += cj
                    df.at[idx, 'Ubicacion'] = ub # Actualiza la ubicación si cambia
                else:
                    nuevo = pd.DataFrame([[cl, no, cj, ub, pr]], columns=df.columns)
                    df = pd.concat([df, nuevo], ignore_index=True)
                guardar(df)
                st.success(f"✅ Registrado en: {ub}")

    # --- SALIDA CON INFORMACIÓN DE UBICACIÓN ---
    elif opcion == "📤 Registrar Salida":
        st.header("📤 Retirar Producto")
        cl_v = st.text_input("Escribe la Clave del producto:").upper()
        
        if cl_v:
            if cl_v in df['Clave'].values:
                producto = df[df['Clave'] == cl_v].iloc[0]
                st.info(f"📍 *Ubicación actual:* {producto['Ubicacion']} | *Stock:* {producto['Cantidad']}")
                
                cant_v = st.number_input("¿Cuántas unidades retirar?", min_value=1, max_value=int(producto['Cantidad']))
                
                if st.button("Confirmar Retiro"):
                    idx = df[df['Clave'] == cl_v].index[0]
                    df.at[idx, 'Cantidad'] -= cant_v
                    guardar(df)
                    st.success(f"✅ Retirado de {producto['Ubicacion']}. Quedan {df.at[idx, 'Cantidad']} unidades.")
                    st.rerun()
            else:
                st.error("❌ Esa clave no existe en el inventario.")
