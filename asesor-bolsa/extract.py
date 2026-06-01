"""Capa 2 — Extracción estructurada con Claude.

Convierte la transcripción de UN video en un objeto `ExtraccionVideo` validado.
El LLM solo extrae datos a un esquema fijo; no analiza ni predice.

Requisitos: pip install anthropic pydantic
Credenciales: variable de entorno ANTHROPIC_API_KEY

Uso:
    from extract import extraer
    datos = extraer(transcripcion, fecha="2026-05-25", autor="Inversor X")
"""

from __future__ import annotations

import anthropic

from models import ExtraccionVideo

MODELO = "claude-opus-4-8"

# Instrucciones estables -> se cachean (mismas en cada video, ahorra coste/latencia).
SYSTEM = """\
Eres un extractor de datos financieros. Recibes la transcripción de un video de \
un inversor que comenta la bolsa, y devuelves SOLO datos estructurados conforme al \
esquema. No analizas, no predices, no opinas: extraes.

Reglas estrictas:
- Ignora el ruido: intros de hype, autopromoción, venta de cursos/formaciones. Si el \
  video es más venta/marketing que análisis, marca marketing_detectado = true.
- tipo_mencion es CRÍTICO:
  * idea_activa        -> el inversor la recomienda/analiza como oportunidad ACTUAL.
  * contexto_historico -> ejemplo del pasado (p.ej. "si invertiste en Apple en 2007"), \
    NO es una recomendación de hoy.
  * comparable         -> se nombra solo para comparar valoración con otra.
- enfasis: deep_dive (análisis dedicado), medio, o pasajera (mención de pasada).
- posicion_propia = true solo si el inversor declara tener posición ("nosotros invertimos...").
- Valoración: rellena per_estimado, crecimiento_eps_pct y peg_ratio SOLO si el video \
  los menciona o se pueden calcular de lo dicho. Si no, déjalos en null. NUNCA inventes números.
- precio_objetivo: solo si lo da explícitamente; casi siempre será null.
- moneda: USD, JPY, EUR... Importante para no mezclar yenes con dólares.
- cita_textual OBLIGATORIA: copia el fragmento LITERAL de la transcripción que respalda \
  cada mención. Si no encuentras una cita literal, no incluyas esa mención.
- La fecha y el autor te los doy en el mensaje; úsalos tal cual."""


def extraer(
    transcripcion: str,
    *,
    fecha: str,
    autor: str,
    titulo: str | None = None,
    url: str | None = None,
    client: anthropic.Anthropic | None = None,
) -> ExtraccionVideo:
    """Extrae un video a `ExtraccionVideo`. Lanza si el modelo no respeta el esquema."""
    client = client or anthropic.Anthropic()

    response = client.messages.parse(
        model=MODELO,
        max_tokens=16000,
        thinking={"type": "adaptive"},
        system=[
            {
                "type": "text",
                "text": SYSTEM,
                "cache_control": {"type": "ephemeral"},  # instrucciones estables -> cache
            }
        ],
        messages=[
            {
                "role": "user",
                "content": (
                    f"fecha: {fecha}\n"
                    f"autor: {autor}\n"
                    f"titulo: {titulo or ''}\n"
                    f"url: {url or ''}\n\n"
                    f"Transcripción:\n{transcripcion}"
                ),
            }
        ],
        output_format=ExtraccionVideo,
    )

    datos = response.parsed_output
    if datos is None:
        raise RuntimeError(
            f"El modelo no devolvió datos válidos (stop_reason={response.stop_reason})"
        )
    # Garantiza coherencia con lo que pedimos (el modelo a veces reescribe la fecha).
    datos.fecha = fecha
    datos.autor = autor
    return datos
