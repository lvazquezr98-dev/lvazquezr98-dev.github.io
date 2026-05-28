# CLAUDE.md — Guía para Claude Code

Este archivo lo lees automáticamente al iniciar cada sesión. Define cómo trabajar en este proyecto. Manténlo corto, vivo y actualizado: cuando una corrección se repita, anótala aquí.

## Sobre el proyecto

**Portafolio profesional** de Luis Reyes (desarrollador web, egresado del bootcamp TripleTen).
Sitio estático publicado vía GitHub Pages en `https://lvazquezr98-dev.github.io`.

## Stack

- HTML5 semántico
- CSS3 puro (sin frameworks, sin preprocesadores)
- Sin JavaScript todavía (agregar solo si una funcionalidad lo requiere de verdad)
- Publicación: GitHub Pages desde la rama `main`

## Estructura del proyecto

```
.
├── index.html         # Página principal (única por ahora)
├── css/
│   └── styles.css     # Todos los estilos (BEM + variables CSS en :root)
├── images/            # Imágenes y miniaturas
├── README.md
└── CLAUDE.md          # Este archivo
```

## Cómo correr el sitio localmente

El sitio es estático, no requiere build. Para preview:

```bash
# Opción recomendada: servidor local (evita problemas de rutas relativas)
python3 -m http.server 8000
# Abrir luego http://localhost:8000
```

## Convenciones (reglas duras)

1. **CSS con metodología BEM:** `bloque__elemento--modificador`. Ej: `project-card__title`, `btn--primary`.
2. **Variables CSS en `:root`** para colores, sombras y tipografía. No hardcodear colores en componentes.
3. **HTML semántico:** usar `<section>`, `<article>`, `<nav>`, `<footer>`, `<header>`. Evitar `<div>` cuando exista una etiqueta más expresiva.
4. **Accesibilidad:**
   - Todas las imágenes con `alt` descriptivo.
   - Enlaces externos con `target="_blank"` deben llevar `rel="noopener noreferrer"`.
   - Contraste de color suficiente (WCAG AA).
5. **Mobile-first:** los estilos base son para móvil; usar `@media (min-width: ...)` para escalar a pantallas más grandes.
6. **Idioma:** todo el contenido visible y los comentarios en español. Atributo `lang="es"` en el `<html>`.
7. **Sin librerías externas** sin discusión previa.

## Flujo de trabajo Git

- Toda nueva tarea va en una rama: `feature/<nombre-corto>` o `fix/<nombre-corto>`.
- Commits pequeños y descriptivos en español. Ejemplos:
  - `feat: agregar sección de testimonios`
  - `fix: corregir alineación del navbar en móvil`
  - `docs: actualizar README`
- **Nunca commitear directo a `main`.** Cambios entran por Pull Request.
- Antes de cualquier cambio no trivial: **propón un plan y espera aprobación**.

## Cómo trabajar conmigo en este proyecto

Luis está aprendiendo a programar mientras construye. Por eso:

- **Explica las decisiones** brevemente al escribir código nuevo.
- **No introduzcas conceptos nuevos** (un framework, una herramienta) sin justificarlos primero.
- **Cuando Luis pregunte "¿por qué?"**, responde a nivel principiante, con un ejemplo concreto.
- **Si algo se vuelve enredado**, sugiere refactorizar en lugar de seguir parchando.
- **Antes de marcar una tarea como terminada**, abre el sitio y verifica visualmente que se ve y se comporta como debe.

## Qué NO hacer

- No añadir JavaScript ni librerías para resolver algo que CSS puro puede hacer.
- No reescribir secciones grandes sin que se haya pedido (cambios mínimos y enfocados).
- No tocar la rama `main` directamente.
- No commitear imágenes pesadas sin optimizarlas primero (>500KB es señal de alerta).
- No "alucinar" que algo funciona: validar siempre con el sitio abierto en el navegador.
