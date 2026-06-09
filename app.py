
import streamlit as st
import mysql.connector
from datetime import datetime
import os

# --- CONFIGURACIÓN DE LA INTERFAZ WEB ---
st.set_page_config(
    page_title="Quiz de Ortografía y Gramática",
    page_icon="✍️",
    layout="centered"
)

# Estilos personalizados para los botones
st.markdown("""
    <style>
    .stButton>button {
        width: 100%;
        border-radius: 8px;
        padding: 10px;
    }
    </style>
""", unsafe_allow_html=True)

# --- CONEXIÓN DE BASE DE DATOS (MÉTODO SEGURO PARA RAILWAY) ---
def conectar_db():
    try:
        return mysql.connector.connect(
            host=os.getenv("MYSQLHOST", "localhost"),
            user=os.getenv("MYSQLUSER", "root"),
            password=os.getenv("MYSQLPASSWORD", ""),
            database=os.getenv("MYSQLDATABASE", "tu_base_datos"),
            port=int(os.getenv("MYSQLPORT", 3306))
        )
    except Exception as e:
        st.error(f"Error crítico al conectar a la base de datos MySQL: {e}")
        return None

def obtener_pregunta():
    conexion = conectar_db()
    if not conexion:
        return None
    cursor = conexion.cursor(dictionary=True)
    # Busca preguntas no olvidadas y prioriza las que tienen menos aciertos
    query = "SELECT * FROM banco_preguntas WHERE olvida = 0 ORDER BY nOK ASC, id ASC LIMIT 1"
    cursor.execute(query)
    resultado = cursor.fetchone()
    cursor.close()
    conexion.close()
    return resultado

def registrar_respuesta(pregunta_id, fue_correcta):
    conexion = conectar_db()
    if not conexion:
        return
    cursor = conexion.cursor()
    fecha_actual = datetime.now().strftime('%Y-%m-%d')
    
    if fue_correcta:
        query = "UPDATE banco_preguntas SET nOK = nOK + 1, cuando = %s WHERE id = %s"
    else:
        query = "UPDATE banco_preguntas SET nKO = nKO + 1, cuando = %s WHERE id = %s"
        
    cursor.execute(query, (fecha_actual, pregunta_id))
    conexion.commit()
    cursor.close()
    conexion.close()

# --- LÓGICA DE ESTADO DE LA SESIÓN WEB ---
if "pregunta_actual" not in st.session_state:
    st.session_state.pregunta_actual = obtener_pregunta()
if "feedback" not in st.session_state:
    st.session_state.feedback = None

# --- INTERFAZ DE USUARIO ---
st.title("✍️ Quiz de Ortografía y Gramática")
st.write("Pon a prueba tus conocimientos. Las preguntas falladas aparecerán más seguido.")
st.divider()

preg = st.session_state.pregunta_actual

if preg:
    st.subheader(f"Pregunta {preg['id']}")
    st.markdown(f"#### {preg['pregunta']}")
    
    # Opciones de respuesta formateadas visualmente
    opciones_visuales = [
        f"A) {preg['opcion_a']}",
        f"B) {preg['opcion_b']}",
        f"C) {preg['opcion_c']}",
        f"D) {preg['opcion_d']}"
    ]
    
    # Selector de radio tipo web nativo moderno
    seleccion = st.radio("Selecciona tu respuesta:", opciones_visuales, index=None, key="radio_quiz")
    
    col1, col2 = st.columns([1, 4])
    
    with col1:
        if st.button("Validar", type="primary"):
            if not seleccion:
                st.warning("⚠️ Selecciona una opción antes de validar.")
            else:
                letra_elegida = seleccion[0] # Extrae 'A', 'B', 'C' o 'D'
                
                if letra_elegida == preg['correcta']:
                    registrar_respuesta(preg['id'], fue_correcta=True)
                    st.session_state.feedback = {"tipo": "ok", "mensaje": f"🎉 ¡Excelente! La respuesta correcta es la ({preg['correcta']}). Progreso guardado."}
                else:
                    registrar_respuesta(preg['id'], fue_correcta=False)
                    st.session_state.feedback = {"tipo": "ko", "mensaje": f"❌ Incorrecto. ¡Sigue practicando! Tu fallo ha sido anotado."}
                    
    with col2:
        if st.session_state.feedback:
            if st.button("Siguiente Pregunta ➡️"):
                st.session_state.pregunta_actual = obtener_pregunta()
                st.session_state.feedback = None
                st.rerun()

    # Mostrar Pop-ups (Toasts/Alertas) de la interfaz basados en la validación
    if st.session_state.feedback:
        if st.session_state.feedback["tipo"] == "ok":
            st.success(st.session_state.feedback["mensaje"])
            st.toast("¡Punto positivo anotado en nOK!", icon="✨")
        else:
            st.error(st.session_state.feedback["mensaje"])
            st.toast("Anotado en nKO. ¡A por la próxima!", icon="⚠️")

else:
    st.balloons()
    st.success("🎉 ¡Felicidades! Has respondido correctamente a todas las preguntas de la base de datos.")
    if st.button("Volver a escanear base de datos"):
        st.session_state.pregunta_actual = obtener_pregunta()
        st.rerun()