<div align="center">
  <img src="assets/logo.png" alt="OpenCMO" width="80" />
  <h1>OpenCMO</h1>
  <p><strong>오픈 소스 AI 성장 워크스페이스.</strong></p>
  <p>제품이 어디에서 발견되고 사람들이 어떤 이야기를 하는지 파악하고,<br />다음에 실행할 성장 전략을 정하세요.</p>
  <p>
    <a href="README.md">English</a> · <a href="README_zh.md">中文</a> · <a href="README_ja.md">日本語</a> · <a href="README_ko.md">한국어</a> · <a href="README_es.md">Español</a>
  </p>
  <p>
    <a href="https://github.com/Lling0000/OpenCMO/actions/workflows/ci.yml"><img src="https://github.com/Lling0000/OpenCMO/actions/workflows/ci.yml/badge.svg" alt="CI" /></a>
    <img src="https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&amp;logoColor=white" alt="Python 3.10+" />
    <img src="https://img.shields.io/badge/React-19-149ECA?logo=react&amp;logoColor=white" alt="React 19" />
    <img src="https://img.shields.io/badge/Models-BYOK-7C3AED" alt="자신의 모델 API 키 사용" />
  </p>
  <p><a href="#opencmo로-할-수-있는-일">개요</a> · <a href="#빠른-시작">빠른 시작</a> · <a href="docs/rag.md">지식과 RAG</a> · <a href="docs/configuration.md">설정</a></p>
</div>

<p align="center">
  <img src="assets/readme-overview.svg" alt="OpenCMO 워크플로: 프로젝트, 모니터링, 공유 컨텍스트, AI 분석, 사람의 검토" width="100%" />
</p>

## OpenCMO로 할 수 있는 일

OpenCMO는 창업자, 오픈 소스 관리자, 소규모 제품 팀을 위한 셀프 호스팅 AI CMO(최고 마케팅 책임자)입니다. 검색 노출, 커뮤니티 대화, 경쟁사 조사, 자체 문서를 하나의 프로젝트 워크스페이스에서 연결합니다.

제품 URL로 시작하세요. OpenCMO는 프로젝트 컨텍스트를 구성하고 신호를 수집하며, 전문 에이전트를 통해 보고서, 콘텐츠 초안, 우선순위가 정해진 제안을 만듭니다. 정기 스캔으로 시간에 따른 변화를 추적하고, 승인 대기열에서 게시 여부를 직접 결정할 수 있습니다.

| 기능 | 할 수 있는 일 |
| --- | --- |
| **SEO와 검색 순위** | 사이트의 기술적 상태를 점검하고, AI 크롤러의 접근 가능 여부를 확인하며, 키워드 순위 변화를 추적합니다. |
| **AI 검색 노출(GEO)** | 지원되는 AI 제공자를 통해 브랜드 언급과 인용을 조사합니다. 지원 범위는 설정된 연동에 따라 달라집니다. |
| **커뮤니티와 경쟁사** | 관련 대화를 찾고 언급을 추적하며, 지식 그래프에서 경쟁사, 키워드, 대화의 관계를 탐색합니다. |
| **지식 라이브러리(RAG)** | 문서와 과거 보고서를 검색하고, 채팅·보고서·초안에 출처 인용과 함께 활용합니다. |
| **보고서와 AI 채팅** | 전략 보고서, 주간 요약, Human Readout과 Agent Brief를 생성하거나, 프로젝트를 이해하는 에이전트와 조사 결과를 논의합니다. |
| **콘텐츠와 승인** | 콘텐츠와 아웃리치 초안을 준비하고, 제안된 활동을 검토한 뒤 준비가 되면 지원되는 게시 연동을 활성화합니다. |

**자신의 모델을 사용하세요.** OpenAI 또는 OpenAI 호환 엔드포인트, 도구 호출을 지원하는 모델, API 키를 설정합니다. 검색, 커뮤니티, 게시 연동은 필요에 따라 추가할 수 있습니다.

플랫폼 자격 증명과 `OPENCMO_AUTO_PUBLISH=1`을 설정하면 Reddit과 Twitter/X에 직접 게시할 수 있습니다. 그 외 아웃리치 결과물은 검토용 초안으로 유지됩니다.

## 하나의 URL에서 실행 계획까지

1. **컨텍스트 구성** — 제품 URL을 크롤링하고 브랜드, 카테고리, 키워드, 경쟁사를 분석합니다.
2. **신호 수집** — 사용 가능한 제공자를 통해 SEO, AI 검색, 키워드 순위, 커뮤니티 데이터를 수집합니다.
3. **결과 통합 검토** — 결과를 정규화한 뒤 전문 에이전트가 각 영역을 분석하고 우선순위를 종합합니다.
4. **결과물 생성** — 조사 결과를 저장하고 보고서와 브리프를 생성하며, 검토할 활동을 준비합니다.
5. **지속적인 모니터링** — 일간, 주간, 월간 스캔을 예약하고 새 결과를 이전 실행 결과와 비교합니다.

모니터링 파이프라인은 컨텍스트 구성 → 신호 수집 → 정규화 → 영역별 검토 → 전략 종합 → 저장의 6단계로 구성됩니다. 보고서, 채팅, 초안은 프로젝트 컨텍스트를 재사용하므로 매번 제품을 다시 설명할 필요가 없습니다.

## 빠른 시작

### Docker Compose

Docker는 웹 인터페이스와 백엔드를 함께 빌드합니다. Compose가 포함된 Docker를 설치한 뒤 다음을 실행하세요.

```bash
git clone https://github.com/Lling0000/OpenCMO.git
cd OpenCMO
cp .env.example .env
```

`.env`를 편집하고 `OPENAI_API_KEY`에 모델 제공자의 키를 설정하세요. 호환 제공자를 사용하는 경우 `OPENAI_BASE_URL`과 `OPENCMO_MODEL_DEFAULT`도 설정하세요. 예시는 [설정 가이드](docs/configuration.md)에 있습니다.

```bash
docker compose up -d --build
```

**[http://localhost:8080](http://localhost:8080)**을 열고 URL로 프로젝트를 만든 뒤 첫 스캔을 실행하세요. 웹 인터페이스에서도 모델을 설정할 수 있습니다.

<details>
<summary><strong>소스에서 실행</strong> — Python 3.10+와 Node.js 20+</summary>

```bash
git clone https://github.com/Lling0000/OpenCMO.git
cd OpenCMO
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[all]"
crawl4ai-setup
cp .env.example .env
```

`.env`에서 모델 API 키를 설정한 뒤 프론트엔드를 빌드하고 서버를 시작하세요.

```bash
cd frontend
npm ci
npm run build
cd ..
opencmo-web
```

`http://localhost:8080`을 여세요. 웹 인터페이스를 사용하려면 프론트엔드 빌드가 필요합니다.

</details>

### 첫 프로젝트

- 제품 또는 저장소 URL을 추가하고 감지된 프로젝트 컨텍스트를 검토하세요.
- 스캔을 실행하고 검색, 커뮤니티, 경쟁사 조사 결과를 살펴보세요.
- AI 채팅에 결과 설명이나 전략 보고서 생성을 요청하세요.
- 자체 지식에 기반한 답변을 원한다면 원본 문서를 추가하세요.
- 초안과 제안을 검토하고 다음 스캔을 예약하세요.

## 자체 자료에 근거한 지식 활용

선택적으로 사용하는 지식 라이브러리는 텍스트가 포함된 PDF, DOCX, Markdown, TXT, 붙여넣은 텍스트, 공개 웹 페이지, 과거 보고서를 지원합니다. **Qdrant 밀집 벡터 검색, BM25, 제목·엔터티 기반 후보 검색, 순위 융합, 재순위화**를 결합하고, 주변 컨텍스트와 출처 인용을 생성 결과에 반영합니다.

```bash
# 앱과 선택 사항인 벡터 데이터베이스를 활성화합니다.
docker compose --profile rag up -d --build
```

**지식 라이브러리 → 모델 및 검색**에서 임베딩과 재순위화 제공자를 설정하고 연결을 테스트한 뒤 검색을 활성화하세요. 자료를 업로드하고 인덱싱이 끝날 때까지 기다린 후 질의하세요.

문서는 기본적으로 프로젝트 내에서만 접근할 수 있습니다. 계정 간 공유와 공개 콘텐츠에 자료를 사용할 권한은 별도 설정입니다. 설정, 권한, API, 제공자 평가에 대한 내용은 [RAG 가이드](docs/rag.md)를 참고하세요.

## 아키텍처와 개발

| 계층 | 기술 스택 |
| --- | --- |
| 웹 인터페이스 | React 19 · TypeScript · Vite · TanStack Query |
| API와 오케스트레이션 | FastAPI · OpenAI Agents SDK |
| 백그라운드 작업 | 스캔, 보고서, 그래프 확장, 지식 인덱싱 워커 |
| 저장 및 검색 | SQLite / FTS5 · 선택 사항인 Qdrant |
| 데이터 수집 | Crawl4AI · 검색 및 플랫폼별 제공자 |

```text
frontend/src/              웹 인터페이스, 프로젝트 화면, 설정
src/opencmo/agents/         CMO와 전문 에이전트
src/opencmo/tools/          크롤링, 검색, 점검, 플랫폼 연동
src/opencmo/services/       프로젝트 분석과 승인 워크플로
src/opencmo/background/     작업 실행과 진행 상태
src/opencmo/rag/            수집, 하이브리드 검색, 출처 인용
src/opencmo/storage/        SQLite 영구 저장
src/opencmo/web/            API 라우트와 인증
```

<details>
<summary><strong>개발 명령어</strong></summary>

소스 의존성을 설치한 뒤 다음을 실행하세요.

```bash
pip install pytest pytest-asyncio ruff
pytest tests/
ruff check src/ tests/

cd frontend
npm ci
npm run dev
```

Vite 개발 서버는 `http://localhost:5173`에서 실행되며 API 요청을 포트 `8080`의 백엔드로 프록시합니다.

</details>

## 문서

- [설정](docs/configuration.md) — 모델 제공자와 선택적 연동.
- [배포](docs/deployment.md) — 호스팅, 영구 저장소, 백업.
- [지식과 RAG](docs/rag.md) — 문서 수집, 검색, 인용.
- [RAG 검증](docs/rag-validation.md) — 테스트 범위, 용량 측정, 평가 상태.
- [기여 가이드](CONTRIBUTING.md) — 개발 워크플로와 기여자 기록.

현재 관리자는 **[Ling (`Lling0000`)](https://github.com/Lling0000)**입니다. 과거 기여는 [CONTRIBUTORS.md](CONTRIBUTORS.md)에 기록되어 있습니다.

## 커뮤니티

[LINUX DO](https://linux.do/) — 기술 애호가들이 모이는 커뮤니티
