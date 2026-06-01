"""Asesor de Bolsa — Modelos de extracción (capa 2).

Este módulo define el "contrato" que el LLM debe cumplir al convertir la
transcripción de UN video en datos estructurados. Validado con Pydantic:
si el LLM devuelve algo que no encaja en este esquema, se rechaza.

Reglas de oro (lo que separa un sistema fiable de uno con resultados pésimos):
  1. Enumeraciones cerradas, nunca texto libre, para los campos clave.
  2. `None` explícito permitido: prohibido inventar números para rellenar huecos.
  3. `cita_textual` obligatoria: si el LLM no encuentra una cita literal que
     respalde la mención, es señal de alucinación y la mención se descarta.
  4. `tipo_mencion` separa recomendaciones reales de ejemplos históricos.

Uso típico (capa 2):
    from anthropic import Anthropic
    client = Anthropic()
    # ... pedir al modelo que devuelva JSON conforme a ExtraccionVideo.model_json_schema()
    datos = ExtraccionVideo.model_validate_json(respuesta_json)
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


# --------------------------------------------------------------------------- #
# Enumeraciones cerradas
# --------------------------------------------------------------------------- #
class Tesis(str, Enum):
    alcista = "alcista"
    bajista = "bajista"
    neutral = "neutral"


class Postura(str, Enum):
    comprar = "comprar"
    vender = "vender"
    mantener = "mantener"
    mencion = "mencion"  # se nombra sin postura clara de compra/venta


class Horizonte(str, Enum):
    corto = "corto"   # < 1 año
    medio = "medio"   # 1-3 años
    largo = "largo"   # > 3 años


class Confianza(str, Enum):
    alta = "alta"
    media = "media"
    baja = "baja"


class TipoMencion(str, Enum):
    idea_activa = "idea_activa"                # recomendación/tesis actual
    contexto_historico = "contexto_historico"  # ejemplo del pasado (Apple 2007, Cisco)
    comparable = "comparable"                  # solo para comparar valoración


class Enfasis(str, Enum):
    deep_dive = "deep_dive"   # análisis profundo dedicado
    medio = "medio"
    pasajera = "pasajera"     # mención de pasada


# --------------------------------------------------------------------------- #
# Modelos
# --------------------------------------------------------------------------- #
class Mencion(BaseModel):
    """Un activo mencionado dentro de un video."""

    ticker: str = Field(..., description="Símbolo bursátil en mayúsculas. Japón usa sufijo .T, p.ej. 3445.T")
    nombre_empresa: str
    mercado: str | None = Field(None, description="NASDAQ, NYSE, TSE, AMS...")
    moneda: str | None = Field(None, description="USD, JPY, EUR. Necesario para no mezclar yenes con dólares")
    sector: str | None = None

    tipo_mencion: TipoMencion = Field(
        ..., description="CRÍTICO: idea_activa vs contexto_historico vs comparable"
    )
    enfasis: Enfasis = Field(Enfasis.pasajera, description="Cuánto espacio le dedica el autor")
    postura: Postura
    horizonte: Horizonte | None = None
    posicion_propia: bool = Field(
        False, description="True si el autor declara tener posición ('nosotros invertimos...')"
    )

    # Valoración estilo Peter Lynch (lo que este tipo de inversor sí aporta)
    per_estimado: float | None = Field(None, description="PER a 12 meses; null si no lo dice")
    crecimiento_eps_pct: float | None = Field(None, description="Crecimiento esperado de beneficios (%)")
    peg_ratio: float | None = Field(None, description="PER / crecimiento; null si no se puede calcular")
    precio_objetivo: float | None = Field(None, description="Solo si lo da explícitamente; casi siempre null")
    precio_mencionado: float | None = Field(None, description="Precio del que hablaba en ese momento")

    confianza: Confianza
    argumento: str = Field(..., description="Una frase: la razón principal")
    cita_textual: str = Field(..., description="Fragmento LITERAL de la transcripción que respalda esto")


class ExtraccionVideo(BaseModel):
    """Resultado de extraer UN video completo."""

    fecha: str = Field(..., description="Fecha del video, formato YYYY-MM-DD (del metadato)")
    autor: str
    titulo: str | None = None
    url: str | None = None
    tesis_macro: Tesis
    resumen: str = Field(..., description="2-3 frases resumiendo la tesis central del video")
    temas_macro: list[str] = Field(default_factory=list, description="Ej: ['adopción de IA','escasez RAM']")
    marketing_detectado: bool = Field(
        False, description="True si el video es más venta de formación/hype que análisis"
    )
    menciones: list[Mencion] = Field(default_factory=list)
