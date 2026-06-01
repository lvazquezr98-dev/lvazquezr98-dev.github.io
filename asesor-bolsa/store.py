"""Capa 3 — Almacén.

Inserta una extracción (dict JSON conforme a ExtraccionVideo) en SQLite.
No depende de pydantic ni anthropic: trabaja sobre dicts, así se puede usar y
probar de forma aislada.

Uso:
    import sqlite3, store
    conn = sqlite3.connect("asesor.db")
    store.init_db(conn)                       # crea tablas si no existen
    video_id = store.guardar(conn, datos)     # datos = dict (de JSON o model_dump)
"""

from __future__ import annotations

import json
import os
import sqlite3

_SCHEMA = os.path.join(os.path.dirname(__file__), "schema.sql")


def init_db(conn: sqlite3.Connection) -> None:
    """Crea las tablas (idempotente) a partir de schema.sql."""
    with open(_SCHEMA, encoding="utf-8") as f:
        conn.executescript(f.read())
    conn.commit()


def _upsert_activo(conn: sqlite3.Connection, m: dict) -> None:
    """Inserta el activo en el catálogo si aún no existe."""
    conn.execute(
        """INSERT INTO activos (ticker, nombre, sector, mercado, moneda, tipo)
           VALUES (?, ?, ?, ?, ?, ?)
           ON CONFLICT(ticker) DO UPDATE SET
               nombre  = COALESCE(excluded.nombre,  activos.nombre),
               sector  = COALESCE(excluded.sector,  activos.sector),
               mercado = COALESCE(excluded.mercado, activos.mercado),
               moneda  = COALESCE(excluded.moneda,  activos.moneda)""",
        (
            m["ticker"],
            m.get("nombre_empresa") or m["ticker"],
            m.get("sector"),
            m.get("mercado"),
            m.get("moneda"),
            None,
        ),
    )


def guardar(
    conn: sqlite3.Connection,
    datos: dict,
    *,
    transcripcion: str | None = None,
    modelo: str | None = None,
    duracion_seg: int | None = None,
) -> int:
    """Guarda un video y sus menciones. Devuelve el id del video.

    Idempotente por `url`: si ya existe un video con esa url, lo reemplaza
    (borra el anterior y sus menciones vía ON DELETE CASCADE).
    """
    url = datos.get("url") or None
    if url:
        conn.execute("DELETE FROM videos WHERE url = ?", (url,))

    cur = conn.execute(
        """INSERT INTO videos
               (fecha, autor, titulo, url, duracion_seg, tesis_macro, resumen,
                temas_macro, marketing_detectado, transcripcion, modelo_extraccion)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            datos["fecha"],
            datos["autor"],
            datos.get("titulo"),
            url,
            duracion_seg,
            datos.get("tesis_macro"),
            datos.get("resumen"),
            json.dumps(datos.get("temas_macro", []), ensure_ascii=False),
            1 if datos.get("marketing_detectado") else 0,
            transcripcion,
            modelo,
        ),
    )
    video_id = cur.lastrowid

    for m in datos.get("menciones", []):
        _upsert_activo(conn, m)
        conn.execute(
            """INSERT INTO menciones
                   (video_id, ticker, fecha, tipo_mencion, enfasis, postura,
                    horizonte, posicion_propia, per_estimado, crecimiento_eps_pct,
                    peg_ratio, precio_objetivo, precio_mencionado, confianza,
                    argumento, cita_textual)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                video_id,
                m["ticker"],
                datos["fecha"],  # desnormalizado desde el video
                m["tipo_mencion"],
                m.get("enfasis"),
                m["postura"],
                m.get("horizonte"),
                1 if m.get("posicion_propia") else 0,
                m.get("per_estimado"),
                m.get("crecimiento_eps_pct"),
                m.get("peg_ratio"),
                m.get("precio_objetivo"),
                m.get("precio_mencionado"),
                m.get("confianza"),
                m.get("argumento"),
                m.get("cita_textual"),
            ),
        )

    conn.commit()
    return video_id
