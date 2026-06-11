import streamlit as st
import json
from datetime import datetime
import os
import re

st.set_page_config(
    page_title="Quiz de Ortografia y Gramatica",
    page_icon=":pencil2:",
    layout="centered",
)

st.markdown(
    """
    <style>
    .stButton>button {
        width: 100%;
        border-radius: 8px;
        padding: 10px;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

DATA_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "datos.json")


def _fix_mojibake(obj):
    """Arregla mojibake en memoria (latin-1 -> utf-8 re-decodificación). No toca el fichero."""
    if isinstance(obj, dict):
        return {k: _fix_mojibake(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_fix_mojibake(v) for v in obj]
    if isinstance(obj, str):
        try:
            # Si el texto es mojibake (UTF-8 leído como latin-1), recupéralo
            cand = obj.encode("latin-1").decode("utf-8")
            return cand
        except (UnicodeEncodeError, UnicodeDecodeError):
            return obj
    return obj


def load_data():
    # Leer en binario para no depender de la codificación del fichero
    try:
        raw = open(DATA_FILE, "rb").read()
    except Exception as e:
        st.error(f"No se pudo leer {DATA_FILE}: {e}")
        return []

    # Intentar decodificar con las codificaciones más comunes
    text = None
    for enc in ("utf-8", "cp1252", "latin-1"):
        try:
            text = raw.decode(enc)
            break
        except UnicodeDecodeError:
            continue

    if text is None:
        # Último recurso: decodificar con reemplazos
        text = raw.decode("utf-8", errors="replace")

    try:
        data = json.loads(text)
    except json.JSONDecodeError as e:
        st.error(f"JSON inválido en {DATA_FILE}: {e}")
        return []

    # Normalizar mojibake en memoria sin modificar el fichero
    return _fix_mojibake(data)


def save_data(data):
    # Escribe siempre en UTF-8; los contadores y fechas son ASCII, no afecta a los textos
    try:
        text = json.dumps(data, indent=2, ensure_ascii=False)
        open(DATA_FILE, "w", encoding="utf-8").write(text)
    except Exception as e:
        st.error(f"No se pudo guardar {DATA_FILE}: {e}")


def _extract_correct_letter(item):
    for letra in ["A", "B", "C", "D"]:
        val = item.get(letra, "")
        if isinstance(val, str) and "Correcta" in val:
            return letra
    return None


def _option_display_text(item, letra):
    val = item.get(letra, "")
    if not isinstance(val, str):
        return ""
    m = re.search(r"['\"]([^'\"]+)['\"]", val)
    if m:
        return m.group(1)
    if ":" in val:
        return val.split(":", 1)[1].strip().split(".")[0]
    return val.split(".")[0][:60]


def _parse_opciones_field(opciones_str):
    """Parsea la cadena 'opciones' del JSON en un dict {'A': texto, 'B': texto, ...}."""
    res = {"A": "", "B": "", "C": "", "D": ""}
    if not opciones_str or not isinstance(opciones_str, str):
        return res
    # Buscar patrones 'A) texto B) texto C) texto D) texto'
    pattern = re.compile(r"([A-D])\)\s*([^A-D]+?)(?=(?:\s+[A-D]\))|$)", re.S)
    for m in pattern.finditer(opciones_str):
        letra = m.group(1)
        texto = m.group(2).strip()
        res[letra] = texto
    return res


def obtener_pregunta():
    data = load_data()
    if not data:
        return None
    candidates = [(i, p) for i, p in enumerate(data) if int(p.get("olvidar", 0)) == 0]
    if not candidates:
        return None
    candidates.sort(key=lambda t: int(t[1].get("contador_OK", 0)))
    idx, item = candidates[0]
    correcta = _extract_correct_letter(item)
    opciones_map = _parse_opciones_field(item.get("opciones", ""))
    return {
        "id": idx,
        "pregunta": item.get("pregunta", ""),
        "opcion_a": opciones_map.get("A", _option_display_text(item, "A")),
        "opcion_b": opciones_map.get("B", _option_display_text(item, "B")),
        "opcion_c": opciones_map.get("C", _option_display_text(item, "C")),
        "opcion_d": opciones_map.get("D", _option_display_text(item, "D")),
        "raw_A": item.get("A", ""),
        "raw_B": item.get("B", ""),
        "raw_C": item.get("C", ""),
        "raw_D": item.get("D", ""),
        "correcta": correcta,
        "nOK": int(item.get("contador_OK", 0)),
        "nKO": int(item.get("contador_KO", 0)),
        "olvida": int(item.get("olvidar", 0)),
    }


def registrar_respuesta(pregunta_id, fue_correcta):
    data = load_data()
    if pregunta_id < 0 or pregunta_id >= len(data):
        return
    key = "contador_OK" if fue_correcta else "contador_KO"
    data[pregunta_id][key] = int(data[pregunta_id].get(key, 0)) + 1
    data[pregunta_id]["cuando"] = datetime.now().strftime("%Y-%m-%d")
    save_data(data)


if "pregunta_actual" not in st.session_state or st.session_state.get("pregunta_actual") is None:
    st.session_state.pregunta_actual = obtener_pregunta()
if "feedback" not in st.session_state or st.session_state.get("feedback") is None:
    st.session_state.feedback = None

st.title("Quiz de Ortografia y Gramatica")
st.write("Las preguntas falladas apareceran mas seguido.")
st.divider()

preg = st.session_state.pregunta_actual

if preg:
    st.subheader(f"Pregunta {preg['id'] + 1}")
    # Mostrar ID real y contadores
    st.caption(f"ID: {preg['id']}  •  OK: {preg.get('nOK',0)}  •  KO: {preg.get('nKO',0)}")
    st.markdown(f"#### {preg['pregunta']}")

    opciones_visuales = [
        f"A) {preg['opcion_a']}",
        f"B) {preg['opcion_b']}",
        f"C) {preg['opcion_c']}",
        f"D) {preg['opcion_d']}",
    ]

    seleccion = st.radio("Selecciona tu respuesta:", opciones_visuales, index=None, key="radio_quiz")

    col1, col2 = st.columns([1, 4])

    with col1:
        if st.button("Validar", type="primary"):
            if not seleccion:
                st.warning("Selecciona una opcion antes de validar.")
            else:
                letra_elegida = seleccion[0]
                if letra_elegida == preg["correcta"]:
                    # Registrar una sola vez
                    registrar_respuesta(preg["id"], fue_correcta=True)
                    # explicación seleccionada y explicación correcta
                    sel_exp = preg.get(f"raw_{letra_elegida}", "") if isinstance(letra_elegida, str) else ""
                    corr_exp = preg.get(f"raw_{preg['correcta']}", "") if preg.get('correcta') else ""
                    # actualizar contadores en memoria desde el fichero
                    data_after = load_data()
                    if 0 <= preg["id"] < len(data_after):
                        item_after = data_after[preg["id"]]
                        preg["nOK"] = int(item_after.get("contador_OK", 0))
                        preg["nKO"] = int(item_after.get("contador_KO", 0))
                    st.session_state.feedback = {
                        "tipo": "ok",
                        "mensaje": f"¡Excelente! La respuesta correcta es la ({preg['correcta']}). Progreso guardado.",
                        "seleccion_letra": letra_elegida,
                        "seleccion_exp": sel_exp,
                        "correcta_exp": corr_exp,
                    }
                else:
                    # Registrar una sola vez
                    registrar_respuesta(preg["id"], fue_correcta=False)
                    sel_exp = preg.get(f"raw_{letra_elegida}", "") if isinstance(letra_elegida, str) else ""
                    corr_exp = preg.get(f"raw_{preg['correcta']}", "") if preg.get('correcta') else ""
                    data_after = load_data()
                    if 0 <= preg["id"] < len(data_after):
                        item_after = data_after[preg["id"]]
                        preg["nOK"] = int(item_after.get("contador_OK", 0))
                        preg["nKO"] = int(item_after.get("contador_KO", 0))
                    st.session_state.feedback = {
                        "tipo": "ko",
                        "mensaje": "Incorrecto. ¡Sigue practicando! Tu fallo ha sido anotado.",
                        "seleccion_letra": letra_elegida,
                        "seleccion_exp": sel_exp,
                        "correcta_exp": corr_exp,
                    }

    with col2:
        if st.session_state.feedback:
            if st.button("Siguiente Pregunta"):
                st.session_state.pregunta_actual = obtener_pregunta()
                st.session_state.feedback = None
                st.rerun()

    if st.session_state.feedback:
        if st.session_state.feedback["tipo"] == "ok":
            st.success(st.session_state.feedback["mensaje"])
            try:
                st.toast("¡Punto positivo anotado en nOK!", icon="✨")
            except Exception:
                pass
        else:
            st.error(st.session_state.feedback["mensaje"])
            try:
                st.toast("Anotado en nKO. ¡A por la próxima!", icon="❌")
            except Exception:
                pass

        # Mostrar explicaciones por opción desde el JSON, marcando seleccionada y correcta
        opciones_raw = [
            ("A", preg.get("raw_A", "")),
            ("B", preg.get("raw_B", "")),
            ("C", preg.get("raw_C", "")),
            ("D", preg.get("raw_D", "")),
        ]
        sel_letra = st.session_state.feedback.get("seleccion_letra")
        correcta_letra = preg.get("correcta")
        st.markdown("**Explicaciones por opción:**")
        for letra, raw in opciones_raw:
            tags = []
            if letra == correcta_letra:
                tags.append("Correcta")
            if sel_letra == letra:
                tags.append("Seleccionada")
            tag_text = f" ({', '.join(tags)})" if tags else ""
            st.markdown(f"**{letra}){tag_text}**")
            if raw:
                st.write(raw)
            else:
                st.write("_Sin explicación en el JSON_")
