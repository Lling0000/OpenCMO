<div align="center">
  <img src="assets/logo.png" alt="OpenCMO Logo" width="120" />
</div>

<h1 align="center">OpenCMO</h1>

<p align="center">
  <strong>URL만 붙여넣으면 → AI CMO 전략 판단, 지속 모니터링, Agent Brief를 바로 받습니다.</strong><br/>
  <sub>창업자와 소규모 팀을 위한 오픈소스 AI CMO. SEO, GEO, SERP, 커뮤니티 신호, 경쟁 맥락, 리포트, 승인, 발행을 하나의 워크스페이스에 모읍니다.</sub>
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
    <a href="https://www.aidcmo.com/">라이브 데모</a> · <a href="https://www.aidcmo.com/static/demo.mp4">영상 보기</a>
  </h3>
</div>

<div align="center">
  <a href="https://www.aidcmo.com/">
    <img src="assets/screenshots/demo-cover.png" alt="OpenCMO 실행 화면" width="850" />
  </a>
  <p><i>모니터링, 리포트, 승인, 경쟁 맥락을 하나의 화면에서 봅니다.</i></p>
</div>

<div align="center">
  <h3>OpenCMO 커뮤니티 참여</h3>
  <img src="assets/community-qr.png" alt="OpenCMO WeChat 그룹 QR 코드" width="240" />
  <p><i>질문, 아이디어, 피드백이 있으신가요? WeChat으로 QR을 스캔해 그룹에 참여하세요.</i></p>
</div>

---

## 실제 프로덕션 사례

OpenCMO는 매일 실제 프로젝트에서 실행됩니다. 두 개의 라이브 스캔이 URL 하나가 어떤 결과로 이어지는지 보여줍니다.

### Coze — 글로벌 AI 에이전트 플랫폼 모니터링

- **자동 발견된 경쟁사**: Dify, FastGPT, OpenAI GPTs
- **50개 키워드** 추적 (예: `coze 和 dify 哪个好用`, `coze vs chatgpt custom gpts`)
- 모니터링 기간 동안 **326건 SERP 스냅샷**
- **100건 커뮤니티 토론** — Hacker News 61, Bilibili 29, Dev.to 10
- 관련 저장소에서 **153명 GitHub 개발자**를 잠재 사용자로 식별
- 자동 감지: *"Citability 점수 24점 하락"* — AI 검색 가시성 회귀가 다음 정기 스캔에서 자동 경고

### DigiGrow — Checkatrade와 Wix와 경쟁하는 영국 SaaS

- **54개 키워드** 추적, **672건 SERP 순위 체크**
- **100건 커뮤니티 토론** (Hacker News, Dev.to, Bilibili, V2EX)
- 엔드투엔드로 **34건의 실행 가능한 인사이트** 생성
- 자동 감지(critical): `digigrow.uk online marketing solutions`이 24시간 만에 **#2에서 #16으로 하락** (5/2 → 5/3) — 아무도 대시보드를 폴링하지 않은 상태에서 실행 가능한 인사이트로 푸시

> [공개 데모](https://www.aidcmo.com/)에서 자신의 URL로 시도해 보세요 — 1회 스캔, 전체 파이프라인, 실제 수치.

---

## 왜 OpenCMO인가

- **URL에서 바로 시작**: full scan 이후 CMO 수준의 시장 판단을 먼저 받습니다.
- **신호를 한곳에서 본다**: SEO, GEO, SERP, 커뮤니티 변화를 함께 추적합니다.
- **판단을 실행으로 연결**: 리포트, Agent Brief, 승인 큐, 발행 초안이 이어집니다.

## 실제로 얻는 것

- **전략 판단**: 포지셔닝, 강점, 약점, 경쟁 구도, CMO 제안.
- **지속 모니터링**: SEO 건강도, AI 검색 가시성, 키워드 순위, 커뮤니티 언급.
- **경쟁 맥락**: 경쟁사, 키워드, 커뮤니티를 잇는 3D 지식 그래프.
- **실행 표면**: AI Chat, 승인 흐름, 발행 가능한 초안.

## AI CMO 리포트

OpenCMO에는 프로젝트별 정식 리포트 시스템이 있습니다. **Reports** 탭 또는 `/projects/<id>/reports` 에서 확인할 수 있습니다.

### 멀티 에이전트 딕 리포트 파이프라인

인간용 리포트는 단일 프롬프트 대신 **6단계 멀티 에이전트 파이프라인**(약 14회 LLM 호출)으로 생성됩니다.

| 단계 | 역할 | 기능 |
| :--- | :--- | :--- |
| 1. Reflection Agent | 품질 감사관 | 모든 Agent 데이터 교차 검증, 이상값 탐지 |
| 2. Insight Distiller | 분석가 | 다차원 분석 인사이트 추출 |
| 3. Outline Planner | 편집장 | 논지와 증거 매핑으로 서사 구조 설계 |
| 4. Section Writers | 저자 (병렬) | 각 섹션을 병렬 작성 |
| 5. Section Grader | 심사자 | 1-5점 채점, 임계값 미달 시 재작성 |
| 6. Report Synthesizer | 총편집 | 요약, 서론, 전략 제안 작성 |

- **Strategic Report**: full scan 이후 생성 — 심층 경쟁 분석, 리스크 평가, CMO 수준 전략 제안.
- **Weekly Report**: 최근 7일 모니터링 윈도우 — 트렌드 분석, 리스크/성과, 다음 주 액션 계획.
- **이중 출력**: **Human Readout**(심층 분석)과 **Agent Brief**(간결한 액션 항목).
- **PDF 내보내기**: 브랜드 로고 헤더/푸터 포함 PDF 다운로드.
- **버전 히스토리**: latest 와 과거 버전을 함께 확인할 수 있습니다.
- **이메일 재사용**: 주간 이메일은 화면에 보이는 동일한 저장 리포트를 그대로 사용합니다.
- **우아한 폴백**: 파이프라인 장애 시 자동으로 싱글 콜 → 템플릿 생성으로 강등.

## "모니터링 시작"을 누르면 무슨 일이 일어나나요

하나의 URL로 6단계 AI 파이프라인이 시작되어 완전한 성장 분석을 구축합니다:

| 단계 | 이름 | 내용 |
|:----:|------|------|
| 1/6 | **Context Build** | URL을 크롤링. 3명의 AI 전문가(제품 분석가, SEO 전략가, 커뮤니티 전략가)가 3라운드 토론으로 브랜드명, 카테고리, 키워드, 경쟁사를 추출. |
| 2/6 | **Signal Collect** | SEO 감사, GEO 가시성 확인, 커뮤니티 검색(Reddit, HN, Dev.to 등), SERP 키워드 추적을 병렬 실행. |
| 3/6 | **Signal Normalize** | 원시 데이터 정리 및 표준화: 토론 중복 제거, 점수 정규화, 키워드 및 경쟁사 레코드 정렬. |
| 4/6 | **Domain Review** | 4명의 AI 분석가가 독립적으로 신호 검토: SEO, GEO, 커뮤니티, 경쟁사 분석가. |
| 5/6 | **Strategy Synthesis** | AI 전략 디렉터가 모든 검토를 종합하여 우선순위별 발견 사항과 실행 가능한 권장 사항 생성. |
| 6/6 | **Persist & Publish** | 결과를 DB에 저장, 전략 보고서 생성, 대시보드에 인사이트 표시. |

> 첫 스캔 후 **매일 / 매주 / 매월** 재스캔을 예약하여 변화를 지속 추적할 수 있습니다.

## 핵심 제품 면

- **SEO Audit**: Core Web Vitals, llms.txt, AI crawler 탐지, 기술 건강도.
- **GEO Visibility**: ChatGPT, Claude, Gemini, Perplexity, You.com 등에서의 노출 추적.
- **SERP Tracking**: 키워드 순위 변화를 장기 추적.
- **Community Monitoring**: Reddit, Hacker News, Dev.to, YouTube, Bluesky, Twitter/X 모니터링.
- **AI Chat**: 25개 이상의 전문 에이전트와 프로젝트 맥락 기반 대화.
- **Approval Queue**: 발행 전에 먼저 검토.
- **3D Knowledge Graph**: 경쟁사, 키워드, 커뮤니티를 시각적으로 탐색.

## 빠른 시작

OpenAI 호환 API를 지원합니다. OpenAI, DeepSeek, NVIDIA NIM, Kimi 호환 게이트웨이, Ollama 등을 사용할 수 있습니다.

```bash
git clone https://github.com/study8677/OpenCMO.git
cd OpenCMO
pip install -e ".[all]"
crawl4ai-setup

cp .env.example .env
opencmo-web
```

그다음 `http://localhost:8080` 을 엽니다.

홈페이지에서 URL을 입력해 첫 번째 스캔을 시작하세요. LLM API 키가 설정되지 않은 경우 Settings 아이콘의 빨간 점이 설정 패널로 안내합니다.

> 팁: API 키는 Web 대시보드의 **Settings** 에서도 직접 설정할 수 있습니다 (`.env` 불필요).

<details>
<summary>프론트엔드 개발 (선택)</summary>

```bash
cd frontend
npm install
npm run dev
npm run build
```

개발 앱은 `http://localhost:5173` 에서 실행되고 API는 `:8080` 으로 프록시됩니다.

</details>

## 연동

| 기능 | 플랫폼 | 인증 |
| :--- | :--- | :--- |
| 모니터링 | SEO, GEO, SERP, Community | 선택적 provider key |
| 커뮤니티 소스 | Reddit, HN, Dev.to, Bluesky, YouTube, Twitter/X | 선택 |
| 발행 | Reddit, Twitter/X | 필수 |
| 리포트 | Web + Email + PDF | 이메일은 SMTP 필요 |
| LLM | OpenAI 호환 API | 필수 |

## 로드맵

- [x] AI CMO 전략 스캔
- [x] SEO / GEO / SERP / 커뮤니티 모니터링
- [x] 버전 관리되는 전략 리포트와 주간 리포트
- [x] 멀티 에이전트 딕 리포트 파이프라인 (6단계)
- [x] 브랜드 포함 PDF 내보내기
- [x] 3D 지식 그래프
- [x] 승인 흐름과 통제된 발행
- [x] 중국 플랫폼 커뮤니티 모니터링 (V2EX, Weibo, Bilibili, XueQiu)
- [x] 완전한 i18n 지원 (영어, 중국어, 일본어, 한국어, 스페인어)
- [x] 로케일 인식 AI 응답 (LLM이 UI 언어 설정을 따름)
- [x] 불안정한 프로바이더를 위한 LLM 지수 백오프 재시도
- [x] 간편 온보딩: 홈페이지에서 URL만 입력하면 바로 시작
- [ ] 더 많은 발행 채널
- [ ] 브랜드 보이스 제어
- [ ] 더 깊은 엔터프라이즈 SEO 크롤링

## Contributors

- [study8677](https://github.com/study8677) - Creator and maintainer
- [Lling0000](https://github.com/Lling0000) - 가장 주요한 기여자
- [ParakhJaggi](https://github.com/ParakhJaggi) - Tavily integration ([#2](https://github.com/study8677/OpenCMO/pull/2), [#3](https://github.com/study8677/OpenCMO/pull/3))
- [BBear0115](https://github.com/BBear0115) - BYOK 키 격리, base_url 정규화 및 리포트 버그 수정 ([#9](https://github.com/study8677/OpenCMO/pull/9))
- 전체 목록은 [CONTRIBUTORS.md](CONTRIBUTORS.md) 참고

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

## Links

- [LINUX DO](https://linux.do/) — 기술 애호가들이 모이는 커뮤니티
