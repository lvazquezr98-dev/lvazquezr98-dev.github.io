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
| `schema.sql` | 3 | Esquema SQLite: `activos`, `videos`, `menciones`, `precios`. |

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

```bash
sqlite3 asesor.db < schema.sql      # crea la base de datos vacía
```

La extracción (capa 2) usa `models.py`: se pide al LLM que devuelva JSON conforme
a `ExtraccionVideo.model_json_schema()` y se valida con
`ExtraccionVideo.model_validate_json(...)`.

## Cómo resuelve los problemas habituales

| Problema "la IA no sirve" | Solución aquí |
|---|---|
| No razona entre toda la documentación | Cada video se extrae solo; el agregado lo hace SQL |
| No recorre cientos de páginas de forma fiable | Miles de filas indexadas, consulta exacta |
| No hace predicción ni estadística | `menciones` × `precios` por fecha → métricas reales con código |

## Siguientes pasos (no incluidos aún)

- Capa 1: script de transcripción (faster-whisper / API).
- Capa 2: cliente del LLM con structured output.
- Capa 4: ingesta de precios (yfinance) y cálculo de aciertos.
- Capa 5: interfaz de consulta.
