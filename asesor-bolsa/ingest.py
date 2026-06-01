"""CLI de ingesta — une las capas 2 y 3.

Dos modos:

  # A) Sin API: carga una extracción ya hecha (JSON conforme a ExtraccionVideo).
  #    Útil para probar el almacén/análisis sin gastar tokens.
  python ingest.py --from-json fixtures/video_ejemplo.json --db asesor.db

  # B) Con API (requiere ANTHROPIC_API_KEY): extrae desde una transcripción.
  python ingest.py --transcripcion video.txt --fecha 2026-05-25 \\
      --autor "Inversor X" --db asesor.db
"""

from __future__ import annotations

import argparse
import json
import sqlite3

import store


def main() -> None:
    p = argparse.ArgumentParser(description="Ingesta de videos al asesor de bolsa")
    p.add_argument("--db", default="asesor.db", help="Ruta de la base SQLite")
    p.add_argument("--from-json", help="Extracción ya hecha (JSON) — no usa API")
    p.add_argument("--transcripcion", help="Fichero de texto con la transcripción")
    p.add_argument("--fecha", help="Fecha del video YYYY-MM-DD (modo transcripción)")
    p.add_argument("--autor", help="Autor del video (modo transcripción)")
    p.add_argument("--titulo", default=None)
    p.add_argument("--url", default=None)
    args = p.parse_args()

    conn = sqlite3.connect(args.db)
    store.init_db(conn)

    if args.from_json:
        with open(args.from_json, encoding="utf-8") as f:
            datos = json.load(f)
        modelo = None
        transcripcion = None
    elif args.transcripcion:
        if not (args.fecha and args.autor):
            p.error("--transcripcion requiere --fecha y --autor")
        from extract import MODELO, extraer  # import perezoso: solo si se usa la API

        with open(args.transcripcion, encoding="utf-8") as f:
            transcripcion = f.read()
        datos = extraer(
            transcripcion,
            fecha=args.fecha,
            autor=args.autor,
            titulo=args.titulo,
            url=args.url,
        ).model_dump(mode="json")
        modelo = MODELO
    else:
        p.error("indica --from-json o --transcripcion")

    video_id = store.guardar(
        conn, datos, transcripcion=transcripcion, modelo=modelo
    )
    n = len(datos.get("menciones", []))
    print(f"Guardado video id={video_id} ({datos['autor']}, {datos['fecha']}) "
          f"con {n} menciones en {args.db}")


if __name__ == "__main__":
    main()
