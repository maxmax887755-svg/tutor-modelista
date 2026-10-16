"""Estadísticas para el panel docente y reporte base para familias."""
from collections import Counter

from . import config


def resumen_grupo(repo, gid, dias=7):
    eventos = repo.eventos_grupo(gid, dias)
    alumnos = repo.listar_usuarios(rol="alumno", gid=gid)
    activos = {e["uid"] for e in eventos}
    tipos = Counter(e.get("tipo") for e in eventos)
    errores = sum(1 for e in eventos if not e.get("ok", True))
    dif = Counter()
    rachas = []
    por_alumno = []
    for a in alumnos:
        p = repo.get_progreso(a["uid"])
        dif.update(p.get("dificultades", {}))
        rachas.append(p.get("racha", 0))
        por_alumno.append({"nombre": a["nombre"], "uid": a["uid"], "xp": p["xp"], "racha": p.get("racha", 0),
                           "actividad": sum(1 for e in eventos if e["uid"] == a["uid"])})
    fb = repo.listar_feedback(gid)
    return {
        "alumnos": len(alumnos), "activos": len(activos), "mensajes": tipos.get("mensaje", 0),
        "quizzes": tipos.get("quiz", 0), "retos": tipos.get("reto", 0), "errores": errores,
        "racha_media": round(sum(rachas) / len(rachas), 1) if rachas else 0,
        "dificultades": dif.most_common(8), "por_alumno": sorted(por_alumno, key=lambda x: -x["actividad"]),
        "likes": sum(1 for f in fb if f.get("valor", 0) > 0), "dislikes": sum(1 for f in fb if f.get("valor", 0) < 0),
        "actividad_total": sum(tipos.get(t, 0) for t in ("mensaje", "quiz", "reto")),
    }


def datos_familia(repo, uid, dias=7):
    """Datos agregados (sin conversaciones) para el reporte a familias."""
    p = repo.get_progreso(uid)
    u = repo.get_usuario(uid) or {}
    eventos = []
    for g in u.get("grupos", []) or [""]:
        eventos += [e for e in repo.eventos_grupo(g, dias) if e["uid"] == uid]
    dias_activos = len({e["dia"] for e in eventos})
    return {"dias_activos": dias_activos, "mensajes": sum(1 for e in eventos if e["tipo"] == "mensaje"),
            "quizzes": sum(1 for e in eventos if e["tipo"] == "quiz"), "retos": sum(1 for e in eventos if e["tipo"] == "reto"),
            "racha": p.get("racha", 0), "temas_logrados": list(p.get("dominados", {}))[:5],
            "temas_por_reforzar": list(p.get("dificultades", {}))[:5],
            "precision": round(100 * p["aciertos"] / p["preguntas"]) if p.get("preguntas") else None}


def reporte_base(nombre, d):
    """Texto de respaldo si la IA no está disponible."""
    logros = ", ".join(d["temas_logrados"]) or "seguir practicando"
    refuerzo = ", ".join(d["temas_por_reforzar"]) or "ningún tema en particular"
    return (f"Reporte semanal de {nombre}\n\nEsta semana estudió con el tutor {d['dias_activos']} día(s) y "
            f"completó {d['quizzes']} quiz(es) y {d['retos']} reto(s) diario(s). Su racha actual es de {d['racha']} día(s).\n"
            f"Temas donde le fue bien: {logros}.\nTemas por reforzar: {refuerzo}.\n\n"
            "Sugerencias: 1) Pregúntele qué aprendió hoy y que se lo explique con sus palabras. "
            "2) Acompañe un ratito de estudio constante en lugar de sesiones largas. "
            "3) Celebre el esfuerzo, no solo los resultados.")


def resumen_escuela(repo, dias=14):
    """Vista general para la dirección: adopción, uso por día, grupos, temas difíciles y satisfacción."""
    orden = list(reversed(config.dias_atras(dias)))
    todos, serie = [], {}
    for d in orden:
        ev = repo.eventos_dia(d)
        todos += ev
        serie[d] = {"eventos": len(ev), "activos": len({e["uid"] for e in ev})}
    siete = set(config.dias_atras(7))
    alumnos = repo.listar_usuarios(rol="alumno")
    ids = {a["uid"] for a in alumnos}
    activos7 = {e["uid"] for e in todos if e["dia"] in siete and e["uid"] in ids}
    dif = Counter()
    for a in alumnos:
        dif.update(repo.get_progreso(a["uid"]).get("dificultades", {}))
    grupos = []
    for g in repo.listar_grupos():
        miembros = {a["uid"] for a in alumnos if g["gid"] in a.get("grupos", [])}
        ev = [e for e in todos if e.get("gid") == g["gid"] and e["dia"] in siete]
        grupos.append({"nombre": g["nombre"], "alumnos": len(miembros), "activos": len({e["uid"] for e in ev} & miembros),
                       "mensajes": sum(1 for e in ev if e["tipo"] == "mensaje"),
                       "quizzes_retos": sum(1 for e in ev if e["tipo"] in ("quiz", "reto"))})
    fb = repo.s.query("feedback")
    likes = sum(1 for f in fb if f.get("valor", 0) > 0)
    dislikes = sum(1 for f in fb if f.get("valor", 0) < 0)
    enc = repo.listar_encuestas()
    uso = [repo.uso_global(d) for d in orden]
    return {
        "dias": orden, "serie": serie, "alumnos": len(alumnos), "activos7": len(activos7),
        "adopcion": round(100 * len(activos7) / len(alumnos)) if alumnos else 0, "grupos": grupos,
        "dificultades": dif.most_common(8), "likes": likes, "dislikes": dislikes,
        "satisfaccion": round(100 * likes / (likes + dislikes)) if likes + dislikes else None,
        "encuesta_prom": round(sum(e["puntaje"] for e in enc) / len(enc), 1) if enc else None, "encuesta_n": len(enc),
        "comentarios": [{"rol": e.get("rol"), "puntaje": e["puntaje"], "comentario": e["comentario"]} for e in enc if e.get("comentario")][:10],
        "mensajes": sum(u.get("msgs", 0) for u in uso), "generaciones": sum(u.get("gen", 0) for u in uso),
        "tokens_in": sum(u.get("tin", 0) for u in uso), "tokens_out": sum(u.get("tout", 0) for u in uso),
        "quizzes": sum(1 for e in todos if e["tipo"] == "quiz"), "retos": sum(1 for e in todos if e["tipo"] == "reto"),
        "errores": len(repo.errores_recientes(7)),
    }


def reporte_direccion_md(d, escuela="Escuela Modelo", resumen_ia=""):
    """Reporte en Markdown para la dirección (se puede descargar y compartir)."""
    sat = f"{d['satisfaccion']}% de respuestas útiles (👍 {d['likes']} · 👎 {d['dislikes']})" if d["satisfaccion"] is not None else "aún sin datos"
    enc = f"{d['encuesta_prom']} de 5 ({d['encuesta_n']} respuestas)" if d["encuesta_prom"] is not None else "aún sin datos"
    lineas = [f"# Reporte del piloto · {escuela}", f"Generado el {config.hoy()} · últimos {len(d['dias'])} días", "",
              "## Adopción", f"- Alumnos registrados: {d['alumnos']}",
              f"- Alumnos activos en los últimos 7 días: {d['activos7']} ({d['adopcion']}%)", "",
              "## Uso", f"- Mensajes al tutor: {d['mensajes']}", f"- Quizzes: {d['quizzes']} · Retos del día: {d['retos']}",
              f"- Tokens procesados: {d['tokens_in']:,} entrada / {d['tokens_out']:,} salida", f"- Errores registrados (7 días): {d['errores']}", "",
              "## Satisfacción", f"- Utilidad de las respuestas: {sat}", f"- Encuesta de opinión: {enc}", "",
              "## Temas que más se les dificultan"]
    lineas += [f"- {t} ({n})" for t, n in d["dificultades"]] or ["- Aún sin datos"]
    lineas += ["", "## Por grupo (últimos 7 días)", "", "| Grupo | Alumnos | Activos | Mensajes | Quizzes y retos |", "|---|---|---|---|---|"]
    lineas += [f"| {g['nombre']} | {g['alumnos']} | {g['activos']} | {g['mensajes']} | {g['quizzes_retos']} |" for g in d["grupos"]]
    if d["comentarios"]:
        lineas += ["", "## Comentarios recientes (anónimos)"] + [f"- ({c['rol']}, {c['puntaje']}/5) {c['comentario']}" for c in d["comentarios"]]
    if resumen_ia:
        lineas += ["", "## Resumen y recomendaciones", resumen_ia]
    lineas += ["", "_Los datos reflejan uso y progreso; no incluyen conversaciones de los alumnos._"]
    return "\n".join(lineas)
