"""Capa 4a — Precios reales de mercado.

Llena la tabla `precios`. El LLM NO interviene aquí: son datos numéricos reales.

Fuentes:
- descargar(): precios reales vía yfinance (requiere `pip install yfinance` + red).
- cargar_csv(): carga desde un CSV (ticker,fecha,cierre,volumen).
- sintetico(): genera una serie ficticia y determinista, SOLO para demos/pruebas
  offline cuando no hay red ni yfinance. NO usar para análisis reales.
"""

from __future__ import annotations

import csv
import datetime as dt
import random
import sqlite3


def cargar_filas(conn: sqlite3.Connection, filas) -> int:
    """Inserta filas (ticker, fecha, cierre, volumen) en `precios`. Idempotente."""
    n = 0
    for ticker, fecha, cierre, volumen in filas:
        conn.execute(
            """INSERT INTO precios (ticker, fecha, cierre, volumen)
               VALUES (?, ?, ?, ?)
               ON CONFLICT(ticker, fecha) DO UPDATE SET
                   cierre = excluded.cierre, volumen = excluded.volumen""",
            (ticker, fecha, float(cierre), int(volumen) if volumen is not None else None),
        )
        n += 1
    conn.commit()
    return n


def cargar_csv(conn: sqlite3.Connection, ruta: str) -> int:
    """Carga precios desde un CSV con cabecera: ticker,fecha,cierre,volumen."""
    with open(ruta, encoding="utf-8") as f:
        lector = csv.DictReader(f)
        filas = [
            (r["ticker"], r["fecha"], r["cierre"], r.get("volumen"))
            for r in lector
        ]
    return cargar_filas(conn, filas)


def descargar(conn: sqlite3.Connection, tickers, desde: str, hasta: str) -> int:
    """Descarga precios reales de cierre vía yfinance y los guarda.

    Requiere `pip install yfinance`. `desde`/`hasta` en formato 'YYYY-MM-DD'.
    """
    import yfinance as yf  # import perezoso: solo si se usa esta vía

    filas = []
    data = yf.download(
        list(tickers), start=desde, end=hasta, group_by="ticker", progress=False
    )
    for t in tickers:
        # Con un solo ticker yfinance no agrupa; normalizamos ambos casos.
        sub = data[t] if len(tickers) > 1 else data
        for fecha, fila in sub.iterrows():
            cierre = fila.get("Close")
            if cierre is None or cierre != cierre:  # NaN
                continue
            vol = fila.get("Volume")
            filas.append((
                t,
                fecha.strftime("%Y-%m-%d"),
                float(cierre),
                None if vol is None or vol != vol else int(vol),
            ))
    return cargar_filas(conn, filas)


def sintetico(tickers, fecha_inicio: str, dias: int = 130, semilla: int = 7):
    """Serie de precios FICTICIA y determinista para demos offline.

    Random walk por ticker (solo días laborables). NO son datos reales.
    Devuelve filas (ticker, fecha, cierre, volumen) para cargar_filas().
    """
    inicio = dt.date.fromisoformat(fecha_inicio)
    filas = []
    for t in tickers:
        rnd = random.Random(f"{t}-{semilla}")
        precio = rnd.uniform(50, 500)
        # Deriva por ticker: algunos suben, otros bajan (para que haya aciertos y fallos).
        deriva = rnd.uniform(-0.004, 0.006)
        for i in range(dias):
            d = inicio + dt.timedelta(days=i)
            if d.weekday() >= 5:  # sábado/domingo: la bolsa cierra
                continue
            precio *= 1 + deriva + rnd.uniform(-0.02, 0.02)
            precio = max(precio, 1.0)
            filas.append((t, d.isoformat(), round(precio, 2), rnd.randint(1_000, 9_000)))
    return filas
