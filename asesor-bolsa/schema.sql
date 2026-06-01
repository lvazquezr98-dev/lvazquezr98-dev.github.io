-- ============================================================================
-- Asesor de Bolsa — Esquema de datos (SQLite)
-- ============================================================================
-- Capa 3 de la arquitectura: texto -> extracción -> [ALMACÉN] -> análisis.
--
-- Principio rector: el LLM NUNCA analiza este almacén. El LLM solo LLENA las
-- tablas (capa de extracción) y luego LEE resultados ya filtrados (capa de
-- respuesta). El análisis estadístico y la correlación temporal los hace SQL
-- y código sobre estas tablas, con precisión perfecta y sin alucinaciones.
--
-- Para crear la base de datos:
--   sqlite3 asesor.db < schema.sql
-- ============================================================================

PRAGMA foreign_keys = ON;

-- ============================================================================
-- activos — catálogo limpio de tickers (se llena una vez, se reutiliza)
-- ============================================================================
CREATE TABLE IF NOT EXISTS activos (
    ticker   TEXT PRIMARY KEY,          -- 'AMZN', '3445.T'
    nombre   TEXT NOT NULL,             -- 'Amazon.com Inc.'
    sector   TEXT,                      -- 'e-commerce', 'semiconductores'...
    mercado  TEXT,                      -- 'NASDAQ', 'NYSE', 'TSE'
    moneda   TEXT,                      -- 'USD', 'JPY', 'EUR'
    tipo     TEXT                       -- 'accion' | 'etf' | 'cripto' | 'indice'
);

-- ============================================================================
-- videos — un registro por video (la "cabecera")
-- ============================================================================
CREATE TABLE IF NOT EXISTS videos (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    fecha               TEXT NOT NULL,   -- 'YYYY-MM-DD' (clave para correlación temporal)
    autor               TEXT NOT NULL,
    titulo              TEXT,
    url                 TEXT UNIQUE,     -- evita procesar dos veces el mismo video
    duracion_seg        INTEGER,
    tesis_macro         TEXT,            -- 'alcista' | 'bajista' | 'neutral'
    resumen             TEXT,            -- 2-3 frases generadas por el LLM
    temas_macro         TEXT,            -- JSON array: ["tasas","inflación"]
    marketing_detectado INTEGER DEFAULT 0,  -- 1 si el video es más venta/hype que análisis
    transcripcion       TEXT,            -- texto crudo (se guarda, NO se analiza)
    modelo_extraccion   TEXT,            -- p.ej. 'claude-...' para trazabilidad
    procesado_en        TEXT DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_videos_fecha ON videos(fecha);

-- ============================================================================
-- menciones — un registro por activo mencionado dentro de un video
-- ============================================================================
-- tipo_mencion es CRÍTICO: separa recomendaciones reales de ejemplos
-- históricos (Apple 2007, Cisco) y de comparables. Sin esto, las métricas
-- de acierto salen falseadas.
CREATE TABLE IF NOT EXISTS menciones (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    video_id            INTEGER NOT NULL REFERENCES videos(id) ON DELETE CASCADE,
    ticker              TEXT NOT NULL REFERENCES activos(ticker),
    fecha               TEXT NOT NULL,   -- desnormalizado desde videos.fecha (acelera consultas)

    tipo_mencion        TEXT NOT NULL,   -- 'idea_activa' | 'contexto_historico' | 'comparable'
    enfasis             TEXT,            -- 'deep_dive' | 'medio' | 'pasajera'
    postura             TEXT NOT NULL,   -- 'comprar' | 'vender' | 'mantener' | 'mencion'
    horizonte           TEXT,            -- 'corto' | 'medio' | 'largo'
    posicion_propia     INTEGER DEFAULT 0,  -- 1 si el autor declara tener posición

    -- Valoración estilo Peter Lynch (lo que este tipo de inversor SÍ aporta)
    per_estimado        REAL,            -- PER a 12 meses
    crecimiento_eps_pct REAL,            -- crecimiento esperado de beneficios (%)
    peg_ratio           REAL,            -- per_estimado / crecimiento_eps_pct
    precio_objetivo     REAL,            -- casi siempre NULL en este tipo de contenido
    precio_mencionado   REAL,            -- precio del que hablaba en ese momento

    confianza           TEXT,            -- 'alta' | 'media' | 'baja'
    argumento           TEXT,            -- una frase: la razón principal
    cita_textual        TEXT,            -- fragmento LITERAL que respalda la mención (anti-alucinación)

    UNIQUE(video_id, ticker)             -- una postura por activo por video
);

CREATE INDEX IF NOT EXISTS idx_menciones_ticker ON menciones(ticker);
CREATE INDEX IF NOT EXISTS idx_menciones_fecha  ON menciones(fecha);
CREATE INDEX IF NOT EXISTS idx_menciones_tipo   ON menciones(tipo_mencion);

-- ============================================================================
-- precios — datos REALES de mercado (NO los toca el LLM)
-- ============================================================================
-- Se llenan desde una API (yfinance, Alpha Vantage...). Cruzando precios con
-- menciones por (ticker, fecha) se mide si el inversor acertó.
CREATE TABLE IF NOT EXISTS precios (
    ticker   TEXT NOT NULL REFERENCES activos(ticker),
    fecha    TEXT NOT NULL,              -- 'YYYY-MM-DD'
    cierre   REAL NOT NULL,
    volumen  INTEGER,
    PRIMARY KEY (ticker, fecha)
);

-- ============================================================================
-- Consultas de ejemplo (capa 4 — análisis, sin LLM)
-- ============================================================================
-- Evolución de la postura sobre un activo en el tiempo:
--   SELECT fecha, postura, peg_ratio FROM menciones
--   WHERE ticker = 'AMZN' AND tipo_mencion = 'idea_activa'
--   ORDER BY fecha;
--
-- Ideas activas más baratas según PEG en las últimas 8 semanas:
--   SELECT ticker, fecha, peg_ratio, argumento FROM menciones
--   WHERE tipo_mencion = 'idea_activa' AND peg_ratio IS NOT NULL
--     AND fecha >= date('now','-56 days')
--   ORDER BY peg_ratio ASC;
--
-- Acierto: rendimiento a 30 días tras una recomendación de 'comprar'
--   SELECT m.ticker, m.fecha, p0.cierre AS precio_dia,
--          p1.cierre AS precio_30d,
--          round((p1.cierre - p0.cierre) / p0.cierre * 100, 1) AS rend_pct
--   FROM menciones m
--   JOIN precios p0 ON p0.ticker = m.ticker AND p0.fecha = m.fecha
--   JOIN precios p1 ON p1.ticker = m.ticker AND p1.fecha = date(m.fecha,'+30 days')
--   WHERE m.postura = 'comprar' AND m.tipo_mencion = 'idea_activa';
