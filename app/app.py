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

    # primera lectura (modelo local) y, encima, la segunda lectura del agente revisor cuando existe
    lecturas = []
    for archivo, quien in [("riesgo.jsonl", "IA local (qwen2.5 7B)"), ("revision.jsonl", None)]:
        ruta = DATA / archivo
        if ruta.exists():
            filas = [json.loads(l) for l in ruta.read_text(encoding="utf-8").splitlines() if l]
            for j in filas:
                j.setdefault("revisado_por", quien)
            lecturas += filas
    if lecturas:
        lect = pd.DataFrame(lecturas).drop_duplicates(["camara", "pl_id"], keep="last")
        df = df.merge(lect.drop(columns=["modelo"], errors="ignore"), on=["camara", "pl_id"], how="left")
    for col in ["semaforo", "resumen", "explicacion", "cita_textual", "revisado_por"]:
        if col not in df:
            df[col] = None
    df["semaforo"] = df["semaforo"].fillna("sin leer")
    df["fecha_presentacion"] = pd.to_datetime(df["fecha_presentacion"], errors="coerce")
    df["grupo_parlamentario"] = df["grupo_parlamentario"].replace("", "Sin bancada (Ejecutivo, instituciones, otros)")
    df["estado"] = df["ultimo_estado"].map(simplificar_estado)

    movs = pd.read_csv(DATA / "movimientos.csv", dtype=str).fillna("")

    # votaciones del Pleno adjuntas a los expedientes (scripts/votaciones.py)
    vot = pd.read_csv(DATA / "votaciones.csv", dtype=str).fillna("")
    vot = vot[vot.tipo != "Asistencia"]
    # el acta («Nota») solo se muestra si esa votación no tiene la tabla nominal
    con_tabla = set(vot[vot.tipo == "Votación"].movimiento + vot[vot.tipo == "Votación"].proposiciones)
    vot = vot[(vot.tipo == "Votación") | ~(vot.movimiento + vot.proposiciones).isin(con_tabla)]
    vot = vot.drop_duplicates(["proposiciones", "movimiento", "a_favor", "en_contra"])
    votos = pd.read_csv(DATA / "votos.csv", dtype=str).fillna("")
    return df, movs, vot, votos


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


df, movs, vot, votos = cargar()

SIGLA = {"FP": "Fuerza Popular", "JP": "Juntos por el Perú", "PBG": "Partido del Buen Gobierno",
         "RP": "Renovación Popular", "AN": "Ahora Nación", "OBRAS": "Partido Cívico Obras"}
COLOR_VOTO = {"Sí": "#2E7D32", "No": "#C62828", "Abstención": "#F9A825", "Sin respuesta": "#9E9E9E"}


def votos_por_bancada(v) -> pd.DataFrame:
    """Votos por bancada de una votación: el cuadro oficial impreso en el PDF o, si no se pudo leer, la suma
    de los votos individuales leídos."""
    if v.votos_por_bancada:
        filas = [{"bancada": SIGLA.get(b, b), "voto": voto, "n": n}
                 for b, nums in json.loads(v.votos_por_bancada).items()
                 for voto, n in zip(["Sí", "No", "Abstención", "Sin respuesta"], nums)]
        return pd.DataFrame(filas)
    x = votos[(votos.pdf == v.pdf) & (votos.pagina == str(v.pagina)) & votos.codigo.isin(["SI", "NO", "Abst.", "SinRes"])]
    return x.assign(bancada=x.bancada.map(SIGLA), voto=x.resultado).groupby(["bancada", "voto"]).size().reset_index(name="n")


def grafico_votacion(v, alto=260):
    d = votos_por_bancada(v)
    if d.empty:
        return None
    return px.bar(d, y="bancada", x="n", color="voto", orientation="h", color_discrete_map=COLOR_VOTO, height=alto,
                  labels={"bancada": "", "n": "votos", "voto": ""}).update_layout(
        margin=dict(l=0, r=0, t=10, b=0), yaxis={"categoryorder": "total ascending"}, legend_orientation="h")


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

tab_lista, tab_votos, tab_panorama = st.tabs(["📋 Proyectos", "🗳️ Votaciones", "📊 Panorama"])

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
                if str(p.revisado_por).startswith("agente"):
                    st.success("✔ Segunda lectura: revisado por el agente revisor")
                elif p.get("revisar") is True:
                    st.warning("Primera lectura con sustento incompleto: en cola para la segunda lectura.")
                st.caption(f"Leído por: {p.revisado_por}")
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

        mis_votos = vot[(vot.camara == p.camara) & vot.proposiciones.str.contains(p.pl_id, regex=False)]
        if len(mis_votos):
            st.markdown(f"#### 🗳️ Votaciones en el Pleno ({len(mis_votos)})")
            for v in mis_votos.itertuples():
                icono = "✅" if v.resultado == "Aprobado" else "❌"
                st.markdown(f"**{icono} {v.resultado}** · {v.fecha} · {v.movimiento.capitalize()[:160]}  \n"
                            f"A favor **{v.a_favor or '—'}** · En contra **{v.en_contra or '—'}** · "
                            f"Abstenciones **{v.abstencion or '—'}**")
                g = grafico_votacion(v)
                if g is not None:
                    st.plotly_chart(g, width="stretch", key=f"g_{v.pdf}_{v.pagina}")
                else:
                    st.caption("Acta sin votación nominal: solo el resultado.")

# ===================== Votaciones =====================
with tab_votos:
    nominales = vot[vot.tipo == "Votación"].copy()
    st.markdown(f"**{len(nominales)} votaciones nominales del Pleno** vinculadas a "
                f"{nominales.proposiciones.str.split('; ').explode().nunique()} proyectos de ley. "
                "Fuente: los PDF de «Asistencia y votación» que el Congreso adjunta a cada expediente, leídos con "
                "texto nativo u OCR y contrastados con los totales impresos.")
    camara_v = st.radio("Cámara", ["diputados", "senado"], horizontal=True, format_func=str.title)
    vv = nominales[nominales.camara == camara_v]
    vt = votos[(votos.camara == camara_v) & votos.codigo.isin(["SI", "NO", "Abst."])]
    vt = vt[vt.pdf.isin(vv.pdf)]

    # posición mayoritaria de cada bancada en cada votación
    vt = vt.assign(votacion=vt.pdf + "-" + vt.pagina)
    pos = vt.groupby(["votacion", "bancada"]).codigo.agg(lambda x: x.value_counts().index[0]).unstack()
    cohesion = vt.groupby(["votacion", "bancada"]).codigo.agg(lambda x: x.value_counts().iloc[0] / len(x)) \
                 .groupby("bancada").mean().sort_values(ascending=False)

    c1, c2 = st.columns(2)
    c1.plotly_chart(px.bar(x=cohesion.values * 100, y=[SIGLA.get(b, b) for b in cohesion.index], orientation="h",
                           title="Cohesión: % de la bancada que vota como su mayoría",
                           labels={"x": "%", "y": ""}, range_x=[0, 100], text=[f"{v:.0%}" for v in cohesion.values])
                    .update_layout(yaxis={"categoryorder": "total ascending"}), width="stretch")
    bancadas = [b for b in pos.columns]
    coincide = pd.DataFrame([[((pos[a] == pos[b]) & pos[a].notna() & pos[b].notna()).sum() /
                               max((pos[a].notna() & pos[b].notna()).sum(), 1) * 100 for b in bancadas] for a in bancadas],
                            index=[SIGLA.get(b, b) for b in bancadas], columns=[SIGLA.get(b, b) for b in bancadas])
    c2.plotly_chart(px.imshow(coincide.round(0), text_auto=True, color_continuous_scale="Purples", zmin=0, zmax=100,
                              title="¿Quién vota con quién? (% de votaciones con la misma posición)",
                              labels={"color": "%"}), width="stretch")

    st.markdown("#### Cada votación")
    for v in vv.sort_values("fecha", ascending=False).itertuples():
        with st.expander(f"{'✅' if v.resultado == 'Aprobado' else '❌'} {v.fecha} · PL {v.proposiciones} · "
                         f"{v.movimiento.capitalize()[:110]}"):
            st.markdown(f"**Asunto:** {v.asunto}")
            st.markdown(f"A favor **{v.a_favor}** · En contra **{v.en_contra}** · Abstenciones **{v.abstencion}** · "
                        f"Lectura: {v.fuente} · Control: {v.control}")
            g = grafico_votacion(v)
            if g is not None:
                st.plotly_chart(g, width="stretch", key=f"t_{v.pdf}_{v.pagina}")
            st.markdown(f"[📄 PDF de la votación]({v.url})")

    st.markdown("#### ¿Cómo votó un congresista?")
    nombre = st.selectbox("Congresista", sorted(votos[votos.camara == camara_v].congresista.unique()), index=None,
                          placeholder="Escribe un apellido…")
    if nombre:
        h = votos[(votos.congresista == nombre) & votos.pdf.isin(vv.pdf)].merge(
            vv[["pdf", "pagina", "movimiento", "proposiciones"]].astype(str), on=["pdf", "pagina"])
        st.dataframe(h[["fecha", "proposiciones", "movimiento", "resultado", "voto_oral"]].rename(columns={
            "fecha": "Fecha", "proposiciones": "Proyecto", "movimiento": "Votación", "resultado": "Voto",
            "voto_oral": "Voto oral"}), hide_index=True, width="stretch")

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
