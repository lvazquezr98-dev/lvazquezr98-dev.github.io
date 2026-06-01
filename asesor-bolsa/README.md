# Asesor de Bolsa — Capa de datos

Sistema para convertir transcripciones de videos de análisis bursátil en datos
estructurados, analizables y correlacionables con precios reales de mercado.

## La idea central

> El LLM **no es la base de datos**. El LLM traduce texto ↔ datos y explica.
> El análisis estadístico y la correlación temporal los hace SQL y código.

El error que da resultados pésimos es usar al LLM como almacén **y** como
analista a la vez (subir PDFs/transcripciones crudas y "preguntarle"). El LLM
se ahoga en el ruido, no puede recorrer cientos de páginas de forma fiable y no
hace estadística sobre prosa. Esta arquitectura separa las responsabilidades.

## Arquitectura (5 capas)

```
[1] INGESTA      video semanal -> audio -> transcripción (texto crudo)
[2] EXTRACCIÓN   texto crudo -> LLM con esquema fijo -> JSON validado   (models.py)
[3] ALMACÉN      JSON -> base de datos SQLite                           (schema.sql)
[4] ANÁLISIS     SQL / pandas / estadística -> métricas, correlaciones
[5] RESPUESTA    LLM lee SOLO resultados ya filtrados -> explicación
```

El LLM aparece en las capas **2 y 5**, nunca en la **3 ni la 4**.

## Archivos

| Archivo | Capa | Qué es |
|---|---|---|
| `models.py` | 2 | Contrato de extracción (Pydantic). Lo que el LLM debe rellenar por video. |
| `extract.py` | 2 | Llama a Claude con structured output y valida contra `models.py`. |
| `schema.sql` | 3 | Esquema SQLite: `activos`, `videos`, `menciones`, `precios`. |
| `store.py` | 3 | Inserta una extracción en SQLite (idempotente por `url`). |
| `precios.py` | 4 | Llena `precios` con datos reales (yfinance), CSV, o sintéticos para demo. |
| `query.py` | 4 | Consultas de análisis: ranking por PEG, evolución, posiciones propias. |
| `aciertos.py` | 4 | Auditoría: rendimiento real a 30/90 días tras cada comprar/vender. |
| `benchmark.py` | 4 | Prueba de fuego: alpha vs S&P 500 (¿batir al índice o no?). |
| `ingest.py` | — | CLI que une las capas (`--from-json` sin API / `--transcripcion` con API). |
| `fixtures/` | — | Extracción de ejemplo (video real) para probar sin gastar tokens. |

## Modelo de datos

```
videos (1) ──< menciones >── (1) activos
                  │
                  └─ se cruza con ── precios (datos reales de mercado)
```

- **videos**: 1 fila por video (fecha, autor, tesis macro, resumen).
- **menciones**: 1 fila por activo mencionado (postura, PEG, confianza, cita).
- **activos**: catálogo de tickers (sector, mercado, moneda).
- **precios**: cierre real por ticker y día (desde una API; el LLM no lo toca).

## Decisiones de diseño clave

- **`tipo_mencion`** (`idea_activa` / `contexto_historico` / `comparable`):
  separa recomendaciones reales de ejemplos del pasado (Apple 2007, Cisco como
  advertencia). Sin esto, las métricas de acierto salen falseadas.
- **Valoración por PEG** (`per_estimado`, `crecimiento_eps_pct`, `peg_ratio`):
  este tipo de inversor casi nunca da precio objetivo, pero sí PER + crecimiento
  (marco de Peter Lynch). Son números comparables y rankeables.
- **`cita_textual` obligatoria**: seguro anti-alucinación. Sin cita literal, la
  mención se descarta.
- **`fecha` desnormalizada en `menciones`**: se repite desde `videos` a propósito
  para acelerar los filtros por fecha+ticker (los más frecuentes).
- **`marketing_detectado`**: marca videos que son más venta/hype que análisis,
  para poder filtrarlos o penalizarlos.

## Puesta en marcha

Sin API (prueba el almacén + análisis con el ejemplo incluido):

```bash
python3 ingest.py --from-json fixtures/video_ejemplo.json --db asesor.db
python3 query.py asesor.db
```

Auditoría de aciertos (objetivo final) — necesita precios reales:

```bash
pip install yfinance        # capa 4a
python3 - <<'PY'
import sqlite3, precios
conn = sqlite3.connect("asesor.db")
tickers = [r[0] for r in conn.execute(
  "SELECT DISTINCT ticker FROM menciones "
  "WHERE tipo_mencion='idea_activa' AND postura IN ('comprar','vender')")]
precios.descargar(conn, tickers, "2025-01-01", "2026-06-01")
PY
python3 aciertos.py asesor.db
```

Benchmark contra el índice (¿bate al S&P 500?) — descarga también el índice:

```bash
python3 -c "import sqlite3, precios; \
  precios.descargar(sqlite3.connect('asesor.db'), ['^GSPC'], '2025-01-01', '2026-06-01')"
python3 benchmark.py asesor.db
```

Con API (extraer un video nuevo desde su transcripción):

```bash
pip install -r requirements.txt
export ANTHROPIC_API_KEY=...
python3 ingest.py --transcripcion video.txt --fecha 2026-05-25 --autor "Inversor X"
```

> `precios.sintetico()` genera precios **ficticios** para probar la auditoría sin
> red; las tasas de acierto que produce no significan nada. Para medir de verdad,
> usa `precios.descargar()` (yfinance) sobre videos con fecha lo bastante antigua
> como para tener 30–90 días de cotización posterior.

## Cómo resuelve los problemas habituales

| Problema "la IA no sirve" | Solución aquí |
|---|---|
| No razona entre toda la documentación | Cada video se extrae solo; el agregado lo hace SQL |
| No recorre cientos de páginas de forma fiable | Miles de filas indexadas, consulta exacta |
| No hace predicción ni estadística | `menciones` × `precios` por fecha → métricas reales con código |

## Siguientes pasos (no incluidos aún)

- Capa 1: script de transcripción (faster-whisper / API) que automatice video → texto.
- Capa 5: interfaz de consulta en lenguaje natural (el LLM lee solo el resultado
  ya filtrado del análisis y lo explica).
- Automatización semanal (cron / GitHub Actions) para ingerir el video nuevo.
