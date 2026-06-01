"""Capa 4c — Benchmark contra el S&P 500 (la prueba de fuego).

Acertar no basta: si el inversor dice "comprar" y la acción sube un 5%, pero el
S&P 500 subió un 8% en la misma ventana, habrías ganado MÁS sin escucharle. Lo
que importa es el ALPHA: cuánto bate (o no) al índice.

Para cada recomendación calcula:
    alpha = rendimiento_del_activo - rendimiento_del_indice   (misma ventana)

"Bate al índice":
    - comprar -> alpha > 0  (la acción lo hizo mejor que el índice)
    - vender  -> alpha < 0  (la acción lo hizo peor: acertaste evitándola)

Requiere que el índice esté en la tabla `precios` con su propio ticker
(por defecto '^GSPC', el del S&P 500 en yfinance).

Uso:
    python benchmark.py asesor.db
"""

from __future__ import annotations

import sqlite3
import sys

from aciertos import HORIZONTES, rendimiento

BENCHMARK_DEFAULT = "^GSPC"  # S&P 500 en yfinance (alternativa: 'SPY')


def evaluar_vs_indice(
    conn: sqlite3.Connection,
    benchmark: str = BENCHMARK_DEFAULT,
    horizontes=HORIZONTES,
) -> list[dict]:
    """Para cada comprar/vender apostable, calcula alpha vs el índice por horizonte."""
    menciones = conn.execute(
        """SELECT ticker, fecha, postura, confianza, enfasis, posicion_propia
           FROM menciones
           WHERE tipo_mencion = 'idea_activa' AND postura IN ('comprar', 'vender')
           ORDER BY fecha, ticker"""
    ).fetchall()

    filas = []
    for ticker, fecha, postura, confianza, enfasis, prop in menciones:
        fila = {
            "ticker": ticker, "fecha": fecha, "postura": postura,
            "confianza": confianza, "enfasis": enfasis, "posicion_propia": bool(prop),
        }
        for h in horizontes:
            r_act = rendimiento(conn, ticker, fecha, h)
            r_idx = rendimiento(conn, benchmark, fecha, h)
            if r_act is None or r_idx is None:
                fila[f"rend_{h}d"] = r_act
                fila[f"indice_{h}d"] = r_idx
                fila[f"alpha_{h}d"] = None
                fila[f"bate_{h}d"] = None
            else:
                alpha = round(r_act - r_idx, 1)
                fila[f"rend_{h}d"] = r_act
                fila[f"indice_{h}d"] = r_idx
                fila[f"alpha_{h}d"] = alpha
                fila[f"bate_{h}d"] = alpha > 0 if postura == "comprar" else alpha < 0
        filas.append(fila)
    return filas


def _media(valores) -> float | None:
    vs = [v for v in valores if v is not None]
    return round(sum(vs) / len(vs), 1) if vs else None


def informe(conn: sqlite3.Connection, benchmark: str = BENCHMARK_DEFAULT) -> None:
    res = evaluar_vs_indice(conn, benchmark)

    if not any(r[f"alpha_{HORIZONTES[0]}d"] is not None for r in res):
        print(f"No hay precios del índice ({benchmark}) en la tabla `precios`.")
        print("Descárgalo primero, p.ej.:")
        print(f"  precios.descargar(conn, ['{benchmark}'], '2025-01-01', '2026-06-01')")
        return

    print(f"=== Alpha vs índice ({benchmark}) por recomendación ===")
    for r in res:
        def marca(h):
            a = r[f"bate_{h}d"]
            if a is None:
                return f"{h}d: s/d"
            return (f"{h}d: {'BATE' if a else 'pierde'} "
                    f"(activo {r[f'rend_{h}d']:+.1f}% vs índice {r[f'indice_{h}d']:+.1f}% "
                    f"= alpha {r[f'alpha_{h}d']:+.1f}%)")
        print(f"  {r['ticker']:7} {r['postura']:8} {marca(30)}")
        print(f"  {'':7} {'':8} {marca(90)}")

    for h in HORIZONTES:
        evaluables = [r for r in res if r[f"bate_{h}d"] is not None]
        if not evaluables:
            continue
        baten = sum(1 for r in evaluables if r[f"bate_{h}d"])
        total = len(evaluables)
        compras = [r for r in evaluables if r["postura"] == "comprar"]
        alpha_medio = _media([r[f"alpha_{h}d"] for r in compras])
        rend_medio = _media([r[f"rend_{h}d"] for r in compras])
        idx_medio = _media([r[f"indice_{h}d"] for r in compras])

        print(f"\n=== Veredicto a {h} días ===")
        print(f"  Recomendaciones que baten al índice: {baten}/{total} "
              f"({100 * baten / total:.0f}%)")
        if compras:
            print(f"  Compras: rend. medio {rend_medio:+.1f}%  vs  "
                  f"índice {idx_medio:+.1f}%  ->  alpha medio {alpha_medio:+.1f}%")
            if alpha_medio is not None:
                if alpha_medio > 0:
                    print(f"  => De media, seguir sus compras batió al S&P 500 "
                          f"en {alpha_medio:+.1f} puntos.")
                else:
                    print(f"  => De media, habrías ganado MÁS comprando el índice "
                          f"(alpha {alpha_medio:+.1f}).")


if __name__ == "__main__":
    db = sys.argv[1] if len(sys.argv) > 1 else "asesor.db"
    conn = sqlite3.connect(db)
    informe(conn)
