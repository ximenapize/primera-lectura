# app.py — Primera Lectura
# Tablero para monitorear los proyectos de ley del Congreso del Perú: filtros por temática, bancada y estado,
# y la "primera lectura" de la IA (semáforo de riesgo frente a derechos humanos y gobernanza).
# Uso: uv run streamlit run app/app.py
import io
import json
from datetime import date, timedelta
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

RAIZ = Path(__file__).resolve().parents[1]
DATA = RAIZ / "data"

COLOR_SEMAFORO = {"rojo": "#C62828", "amarillo": "#F9A825", "verde": "#2E7D32", "sin leer": "#9E9E9E"}
ICONO = {"rojo": "🔴", "amarillo": "🟡", "verde": "🟢", "sin leer": "⚪"}

st.set_page_config(page_title="Primera Lectura", page_icon="📜", layout="wide")


# ===================== Datos =====================
@st.cache_data
def cargar():
    props = pd.read_csv(DATA / "proposiciones.csv", dtype=str).fillna("")
    temas = pd.read_csv(DATA / "temas.csv", dtype=str).fillna("")
    df = props.merge(temas[["camara", "pl_id", "tema", "temas_secundarios"]], on=["camara", "pl_id"], how="left")

    riesgo = pd.DataFrame()
    if (DATA / "riesgo.jsonl").exists():
        riesgo = pd.DataFrame([json.loads(l) for l in (DATA / "riesgo.jsonl").read_text().splitlines() if l])
    if len(riesgo):
        riesgo = riesgo.drop_duplicates(["camara", "pl_id"], keep="last").drop(columns=["modelo"], errors="ignore")
        df = df.merge(riesgo, on=["camara", "pl_id"], how="left")
    for col in ["semaforo", "resumen", "explicacion", "cita_textual"]:
        if col not in df:
            df[col] = None
    df["semaforo"] = df["semaforo"].fillna("sin leer")
    df["fecha_presentacion"] = pd.to_datetime(df["fecha_presentacion"], errors="coerce")
    df["grupo_parlamentario"] = df["grupo_parlamentario"].replace("", "Sin bancada (Ejecutivo, instituciones, otros)")
    df["estado"] = df["ultimo_estado"].map(simplificar_estado)

    movs = pd.read_csv(DATA / "movimientos.csv", dtype=str).fillna("")
    return df, movs


def simplificar_estado(e: str) -> str:
    e = e.upper()
    if "PUBLICADA" in e or "AUTÓGRAFA" in e or "APROBADO" in e:
        return "5. Aprobado / publicado"
    if "AGENDA" in e:
        return "4. En agenda del Pleno"
    if "DICTAMEN" in e:
        return "3. Con dictamen"
    if "COMISIÓN" in e or "REMITIDA" in e:
        return "2. En comisión"
    if "ARCHIV" in e or "RETIRADO" in e:
        return "0. Archivado / retirado"
    return "1. Presentado"


df, movs = cargar()

# ===================== Encabezado =====================
st.title("📜 Primera Lectura")
st.caption("Cada proyecto de ley del Congreso, leído por IA el día que se presenta. "
           f"Diputados y Senado · periodo 2026-2031 · {len(df)} proposiciones · "
           f"datos al {df.fecha_presentacion.max():%d/%m/%Y}")

# ===================== Filtros =====================
with st.sidebar:
    st.header("Filtros")
    buscar = st.text_input("Buscar en título o sumilla", placeholder="minería, protesta, ONG…")
    temas_sel = st.multiselect("Temática", sorted(df.tema.dropna().unique()))
    bancadas_sel = st.multiselect("Bancada", sorted(df.grupo_parlamentario.unique()))
    estados_sel = st.multiselect("Avance", sorted(df.estado.unique(), reverse=True))
    semaforo_sel = st.multiselect("Semáforo de la IA", ["rojo", "amarillo", "verde", "sin leer"],
                                  format_func=lambda s: f"{ICONO[s]} {s}")
    camara_sel = st.multiselect("Cámara", ["diputados", "senado"])
    desde = st.date_input("Presentados desde", value=df.fecha_presentacion.min().date())

f = df[df.fecha_presentacion.dt.date >= desde]
if buscar:
    f = f[(f.titulo + " " + f.sumilla).str.contains(buscar, case=False, na=False)]
for col, sel in [("tema", temas_sel), ("grupo_parlamentario", bancadas_sel), ("estado", estados_sel),
                 ("semaforo", semaforo_sel), ("camara", camara_sel)]:
    if sel:
        f = f[f[col].isin(sel)]

# ===================== Indicadores =====================
hace_7 = pd.Timestamp(date.today() - timedelta(days=7))
c = st.columns(5)
c[0].metric("Proyectos", len(f))
c[1].metric("Nuevos (7 días)", int((f.fecha_presentacion >= hace_7).sum()))
c[2].metric("🔴 Alerta roja", int((f.semaforo == "rojo").sum()))
c[3].metric("🟡 Atención", int((f.semaforo == "amarillo").sum()))
c[4].metric("Con dictamen o en Pleno", int(f.estado.str.startswith(("3", "4")).sum()))

tab_lista, tab_panorama = st.tabs(["📋 Proyectos", "📊 Panorama"])

# ===================== Lista y ficha =====================
with tab_lista:
    orden = f.assign(_r=f.semaforo.map({"rojo": 0, "amarillo": 1, "verde": 2, "sin leer": 3})) \
             .sort_values(["_r", "fecha_presentacion"], ascending=[True, False])
    tabla = orden.assign(IA=orden.semaforo.map(ICONO), Fecha=orden.fecha_presentacion.dt.strftime("%d/%m/%Y"))[
        ["IA", "pl_id", "Fecha", "titulo", "tema", "grupo_parlamentario", "estado"]
    ].rename(columns={"pl_id": "Código", "titulo": "Título", "tema": "Temática",
                      "grupo_parlamentario": "Bancada", "estado": "Avance"})
    st.caption("Haz clic en una fila para abrir la ficha del proyecto.")
    evento = st.dataframe(tabla, hide_index=True, width="stretch", height=380,
                          on_select="rerun", selection_mode="single-row",
                          column_config={"Título": st.column_config.TextColumn(width="large")})

    xls = io.BytesIO()
    orden.drop(columns=["_r"]).to_excel(xls, index=False)
    st.download_button("⬇️ Descargar en Excel", xls.getvalue(), "primera_lectura.xlsx")

    filas = evento.selection.rows
    if filas:
        p = orden.iloc[filas[0]]
        st.divider()
        st.subheader(f"{ICONO[p.semaforo]} {p.pl_id} · {p.camara.title()}")
        st.markdown(f"**{p.titulo}**")
        izq, der = st.columns([3, 2])
        with izq:
            if p.semaforo != "sin leer":
                st.markdown("#### Primera lectura de la IA")
                st.markdown(f"**En una frase:** {p.resumen}")
                color = COLOR_SEMAFORO[p.semaforo]
                st.markdown(f"<div style='border-left:6px solid {color};padding:.6rem 1rem;background:{color}14'>"
                            f"<b>Semáforo: {p.semaforo.upper()}</b><br>{p.explicacion}</div>", unsafe_allow_html=True)
                if isinstance(p.get("derechos"), list) and p.derechos:
                    st.markdown("**Derechos en juego:** " + " · ".join(p.derechos))
                if isinstance(p.get("estandares"), list) and p.estandares:
                    st.markdown("**Estándares:** " + " · ".join(p.estandares))
                if p.cita_textual:
                    marca = "✅ cita verificada en el PDF" if p.get("cita_verificada") else "⚠️ cita no encontrada en el PDF"
                    st.markdown(f"> {p.cita_textual}\n\n<small>{marca}</small>", unsafe_allow_html=True)
                if p.get("revisar") is True:
                    st.warning("Este análisis está marcado para revisión: el sustento está incompleto.")
            else:
                st.info("Este proyecto todavía no tiene primera lectura de la IA (no pasó el filtro de temas sensibles "
                        "o está en cola).")
            st.markdown(f"**Sumilla:** {p.sumilla}")
        with der:
            st.markdown(f"**Temática:** {p.tema}" + (f" · {p.temas_secundarios}" if p.temas_secundarios else ""))
            st.markdown(f"**Bancada:** {p.grupo_parlamentario}")
            st.markdown(f"**Autor:** {p.autor_principal or p.proponente}")
            if p.coautores:
                st.markdown(f"**Coautores:** {p.coautores.replace('; ', ', ')}")
            st.markdown(f"**Comisión:** {p.comisiones or '—'}")
            st.markdown(f"**Estado:** {p.ultimo_estado}")
            st.markdown(f"[📄 PDF del proyecto]({p.pdf_proyecto}) · [🏛️ Ver en el portal]({p.url})")
            m = movs[(movs.camara == p.camara) & (movs.pl_id == p.pl_id)][["seg_fecha", "seg_estado", "seg_detalle"]]
            st.markdown("**Recorrido**")
            st.dataframe(m.rename(columns={"seg_fecha": "Fecha", "seg_estado": "Estado", "seg_detalle": "Detalle"}),
                         hide_index=True, width="stretch")

# ===================== Panorama =====================
with tab_panorama:
    a, b = st.columns(2)
    por_tema = f.groupby(["tema", "semaforo"]).size().reset_index(name="n")
    a.plotly_chart(px.bar(por_tema, y="tema", x="n", color="semaforo", orientation="h",
                          color_discrete_map=COLOR_SEMAFORO, title="Proyectos por temática",
                          labels={"tema": "", "n": "proyectos", "semaforo": "IA"})
                   .update_layout(yaxis={"categoryorder": "total ascending"}), width="stretch")
    por_bancada = f.groupby(["grupo_parlamentario", "semaforo"]).size().reset_index(name="n")
    b.plotly_chart(px.bar(por_bancada, y="grupo_parlamentario", x="n", color="semaforo", orientation="h",
                          color_discrete_map=COLOR_SEMAFORO, title="Proyectos por bancada",
                          labels={"grupo_parlamentario": "", "n": "proyectos", "semaforo": "IA"})
                   .update_layout(yaxis={"categoryorder": "total ascending"}), width="stretch")

    cruce = pd.crosstab(f.tema, f.grupo_parlamentario)
    st.plotly_chart(px.imshow(cruce, text_auto=True, aspect="auto", color_continuous_scale="Purples",
                              title="¿De qué legisla cada bancada?", labels={"x": "", "y": "", "color": "proyectos"}),
                    width="stretch")
    semana = f.set_index("fecha_presentacion").resample("W").size().reset_index(name="n")
    st.plotly_chart(px.bar(semana, x="fecha_presentacion", y="n", title="Proyectos presentados por semana",
                           labels={"fecha_presentacion": "", "n": "proyectos"}), width="stretch")

st.caption("Fuente: portal de proposiciones legislativas del Congreso de la República. La primera lectura la hace "
           "un modelo abierto (qwen2.5 7B) que corre en local; es una alerta temprana, no una opinión legal.")
