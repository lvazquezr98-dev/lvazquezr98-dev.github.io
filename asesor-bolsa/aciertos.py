"""Capa 4b — Auditoría de aciertos (el objetivo final).

Cruza cada recomendación (`menciones`) con el precio real (`precios`) y mide si
el inversor acertó: rendimiento a N días tras una postura de comprar/vender.

Disciplina de diseño:
- Solo se evalúan menciones tipo 'idea_activa' con postura 'comprar' o 'vender'.
  Los ejemplos históricos (Apple 2007, Cisco) y los 'mantener'/'mencion' se ignoran:
  no son apuestas medibles.
- 'comprar' acierta si el precio sube; 'vender' acierta si baja.
- Todo es aritmética sobre números reales. El LLM no interviene.

Uso:
    python aciertos.py asesor.db
"""

from __future__ import annotations

import datetime as dt
import sqlite3
import sys

HORIZONTES = (30, 90)  # días naturales tras la recomendación


def precio_en_o_despues(conn: sqlite3.Connection, ticker: str, fecha: str):
    """Cierre del primer día de cotización en o después de `fecha` (None si no hay)."""
    fila = conn.execute(
        """SELECT cierre FROM precios
           WHERE ticker = ? AND fecha >= ?
           ORDER BY fecha ASC LIMIT 1""",
        (ticker, fecha),
    ).fetchone()
    return fila[0] if fila else None


def rendimiento(conn: sqlite3.Connection, ticker: str, fecha: str, dias: int):
    """Rendimiento % entre `fecha` y `fecha`+dias (None si faltan precios)."""
    p0 = precio_en_o_despues(conn, ticker, fecha)
    objetivo = (dt.date.fromisoformat(fecha) + dt.timedelta(days=dias)).isoformat()
    p1 = precio_en_o_despues(conn, ticker, objetivo)
    if p0 is None or p1 is None or p0 == 0:
        return None
    return round((p1 - p0) / p0 * 100, 1)


def _acierto(postura: str, rend: float) -> bool:
    return rend > 0 if postura == "comprar" else rend < 0


def evaluar(conn: sqlite3.Connection, horizontes=HORIZONTES) -> list[dict]:
    """Evalúa cada recomendación apostable y devuelve filas con sus rendimientos."""
    menciones = conn.execute(
        """SELECT ticker, fecha, postura, confianza, enfasis, posicion_propia, peg_ratio
           FROM menciones
           WHERE tipo_mencion = 'idea_activa' AND postura IN ('comprar', 'vender')
           ORDER BY fecha, ticker"""
    ).fetchall()

    resultados = []
    for ticker, fecha, postura, confianza, enfasis, prop, peg in menciones:
        fila = {
            "ticker": ticker, "fecha": fecha, "postura": postura,
            "confianza": confianza, "enfasis": enfasis,
            "posicion_propia": bool(prop), "peg_ratio": peg,
        }
        for h in horizontes:
            r = rendimiento(conn, ticker, fecha, h)
            fila[f"rend_{h}d"] = r
            fila[f"acierto_{h}d"] = None if r is None else _acierto(postura, r)
        resultados.append(fila)
    return resultados


def tasa_acierto(resultados: list[dict], horizonte: int, filtro=None) -> tuple[int, int]:
    """(aciertos, total_evaluables) para un horizonte, con filtro opcional."""
    clave = f"acierto_{horizonte}d"
    filas = [r for r in resultados if r[clave] is not None]
    if filtro:
        filas = [r for r in filas if filtro(r)]
    aciertos = sum(1 for r in filas if r[clave])
    return aciertos, len(filas)


def _pct(a: int, t: int) -> str:
    return f"{a}/{t} ({100 * a / t:.0f}%)" if t else "sin datos suficientes"


def informe(conn: sqlite3.Connection) -> None:
    res = evaluar(conn)
    print("=== Rendimiento por recomendación ===")
    for r in res:
        def marca(h):
            a = r[f"acierto_{h}d"]
            rd = r[f"rend_{h}d"]
            if a is None:
                return f"{h}d: s/d"
            return f"{h}d: {'✓' if a else '✗'} {rd:+.1f}%"
        print(f"  {r['ticker']:7} {r['postura']:8} "
              f"{marca(30)}  {marca(90)}  (conf={r['confianza']})")

    for h in HORIZONTES:
        print(f"\n=== Tasa de acierto a {h} días ===")
        print(f"  Global:                {_pct(*tasa_acierto(res, h))}")
        print(f"  Confianza alta:        "
              f"{_pct(*tasa_acierto(res, h, lambda r: r['confianza'] == 'alta'))}")
        print(f"  Con posición propia:   "
              f"{_pct(*tasa_acierto(res, h, lambda r: r['posicion_propia']))}")
        print(f"  Análisis deep_dive:    "
              f"{_pct(*tasa_acierto(res, h, lambda r: r['enfasis'] == 'deep_dive'))}")


if __name__ == "__main__":
    db = sys.argv[1] if len(sys.argv) > 1 else "asesor.db"
    conn = sqlite3.connect(db)
    informe(conn)
