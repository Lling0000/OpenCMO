<div align="center">
  <img src="assets/logo.png" alt="OpenCMO Logo" width="120" />
</div>

<h1 align="center">OpenCMO</h1>

<p align="center">
  <strong>Pega tu URL → obtén un brief de AI CMO, monitoreo continuo y acciones listas para tus agentes.</strong><br/>
  <sub>AI CMO open source para founders y equipos pequeños. Unifica SEO, GEO, SERP, señales de comunidad, contexto competitivo, reportes, aprobaciones y publicación.</sub>
</p>

<div align="center">
  <a href="README.md">English</a> | <a href="README_zh.md">中文</a> | <a href="README_ja.md">日本語</a> | <a href="README_ko.md">한국어</a> | <a href="README_es.md">Español</a>
</div>

<p align="center">
  <a href="https://www.python.org/downloads/"><img src="https://img.shields.io/badge/python-3.10+-blue.svg?style=for-the-badge&logo=python" alt="Python 3.10+"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-Apache%202.0-green.svg?style=for-the-badge" alt="License"></a>
  <a href="https://github.com/study8677/OpenCMO/stargazers"><img src="https://img.shields.io/github/stars/study8677/OpenCMO?style=for-the-badge&color=yellow&logo=github" alt="Stars"></a>
  <img src="https://img.shields.io/badge/react-SPA-61DAFB.svg?style=for-the-badge&logo=react" alt="React SPA">
</p>

<div align="center">
  <h3>
    <a href="https://www.aidcmo.com/">Demo en vivo</a> · <a href="https://www.aidcmo.com/static/demo.mp4">Ver video</a>
  </h3>
</div>

<div align="center">
  <a href="https://www.aidcmo.com/">
    <img src="assets/screenshots/demo-cover.png" alt="OpenCMO en acción" width="850" />
  </a>
  <p><i>Un solo workspace para monitoreo, reportes, aprobaciones y contexto competitivo.</i></p>
</div>

<div align="center">
  <h3>Únete a la comunidad de OpenCMO</h3>
  <img src="assets/community-qr.png" alt="Código QR del grupo de WeChat de OpenCMO" width="240" />
  <p><i>¿Preguntas, ideas o comentarios? Escanea el QR con WeChat para unirte a nuestro grupo.</i></p>
</div>

---

## Ejemplos de Produccion Reales

OpenCMO se ejecuta a diario en proyectos reales. Dos escaneos en vivo muestran en que se convierte una sola URL.

### Coze — monitoreo de una plataforma global de agentes de IA

- **Competidores auto-descubiertos**: Dify, FastGPT, OpenAI GPTs
- **50 palabras clave** rastreadas (ej. `coze 和 dify 哪个好用`, `coze vs chatgpt custom gpts`)
- **326 instantaneas SERP** durante la ventana de monitoreo
- **100 discusiones de comunidad** — 61 en Hacker News, 29 en Bilibili, 10 en Dev.to
- **153 desarrolladores de GitHub** identificados como usuarios potenciales desde repos relacionados
- Detectado: *"Citability score cayo 24 puntos"* — regresion de visibilidad en busqueda IA, alertada en el siguiente escaneo programado

### DigiGrow — un SaaS britanico que compite con Checkatrade y Wix

- **54 palabras clave** rastreadas, **672 chequeos de ranking SERP**
- **100 discusiones de comunidad** (Hacker News, Dev.to, Bilibili, V2EX)
- **34 insights accionables** generados de extremo a extremo
- Detectado (critical): `digigrow.uk online marketing solutions` cayo de **#2 a #16 en 24 horas** (5/2 → 5/3) — convertido en insight accionable sin que nadie revisara el dashboard

> Prueba la [demo publica](https://www.aidcmo.com/) con tu propia URL — un escaneo, pipeline completo, numeros reales.

---

## Por Qué OpenCMO

- **Empieza desde una URL**: tras un full scan recibes una lectura de nivel CMO sobre posicionamiento y mercado.
- **Mantiene el loop de señales activo**: SEO, GEO, SERP y comunidad en un solo lugar.
- **Convierte insight en ejecución**: reportes, agent briefs, cola de aprobación y borradores publicables conectados.

## Qué Obtienes

- **Estrategia inicial**: posicionamiento, fortalezas, debilidades, competencia y recomendación CMO.
- **Monitoreo continuo**: salud SEO, visibilidad en buscadores IA, rankings de keywords y menciones de comunidad.
- **Contexto competitivo**: grafo de conocimiento 3D con competidores, keywords y comunidades.
- **Superficie de ejecución**: AI chat, aprobaciones y borradores para publicar.

## Reportes AI CMO

OpenCMO ya incluye un sistema formal de reportes dentro de cada proyecto. Abre la pestaña **Reports** o visita `/projects/<id>/reports`.

### Pipeline Multi-Agente de Reportes Profundos

Los reportes para personas se generan a través de un **pipeline de 6 fases multi-agente** (~14 llamadas LLM) en vez de un solo prompt. Esto produce análisis de nivel McKinsey con datos validados cruzadamente y control de calidad iterativo.

| Fase | Rol | Función |
| :--- | :--- | :--- |
| 1. Reflection Agent | Auditor de calidad | Valida cruzadamente datos de todos los Agents |
| 2. Insight Distiller | Analista | Extrae insights analíticos multi-dimensionales |
| 3. Outline Planner | Editor en Jefe | Diseña arco narrativo con tesis y evidencias |
| 4. Section Writers | Autores (paralelo) | Escriben secciones en paralelo |
| 5. Section Grader | Revisor | Puntua 1-5, rechaza y reintenta bajo umbral |
| 6. Report Synthesizer | Editor General | Escribe resumen ejecutivo, intro y estrategia |

- **Strategic Report**: tras un full scan — análisis competitivo profundo, evaluación de riesgos, recomendaciones estratégicas CMO.
- **Weekly Report**: ventana de 7 días — análisis de tendencias, riesgos/logros, plan de acción.
- **Salida dual**: **Human Readout** (análisis profundo) y **Agent Brief** (acciones concisas).
- **Exportar PDF**: descarga PDFs con logo de marca en header y footer.
- **Historial de versiones**: puedes ver latest e histórico.
- **Email**: el correo semanal reutiliza el mismo reporte persistido.
- **Fallback elegante**: fallos del pipeline degradan automáticamente a llamada única → plantilla.

## Qué Sucede al Pulsar "Iniciar Monitoreo"

Una URL activa un pipeline de IA de 6 etapas que construye un panorama completo de crecimiento:

| Etapa | Nombre | Qué hace |
|:-----:|--------|----------|
| 1/6 | **Context Build** | Rastrea tu URL. Tres especialistas IA (Analista de Producto, Estratega SEO, Estratega de Comunidad) debaten en 3 rondas para extraer marca, categoría, palabras clave y competidores. |
| 2/6 | **Signal Collect** | Ejecuta auditoría SEO, verificación de visibilidad GEO, búsqueda en comunidades (Reddit, HN, Dev.to, etc.) y rastreo de palabras clave SERP — todo en paralelo. |
| 3/6 | **Signal Normalize** | Limpia y estandariza datos brutos: deduplicación de discusiones, normalización de puntuaciones, alineación de registros de palabras clave y competidores. |
| 4/6 | **Domain Review** | Cuatro analistas IA revisan las señales de forma independiente: Analista SEO, GEO, Comunidad y Competencia. |
| 5/6 | **Strategy Synthesis** | Un Director de Estrategia IA sintetiza todas las revisiones en hallazgos priorizados y recomendaciones accionables. |
| 6/6 | **Persist & Publish** | Guarda resultados en la BD, genera informe estratégico, muestra insights en el dashboard. |

> Después del escaneo inicial, programa re-escaneos **diarios / semanales / mensuales** para rastrear cambios a lo largo del tiempo.

## Superficie Principal del Producto

- **SEO Audit**: Core Web Vitals, llms.txt, crawlers IA y salud técnica.
- **GEO Visibility**: seguimiento en ChatGPT, Claude, Gemini, Perplexity y You.com.
- **SERP Tracking**: evolución de rankings en el tiempo.
- **Community Monitoring**: Reddit, Hacker News, Dev.to, YouTube, Bluesky y Twitter/X.
- **AI Chat**: 25+ agentes especialistas con contexto del proyecto.
- **Approval Queue**: revisa antes de publicar.
- **3D Knowledge Graph**: explora competidores, keywords y comunidades.

## Inicio Rápido

Compatible con APIs tipo OpenAI, incluyendo OpenAI, DeepSeek, NVIDIA NIM, gateways compatibles con Kimi y Ollama.

```bash
git clone https://github.com/study8677/OpenCMO.git
cd OpenCMO
pip install -e ".[all]"
crawl4ai-setup

cp .env.example .env
opencmo-web
```

Luego abre `http://localhost:8080`.

Ingresa tu URL del proyecto en la página principal para ejecutar el primer escaneo. Si no hay clave de API LLM configurada, un punto rojo en el ícono de Settings te guiará al panel de configuración.

> Consejo: también puedes configurar las claves API desde el panel **Settings** del dashboard (sin tocar `.env`).

<details>
<summary>Desarrollo frontend (opcional)</summary>

```bash
cd frontend
npm install
npm run dev
npm run build
```

La app de desarrollo corre en `http://localhost:5173` y proxya la API a `:8080`.

</details>

## Integraciones

| Capacidad | Plataformas | Auth |
| :--- | :--- | :--- |
| Monitoreo | SEO, GEO, SERP, Community | Keys opcionales |
| Fuentes de comunidad | Reddit, HN, Dev.to, Bluesky, YouTube, Twitter/X | Opcional |
| Publicación | Reddit, Twitter/X | Obligatoria |
| Reportes | Web + Email + PDF | SMTP para email |
| LLM | APIs compatibles con OpenAI | Obligatoria |

## Roadmap

- [x] Escaneo estratégico AI CMO
- [x] Monitoreo SEO / GEO / SERP / comunidad
- [x] Reportes estratégicos y semanales versionados
- [x] Pipeline multi-agente de reportes profundos (6 fases)
- [x] Exportar PDF con marca
- [x] Grafo de conocimiento 3D
- [x] Aprobaciones y publicación controlada
- [x] Monitoreo de comunidades en plataformas chinas (V2EX, Weibo, Bilibili, XueQiu)
- [x] i18n completo (inglés, chino, japonés, coreano, español)
- [x] Respuestas IA según el idioma (el LLM sigue la configuración de idioma de la UI)
- [x] Reintentos LLM con backoff exponencial para proveedores inestables
- [x] Onboarding simplificado: ingresa tu URL en la página principal, sin configuración previa
- [ ] Más destinos de publicación
- [ ] Control de brand voice
- [ ] Crawls SEO enterprise más profundos

## Contributors

- [study8677](https://github.com/study8677) - Creador y maintainer
- [Lling0000](https://github.com/Lling0000) - Principal contribuyente
- [ParakhJaggi](https://github.com/ParakhJaggi) - Integración Tavily ([#2](https://github.com/study8677/OpenCMO/pull/2), [#3](https://github.com/study8677/OpenCMO/pull/3))
- [BBear0115](https://github.com/BBear0115) - Corrección de bugs en aislamiento de claves BYOK, normalización de base_url e informes ([#9](https://github.com/study8677/OpenCMO/pull/9))
- Ver [CONTRIBUTORS.md](CONTRIBUTORS.md) para la lista completa

## Acknowledgments

- [geo-seo-claude](https://github.com/zubair-trabzada/geo-seo-claude) by [@zubair-trabzada](https://github.com/zubair-trabzada)
- [last30days-skill](https://github.com/mvanhorn/last30days-skill) by [@mvanhorn](https://github.com/mvanhorn)

## Star History

<a href="https://star-history.com/#study8677/OpenCMO&Date">
 <picture>
   <source media="(prefers-color-scheme: dark)" srcset="https://api.star-history.com/svg?repos=study8677/OpenCMO&type=Date&theme=dark" />
   <source media="(prefers-color-scheme: light)" srcset="https://api.star-history.com/svg?repos=study8677/OpenCMO&type=Date" />
   <img alt="Star History Chart" src="https://api.star-history.com/svg?repos=study8677/OpenCMO&type=Date" width="100%" />
 </picture>
</a>

## Enlaces

- [LINUX DO](https://linux.do/) — Donde se reúnen los entusiastas de la tecnología
