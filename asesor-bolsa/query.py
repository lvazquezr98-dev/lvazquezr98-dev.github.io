"""Capa 4 — Análisis (SQL puro, sin LLM).

Consultas de ejemplo sobre el almacén. Demuestran lo que el LLM NO hace bien y
SQL sí: recorrer todo, filtrar con precisión y agregar por fecha/ticker.

Uso:
    python query.py asesor.db
"""

from __future__ import annotations

import sqlite3
import sys


def ideas_activas_por_peg(conn: sqlite3.Connection, limite: int = 10) -> list[sqlite3.Row]:
    """Ideas activas más baratas según PEG (más bajo = más atractivo)."""
    return conn.execute(
        """SELECT ticker, fecha, peg_ratio, per_estimado, crecimiento_eps_pct, argumento
           FROM menciones
           WHERE tipo_mencion = 'idea_activa' AND peg_ratio IS NOT NULL
           ORDER BY peg_ratio ASC
           LIMIT ?""",
        (limite,),
    ).fetchall()


def evolucion_postura(conn: sqlite3.Connection, ticker: str) -> list[sqlite3.Row]:
    """Cómo cambió la postura sobre un activo a lo largo del tiempo."""
    return conn.execute(
        """SELECT fecha, postura, peg_ratio, confianza
           FROM menciones
           WHERE ticker = ? AND tipo_mencion = 'idea_activa'
           ORDER BY fecha""",
        (ticker,),
    ).fetchall()


def resumen_cartera(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    """Activos en los que el inversor declara posición propia."""
    return conn.execute(
        """SELECT DISTINCT m.ticker, a.nombre, m.fecha, m.postura
           FROM menciones m JOIN activos a ON a.ticker = m.ticker
           WHERE m.posicion_propia = 1
           ORDER BY m.fecha DESC"""
    ).fetchall()


def _imprimir(titulo: str, filas: list[sqlite3.Row]) -> None:
    print(f"\n=== {titulo} ===")
    if not filas:
        print("  (sin resultados)")
        return
    for f in filas:
        print("  " + " | ".join(f"{k}={f[k]}" for k in f.keys()))


def main(db: str) -> None:
    conn = sqlite3.connect(db)
    conn.row_factory = sqlite3.Row
    _imprimir("Ideas activas por PEG (más baratas primero)", ideas_activas_por_peg(conn))
    _imprimir("Evolución de la postura sobre AMZN", evolucion_postura(conn, "AMZN"))
    _imprimir("Posiciones propias declaradas", resumen_cartera(conn))


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "asesor.db")
