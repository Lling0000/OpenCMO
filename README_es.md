<div align="center">
  <img src="assets/logo.png" alt="OpenCMO" width="80" />
  <h1>OpenCMO</h1>
  <p><strong>Tu espacio de trabajo de crecimiento con IA, de código abierto.</strong></p>
  <p>Descubre dónde encuentran tu producto, qué dicen de él<br />y qué acciones de crecimiento conviene emprender después.</p>
  <p>
    <a href="README.md">English</a> · <a href="README_zh.md">中文</a> · <a href="README_ja.md">日本語</a> · <a href="README_ko.md">한국어</a> · <a href="README_es.md">Español</a>
  </p>
  <p>
    <a href="https://github.com/Lling0000/OpenCMO/actions/workflows/ci.yml"><img src="https://github.com/Lling0000/OpenCMO/actions/workflows/ci.yml/badge.svg" alt="CI" /></a>
    <img src="https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&amp;logoColor=white" alt="Python 3.10+" />
    <img src="https://img.shields.io/badge/React-19-149ECA?logo=react&amp;logoColor=white" alt="React 19" />
    <img src="https://img.shields.io/badge/Models-BYOK-7C3AED" alt="Usa tus propias claves de modelos" />
  </p>
  <p><a href="#qué-hace-opencmo">Descripción</a> · <a href="#inicio-rápido">Inicio rápido</a> · <a href="docs/rag.md">Conocimiento y RAG</a> · <a href="docs/configuration.md">Configuración</a></p>
</div>

<p align="center">
  <img src="assets/readme-overview.svg" alt="Flujo de OpenCMO: proyecto, seguimiento, contexto compartido, análisis con IA y revisión humana" width="100%" />
</p>

## Qué hace OpenCMO

OpenCMO es un director de marketing con IA, alojado en tu propia infraestructura, para fundadores, responsables de proyectos de código abierto y pequeños equipos de producto. Conecta la visibilidad en buscadores, las conversaciones de comunidades, la investigación de competidores y tus propios documentos en un único espacio de trabajo por proyecto.

Empieza con la URL de un producto. OpenCMO construye el contexto del proyecto, recopila señales y utiliza agentes especializados para convertirlas en informes, borradores de contenido y recomendaciones priorizadas. Los análisis programados permiten seguir los cambios a lo largo del tiempo; una cola de aprobación mantiene las decisiones de publicación en tus manos.

| Función | Qué puedes hacer |
| --- | --- |
| **SEO y posiciones en buscadores** | Auditar el estado técnico del sitio, comprobar el acceso de rastreadores de IA y seguir la evolución de las posiciones de palabras clave. |
| **Visibilidad en búsquedas con IA (GEO)** | Examinar menciones y citas de la marca mediante proveedores de IA compatibles; la cobertura depende de las integraciones configuradas. |
| **Comunidades y competidores** | Encontrar conversaciones relevantes, seguir menciones y explorar competidores, palabras clave y conversaciones en un grafo de conocimiento. |
| **Biblioteca de conocimiento (RAG)** | Recuperar información de tus documentos e informes anteriores, con citas de las fuentes en chats, informes y borradores. |
| **Informes y chat con IA** | Generar informes estratégicos y resúmenes semanales, obtener un Human Readout y un Agent Brief, o comentar los resultados con agentes que conocen el proyecto. |
| **Contenido y aprobaciones** | Preparar borradores de contenido y mensajes de contacto, revisar las acciones propuestas y activar las integraciones de publicación compatibles cuando estés listo. |

**Usa tu propio modelo.** Configura OpenAI o un endpoint compatible con OpenAI, un modelo que admita llamadas a herramientas y una clave de API. Las integraciones opcionales de búsqueda, comunidades y publicación amplían el espacio de trabajo según tus necesidades.

La publicación directa admite Reddit y Twitter/X cuando se configuran las credenciales de la plataforma y `OPENCMO_AUTO_PUBLISH=1`. Los demás mensajes de contacto se conservan como borradores para revisión.

## De una URL a un plan de acción

1. **Construir el contexto** — rastrear la URL del producto y analizar su marca, categoría, palabras clave y competidores.
2. **Recopilar señales** — reunir datos de SEO, búsquedas con IA, posiciones de palabras clave y comunidades mediante los proveedores disponibles.
3. **Revisar los resultados en conjunto** — normalizar los resultados y dejar que los agentes especializados analicen cada área y sinteticen las prioridades.
4. **Generar resultados** — guardar los hallazgos, generar informes y briefs, y preparar acciones para su revisión.
5. **Mantener el seguimiento** — programar análisis diarios, semanales o mensuales y comparar los nuevos resultados con ejecuciones anteriores.

El flujo de seguimiento tiene seis etapas: construcción del contexto → recopilación de señales → normalización → revisión por área → síntesis estratégica → persistencia. Los informes, el chat y los borradores reutilizan el contexto del proyecto, sin necesidad de explicar el producto cada vez.

## Inicio rápido

### Docker Compose

Docker compila la interfaz web y el backend juntos. Instala Docker con Compose y ejecuta:

```bash
git clone https://github.com/Lling0000/OpenCMO.git
cd OpenCMO
cp .env.example .env
```

Edita `.env` y asigna a `OPENAI_API_KEY` la clave de tu proveedor de modelos. Para un proveedor compatible, configura también `OPENAI_BASE_URL` y `OPENCMO_MODEL_DEFAULT`; encontrarás ejemplos en la [guía de configuración](docs/configuration.md).

```bash
docker compose up -d --build
```

Abre **[http://localhost:8080](http://localhost:8080)**, crea un proyecto a partir de su URL y ejecuta el primer análisis. También puedes configurar los modelos desde la interfaz web.

<details>
<summary><strong>Ejecutar desde el código fuente</strong> — Python 3.10+ y Node.js 20+</summary>

```bash
git clone https://github.com/Lling0000/OpenCMO.git
cd OpenCMO
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[all]"
crawl4ai-setup
cp .env.example .env
```

Configura la clave del modelo en `.env`, compila el frontend e inicia el servidor:

```bash
cd frontend
npm ci
npm run build
cd ..
opencmo-web
```

Abre `http://localhost:8080`. Es necesario compilar el frontend para usar la interfaz web.

</details>

### Tu primer proyecto

- Añade la URL del producto o del repositorio y revisa el contexto detectado.
- Ejecuta un análisis y examina los resultados sobre búsquedas, comunidades y competidores.
- Pide al chat con IA que explique un hallazgo o genere un informe estratégico.
- Añade documentos fuente si quieres respuestas basadas en tu propio conocimiento.
- Revisa los borradores y las recomendaciones, y programa el siguiente análisis.

## Conocimiento basado en tus fuentes

La biblioteca de conocimiento opcional admite PDF con texto, DOCX, Markdown, TXT, texto pegado, páginas web públicas e informes anteriores. Combina **recuperación de vectores densos con Qdrant, BM25, recuperación por títulos y entidades, fusión de rankings y reranking**, e incorpora el contexto circundante y las citas de las fuentes en los resultados generados.

```bash
# Activa la aplicación y la base de datos vectorial opcional.
docker compose --profile rag up -d --build
```

En **Biblioteca de conocimiento → Modelos y recuperación**, configura los proveedores de embeddings y reranking, prueba las conexiones y activa la recuperación. Sube una fuente y espera a que termine la indexación antes de consultarla.

Los documentos son privados para cada proyecto de forma predeterminada. Compartir entre cuentas y permitir el uso de una fuente en contenido público son ajustes independientes. Consulta la [guía de RAG](docs/rag.md) para conocer la configuración, los permisos, las API y la evaluación de proveedores.

## Arquitectura y desarrollo

![Arquitectura de software de OpenCMO](docs/assets/architecture.png)

| Capa | Tecnologías |
| --- | --- |
| Interfaz web | React 19 · TypeScript · Vite · TanStack Query |
| API y orquestación | FastAPI · OpenAI Agents SDK |
| Trabajo en segundo plano | Workers de análisis, informes, expansión de grafos e indexación del conocimiento |
| Almacenamiento y recuperación | SQLite / FTS5 · Qdrant opcional |
| Recopilación | Crawl4AI · proveedores de búsqueda y específicos de cada plataforma |

```text
frontend/src/              Interfaz web, vistas de proyectos y configuración
src/opencmo/agents/         CMO y agentes especializados
src/opencmo/tools/          Rastreo, búsqueda, auditorías e integraciones de plataformas
src/opencmo/services/       Análisis del proyecto y flujos de aprobación
src/opencmo/background/     Ejecución de tareas y seguimiento del progreso
src/opencmo/rag/            Ingesta, recuperación híbrida y citas de fuentes
src/opencmo/storage/        Persistencia con SQLite
src/opencmo/web/            Rutas de API y autenticación
```

<details>
<summary><strong>Comandos de desarrollo</strong></summary>

Tras instalar las dependencias del código fuente:

```bash
pip install pytest pytest-asyncio ruff
pytest tests/
ruff check src/ tests/

cd frontend
npm ci
npm run dev
```

El servidor de desarrollo de Vite se ejecuta en `http://localhost:5173` y redirige las solicitudes de API al backend en el puerto `8080`.

</details>

## Documentación

- [Arquitectura](docs/architecture.md) — componentes y flujos de datos (en chino).
- [Revisión de optimización](docs/optimization-review.md) — mejoras, mediciones y prioridades pendientes (en chino).
- [Configuración](docs/configuration.md) — proveedores de modelos e integraciones opcionales.
- [Despliegue](docs/deployment.md) — alojamiento, almacenamiento persistente y copias de seguridad.
- [Conocimiento y RAG](docs/rag.md) — ingesta de documentos, recuperación y citas.
- [Validación de RAG](docs/rag-validation.md) — alcance de las pruebas, mediciones de capacidad y estado de la evaluación.
- [Contribuir](CONTRIBUTING.md) — flujo de desarrollo y reconocimiento de contribuciones.

Mantenido por **[Ling (`Lling0000`)](https://github.com/Lling0000)**. Las contribuciones históricas se recogen en [CONTRIBUTORS.md](CONTRIBUTORS.md).

## Comunidad

[LINUX DO](https://linux.do/) — Una comunidad para entusiastas de la tecnología
