# aidCMO 重新定位 · 实施计划(Phase 1)

> 决策来源:`new-positioning.md` § 1.8 决策表(全部锁定)
> 代码事实来源:Explore agent 2026-04-28 的代码扫描报告
> 单 PR 范围:本文档 §A → §B → §C 全部内容,合并即上线;§D 是部署步骤

---

## A. 前置事实(写计划前已验证)

| 事实 | 来源 | 影响 |
|---|---|---|
| **公开路由全部在根路径**(`/`, `/services`, `/contact`...),CLAUDE.md 提到的 `/app/*` 是私有路由前缀,且实际由 catch-all 路由 `App.tsx:60-129` 统一处理 | `frontend/src/App.tsx:60-129`, `BrowserRouter` basename `/` 在 134 | 301 重定向必须**服务端**做(在 FastAPI catch-all 之前注册);客户端 `<Navigate>` 是 200 不是 301 |
| **`/api/v1/*` 当前无 auth 中间件**,所有 `api/v1` 路由直接 open(CLAUDE.md 描述与当前代码不符) | `src/opencmo/web/app.py:1317-1368` 全部 endpoint 无 `Depends`/auth 检查 | 新增 `/api/v1/waitlist` `/api/v1/github-stats` 保持 public,**不**为它们引入 auth(否则与现状不一致) |
| **i18n 是扁平 dotted strings**,5 个语言文件:`en.ts` / `zh.ts` / `ja.ts` / `ko.ts` / `es.ts` | `frontend/src/i18n/locales/*.ts` | 每个 key 改动要乘以 5;ja/ko/es 走 EN 回填策略(详见 §B.1) |
| **storage 是目录不是单文件**,新增表 → `storage/<entity>.py` + schema 注册到 `storage/_db.py:755 ensure_db()` | `storage/_db.py:139-142` (site_counters 例),`_db.py:755` (`ensure_db`),`storage/site_stats.py` (helper 模板) | waitlist 表按 site_counters 风格新建 |
| **`PublicServicePage.tsx` 用 `kind` prop 多路复用** 6 个公开页:b2b-leads / sample-data / seo-geo / open-source / data-policy / contact | `App.tsx:78-94`,`PublicServicePage.tsx` | 删除 = 删 4 个 kind 分支 + 删路由;`/services` 干脆抽成独立页(不复用 PublicServicePage,Phase 2 易扩展) |
| **`/sample-audit` 是独立 page**(`SampleAuditPage.tsx`,80 行),不走 PublicServicePage | `App.tsx:90`, `pages/SampleAuditPage.tsx` | 保留不动 |
| **`tools/github_api.py` 已有 httpx-based GitHub 调用 + 限流追踪** | `src/opencmo/tools/github_api.py:1-82` | `/api/v1/github-stats` 复用其 token 解析 + httpx pattern,不重写 |
| **路径辅助函数集中在 `marketing.ts`**(`getB2BLeadsPath`, `getSeoGeoPath` 等) | `frontend/src/content/marketing.ts:41-48` 及周边 | 删 / 重命名要同步改 |
| **CLAUDE.md 中提到的 `footer.publicTagline`、`landing.b2bSection*`、`landing.desktopPreviewTitle` 这 3 类 key 实际不存在** | Explore 报告 § 1 末尾 NOT FOUND | 落地时不要尝试删 / 改它们;需要先 grep 实际 footer key 名再编辑 |
| **服务端注入的 SEO meta + JSON-LD 还在硬编码 B2B 文案**(Explore 漏掉,Codex review 发现) | `web/app.py:39-88, 604-737, 808-843, 1101-1125` | 单改 React 不够;服务端模板 + 元数据必须同步改,见 §B.9 |
| **`frontend/public/sitemap.xml` 和 `llms.txt` 还在登记被删的路由** | `sitemap.xml:19-44, 64-104`, `llms.txt:15-22, 45` | Phase 1 必须同步清理,见 §B.9 |
| **i18n provider 已自动 EN fallback** | `frontend/src/i18n/I18nProvider.tsx:43-51`,locale 字典是 `Partial<Record<TranslationKey, string>>`(`ja.ts:1-3` 等) | 新增 key **不需要**在 ja/ko/es 加占位,自动回退到 EN;只需删旧 B2B key 即可 |
| **`apiJson` 已自动加 `/api/v1` 前缀** | `frontend/src/api/client.ts:3, 22`;现有 POST 调用要 `JSON.stringify` body(`api/keywords.ts:12-15`) | 新 wrapper 路径写 `/waitlist`(不是 `/api/v1/waitlist`),body 必须 stringify |
| **`@/` TS 路径别名未配置** | `frontend/tsconfig.app.json:2-19`、`vite.config.ts:5-16` 都没有 alias | 新代码必须用相对路径 `import` |
| **`tools/github_api.py:_get_github_token` 是 private,且查的是 `GITHUB_TOKEN` 不是 `OPENCMO_GITHUB_TOKEN`**;同模块已有 `_SEM` 限流信号量 + `_rate_remaining` 追踪 | `tools/github_api.py:13-15, 18-27, 46-60` | github-stats 必须通过新增的**公开**包装函数走,复用现有限流;新代码不直接 import 私有 `_` 前缀名 |

---

## B. 实施步骤

### Phase 0:开新分支,跑基线(≤ 5 min)

```bash
git checkout -b feat/repositioning-phase-1
cd frontend && npm run build  # 记录 baseline dist size
cd .. && pytest tests/        # 记录 baseline pass count
```

记录 baseline 后台 PR description 里贴一行,部署后对比。

---

### B.1 i18n 五语言改造(单步骤,但工作量最大,~3h)

> **‼️ 本节绝不在 ja/ko/es 中加任何 placeholder / `[needs-translation]` / EN 复制 ‼️**(决策见 §G #8,首版方案已废弃)
> 唯一动作:**删**旧 B2B 相关 keys。新 keys 不写入 ja/ko/es 文件 → `I18nProvider:43-51` 自动 fallback 到 EN。


**翻译策略**(已按 Codex review 修订):
- **EN 主基准**(`en.ts`):用 `new-positioning.md` § 1.5 的锁定文案
- **ZH 同步**(`zh.ts`):用 § 1.5 的锁定文案
- **ja / ko / es**:**只删旧 B2B keys,不新增任何 key,不加占位注释**。理由:
  - `I18nProvider:43-51` 对未命中的 key 已自动回退到 EN(locale 字典是 `Partial<Record<TranslationKey, string>>`)
  - 新 key 在 ja/ko/es 字典中不存在 ⇒ 框架自动显示 EN 值,无需手工占位
  - 旧 `service.b2b.*` / `service.sample.*` / `service.policy.*` 必须从 ja/ko/es **删掉**,否则切语言时仍会显示老 B2B 文案
  - 后续翻译 PR 独立做,不阻塞本期

#### B.1.1 删除(每个语言文件都要做一次)

| 操作 | 范围 | 备注 |
|---|---|---|
| 删整个 namespace | `service.b2b.*`(en.ts:682-722) | 5 文件 × ~40 keys |
| 删整个 namespace | `service.sample.*`(en.ts:805-842) | 5 文件 |
| 删整个 namespace | `service.policy.*`(en.ts:879-918) | 5 文件 |
| 删 inquiry 类型相关 sub-key | `service.contact.leadsTitle`、`service.contact.policyTitle` 等 B2B inquiry kind(en.ts:843-877 范围内) | 5 文件;具体哪几个 key 落地时 grep |
| 删 nav key | `nav.b2bLeads`、`nav.dataPolicy`(en.ts:411-415 附近)<br>**以及** `landing.navLeads`、`landing.navDataPolicy`(marketing.ts 实际引用的那一组,grep 确认) | 5 文件 |
| 删 landing 单 key | `landing.serviceLeadsTitle/Description`(635-638)、`landing.serviceCleanTitle/Description`(同区) | 5 文件 |

**⚠️ 落地前先 grep**:
- `grep -rn "landing.b2bSection" frontend/src/i18n/` —— Explore 报告说没有,grep 确认下
- `grep -rn "landing.desktopPreviewTitle" frontend/src/i18n/` —— 同上
- `grep -rn "footer.publicTagline" frontend/src/i18n/` —— 同上
- 若没找到,跳过(不要硬加)

#### B.1.2 重命名(整 namespace rename + 内容重写)

| 旧 namespace | 新 namespace | 内容来源 |
|---|---|---|
| `service.seoGeo.*` | `service.audit.*` | new-positioning.md § 1.5「Service landing page」草稿;Phase 1 只用 `heroTitle / heroSubtitle / ctaPrimary` 这 3 个 key,其他 key Phase 2 加 |

#### B.1.3 重写值(key 不变,值换)

| Key | 新值来源 |
|---|---|
| `landing.heroEyebrow` | new-positioning.md § 1.5「Hero(锁定 B)」 |
| `landing.heroTitle` | 同上 |
| `landing.heroSubtitle` | 同上 |
| `landing.metaTitle` | new-positioning.md § 1.5「Meta title / description」 |
| `landing.metaDescription` | 同上 |
| 实际 footer tagline / description key(grep 后确定的真实 key 名) | new-positioning.md § 1.5「Footer tagline + description」 |

#### B.1.4 新增 keys(扁平字符串,5 文件全部加)

```ts
// landing.builtInOpen.* — Built in the open 区块
"landing.builtInOpen.title": "Built in the open.",
"landing.builtInOpen.subtitle": "OpenCMO is the open-source engine behind every audit we deliver.",
"landing.builtInOpen.statStars": "{count} GitHub stars",
"landing.builtInOpen.statLastCommit": "Last commit · {time}",
"landing.builtInOpen.statContributors": "{count} contributors",
"landing.builtInOpen.fallbackStat": "View on GitHub",
"landing.builtInOpen.cta": "See the code, file an issue, or fork it →",

// landing.hosted.* — Hosted waitlist 表单
"landing.hosted.title": "Don't want to self-host? Get on the waitlist.",
"landing.hosted.subtitle": "We're working on a hosted version of OpenCMO. No date yet — we'll only email when it's ready.",
"landing.hosted.inputPlaceholder": "you@company.com",
"landing.hosted.submitButton": "Notify me",
"landing.hosted.submitting": "Sending…",
"landing.hosted.success": "You're on the list. We'll only email once.",
"landing.hosted.errorBadEmail": "That doesn't look like a valid email.",
"landing.hosted.errorGeneric": "Couldn't submit. Try again in a minute.",
"landing.hosted.note": "No drip sequences. One email when it ships.",

// landing.nav* — 导航(替换旧的)
"landing.navServices": "Services",
"landing.navOpenSource": "OpenCMO",            // 已存在,保留
"landing.navAuditExample": "Audit example",
"landing.navContact": "Contact",                // 已存在,保留
"landing.navBlog": "Blog",                      // 已存在,保留
"landing.navPrimaryCta": "Get a growth audit",

// service.audit.* — 服务页 Phase 1 minimal
"service.audit.heroTitle": "Get a growth audit.",
"service.audit.heroSubtitle": "Run by us. Powered by OpenCMO.",
"service.audit.heroCta": "Book a 30-min call",
"service.audit.placeholderNote": "Full overview, pricing, and FAQ coming soon. In the meantime, drop us a line.",
```

ZH 翻译见 § 1.5 各对应 block。
**ja/ko/es 字典中不写入这些新 key**(决议 §G #8) —— `I18nProvider:43-51` 自动 fallback 到 EN。

---

### B.2 后端 — `waitlist` 表(~30 min)

#### B.2.1 新建文件 `src/opencmo/storage/waitlist.py`

```python
"""Waitlist signups for the hosted OpenCMO version."""
from __future__ import annotations

import re
from typing import Optional

from ._db import get_db

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_ALLOWED_SOURCES = {"home_inline", "hosted_page", ""}


def is_valid_email(email: str) -> bool:
    """Reject obviously bad input. Real validation = double opt-in (Phase 2)."""
    if not isinstance(email, str):
        return False
    e = email.strip().lower()
    if len(e) > 254 or len(e) < 5:
        return False
    return bool(_EMAIL_RE.match(e))


def _normalize_source(source: Optional[str]) -> str:
    """Whitelist-only — defends against arbitrary string injection in source col."""
    if not source:
        return ""
    s = source.strip()
    return s if s in _ALLOWED_SOURCES else ""


async def add_to_waitlist(email: str, source: str = "") -> bool:
    """Idempotent insert. Returns True if accepted (new or duplicate)."""
    if not is_valid_email(email):
        return False
    normalized_source = _normalize_source(source)
    db = await get_db()
    try:
        await db.execute(
            "INSERT OR IGNORE INTO waitlist (email, source, created_at) "
            "VALUES (?, ?, datetime('now'))",
            (email.strip().lower(), normalized_source),
        )
        await db.commit()
        return True
    finally:
        await db.close()


async def count_waitlist() -> int:
    """For monitoring / debug only — no public endpoint exposes this."""
    db = await get_db()
    try:
        cursor = await db.execute("SELECT COUNT(*) FROM waitlist")
        row = await cursor.fetchone()
        return int(row[0]) if row else 0
    finally:
        await db.close()
```

#### B.2.2 注册 schema(Codex round 2 修订:跟实际 codebase 对齐)

实际 bootstrap 通过 `db.executescript(_SCHEMA)` 一次执行(`_db.py:755-767`),`_SCHEMA` 是模块顶部的字符串常量(包含所有 `CREATE TABLE`,例如 `site_counters` 在 `_db.py:136-140`)。**不要**在 `ensure_db()` 函数体里写 `await db.execute("CREATE TABLE...")`,要追加到 `_SCHEMA` 常量末尾。

```python
# storage/_db.py 顶部 _SCHEMA 字符串常量内,追加:

_SCHEMA = """
... 原有所有 CREATE TABLE ...

CREATE TABLE IF NOT EXISTS waitlist (
    email TEXT PRIMARY KEY,
    source TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS github_stats_cache (
    key TEXT PRIMARY KEY,
    payload TEXT NOT NULL,
    fetched_at REAL NOT NULL
);
"""
```

`source` 字段加入决议见 § G #11(已撤销原「不存 source」决定)。Phase 1 schema 一版定型,无 ALTER 迁移。**`github_stats_cache` 表合并在这里注册**(§B.4.1 不再单独写注册段)。

#### B.2.3 注册到 `storage/__init__.py`

按现有 `site_stats` 风格在 `storage/__init__.py` 添加 re-export(`storage.add_to_waitlist(...)` 直接可用,与 `site_counters` 一致 —— 见 `storage/__init__.py:221-225, 289-290`):

```python
from .waitlist import add_to_waitlist, count_waitlist, is_valid_email

__all__ = [..., "add_to_waitlist", "count_waitlist", "is_valid_email"]
```

---

### B.3 后端 — `POST /api/v1/waitlist`(~30 min)

#### B.3.1 写到 `src/opencmo/web/app.py`(在 catch-all `@app.get("/{full_path:path}")` 之前)

```python
from typing import Literal, Optional
from pydantic import BaseModel, Field  # 不导入 EmailStr —— 用纯 str + 自家正则,避免引入 email-validator dep,Ruff F401 也会保护
from opencmo.storage import add_to_waitlist, is_valid_email


class WaitlistSubmit(BaseModel):
    email: str = Field(..., min_length=5, max_length=254)
    # Whitelist 限制,防止前端传任意值;后端再次 normalize
    source: Optional[Literal["home_inline", "hosted_page"]] = None


@app.post("/api/v1/waitlist")
async def api_v1_waitlist(payload: WaitlistSubmit):
    if not is_valid_email(payload.email):
        return JSONResponse({"ok": False, "error": "invalid_email"}, status_code=400)
    accepted = await add_to_waitlist(payload.email, source=payload.source or "")
    if not accepted:
        return JSONResponse({"ok": False, "error": "rejected"}, status_code=400)
    return JSONResponse({"ok": True})
```

**Pydantic 版本**:仓库实际用 Pydantic v2(`pyproject.toml` 锁定)。`Field(..., min_length=...)` 在 v2 里是合法签名;`Literal` 比 `EmailStr` 更窄,不引入 `email-validator` 新 dep。

**取舍**(Phase 1):
- **不**做应用层 rate limit(无新 dep);**前置 nginx `limit_req` 在 §D 配置**(已撤销 §G #12 偷懒决定)
- **不**做双重 opt-in(产品发布前必加,见 §F「DKIM/SPF/DMARC + 双重 opt-in」)
- **不**记 IP / UA;但**记** `source ∈ {home_inline, hosted_page}`(已撤销 §G #11 偷懒决定),用于区分两个入口的转化

---

### B.4 后端 — `GET /api/v1/github-stats`(~2h,Codex review 后调高)

#### B.4.0 先在 `tools/github_api.py` 加公开 token helper + headers-aware GET

`_get_github_token` 是 private,且查的是 `GITHUB_TOKEN` 不是 `OPENCMO_GITHUB_TOKEN`(`tools/github_api.py:18-27`)。在该文件**尾部追加**两个公开包装函数,以便:
- github-stats 不直接 import `_` 前缀名
- 复用现有 `_SEM` 信号量 + `_rate_remaining` 追踪(`tools/github_api.py:13-15, 46-60`)
- 暴露 response headers 用于 Link header 解析

```python
# tools/github_api.py 末尾追加

# 文件顶部确保已 import:
#   from typing import Any, Optional
# 当前 github_api.py:1-10 没有 typing import,**必须**加上;
# 或全部用 PEP 604 写法(`X | None`),与项目其余文件一致即可

async def get_github_token() -> Optional[str]:
    """Public wrapper for token resolution. Reads DB settings then env."""
    return await _get_github_token()


async def github_get_with_headers(
    path: str,
    params: Optional[dict] = None,
) -> tuple[Optional[Any], dict[str, str]]:
    """Like _github_get but also returns response headers.
    Returns (parsed_json_or_None, headers_dict).

    Return type is Optional[Any] not Optional[dict] because GitHub
    endpoints return both objects (e.g. /repos/X) and arrays (e.g.
    /repos/X/contributors). Caller must type-narrow.

    Implementation contract:
      1. Acquire `_SEM` (existing semaphore at line 13)
      2. Resolve token via `_get_github_token()` (line 18-27)
      3. Use existing httpx client style (matching `_github_get` line 46-60)
      4. Update `_rate_remaining` from `X-RateLimit-Remaining` response header
      5. On 4xx/5xx/network/timeout: return (None, response_headers_or_{})
      6. On success: return (response.json(), dict(response.headers))

    Falsehoods to avoid:
      - Do NOT duplicate rate-tracking logic — call into the same
        path `_github_get` uses, or refactor `_github_get` to internally
        call this function.
      - Do NOT silently raise — caller relies on None for failure.

    Behavioral split between `_github_get` and `github_get_with_headers`:
      - `_github_get` (existing, line 46-60): raises on HTTP/network failures
        (other internal callers depend on this exception path)
      - `github_get_with_headers` (new public): swallows failures, returns
        `(None, headers_or_{})` so marketing-site rendering degrades gracefully

      If you refactor `_github_get` to internally call the new function (option
      a), you MUST re-raise inside `_github_get` to preserve its public contract.
      Don't change `_github_get`'s caller-visible behavior.
    """
    # 落地策略二选一:
    # (a) 重构 _github_get 内部调用 github_get_with_headers,
    #     _github_get 仅丢弃 headers 返回 body
    # (b) 新写薄层完整复制 _github_get 逻辑
    # 推荐 (a),避免代码重复;(b) 维护成本高
```

#### B.4.1 新建 `src/opencmo/storage/github_stats_cache.py` —— SQLite 缓存层

按 `storage/site_stats.py:8-37` 同款 async 风格(已撤销 §G #9 偷懒决定,恢复 memory + SQLite 双层,匹配 `new-positioning.md:166-175` 锁定规范):

```python
"""SQLite-backed cache for GitHub repo stats. TTL handled at read time."""
from __future__ import annotations

import json
import time
from typing import Optional

from ._db import get_db


async def get_cached_github_stats(key: str, ttl_sec: int) -> Optional[dict]:
    """Returns parsed payload if fresh, None if missing or stale."""
    db = await get_db()
    try:
        cursor = await db.execute(
            "SELECT payload, fetched_at FROM github_stats_cache WHERE key = ?",
            (key,),
        )
        row = await cursor.fetchone()
        if not row:
            return None
        payload, fetched_at = row[0], float(row[1])
        if time.time() - fetched_at > ttl_sec:
            return None
        return json.loads(payload)
    finally:
        await db.close()


async def set_cached_github_stats(key: str, payload: dict) -> None:
    db = await get_db()
    try:
        await db.execute(
            """INSERT INTO github_stats_cache (key, payload, fetched_at)
            VALUES (?, ?, ?)
            ON CONFLICT(key) DO UPDATE SET
                payload = excluded.payload,
                fetched_at = excluded.fetched_at""",
            (key, json.dumps(payload), time.time()),
        )
        await db.commit()
    finally:
        await db.close()
```

**Schema 注册位置**:已合并到 §B.2.2 `_SCHEMA` 常量(避免在 `ensure_db()` 里散落 `db.execute()`,匹配现有 `site_counters` 同款风格)。

并在 `storage/__init__.py` re-export `get_cached_github_stats`、`set_cached_github_stats`(同 `add_to_waitlist` 路径)。

#### B.4.2 新建 `src/opencmo/web/github_stats.py` —— 拉取 + 双层缓存 + 单飞锁

```python
"""Cached GitHub repo stats for marketing site Built-in-open block.

Cache layers (per Codex review fix):
  L1 = in-process memory dict (avoids SQLite hit on hot path)
  L2 = SQLite github_stats_cache table (survives restarts)
  Both honor the same 24h TTL. Asyncio lock prevents thundering herd
  when memory cold-starts and multiple requests race.
"""
from __future__ import annotations

import asyncio
import re
import time
from typing import Optional, TypedDict

import httpx

from opencmo.storage import get_cached_github_stats, set_cached_github_stats
# 注意:`get_github_token` 在本文件**不**直接调用 —— token 解析由 `github_get_with_headers` 内部完成。
# 不要 import 进来(否则 Ruff F401 报未用)。
from opencmo.tools.github_api import github_get_with_headers

_REPO = "Lling0000/OpenCMO"
_CACHE_KEY = f"repo:{_REPO}"
_CACHE_TTL_SEC = 24 * 3600
_TIMEOUT = httpx.Timeout(8.0, connect=4.0)

# L1: in-process memory.  Tuple = (epoch_seconds, payload).
_mem_cache: dict[str, tuple[float, dict]] = {}
# Single-flight lock: prevents N concurrent cold-start requests from
# all hitting GitHub simultaneously after deploy/restart.
_fetch_lock = asyncio.Lock()


class GitHubStats(TypedDict):
    stars: Optional[int]
    contributors: Optional[int]
    last_commit_iso: Optional[str]
    fetched_at: Optional[str]


def _empty_stats() -> GitHubStats:
    return {"stars": None, "contributors": None, "last_commit_iso": None, "fetched_at": None}


def _read_mem(now: float) -> Optional[dict]:
    cached = _mem_cache.get(_CACHE_KEY)
    if cached and now - cached[0] < _CACHE_TTL_SEC:
        return cached[1]
    return None


async def _fetch_repo() -> Optional[dict]:
    """Returns the repo JSON, or None on any failure (network / 4xx / 5xx)."""
    try:
        body, _headers = await github_get_with_headers(f"/repos/{_REPO}")
        return body
    except Exception:
        return None


async def _fetch_contributor_count() -> Optional[int]:
    """Parses contributor count from Link header rel='last'.

    Edge cases (verified by tests in §C):
      * 0 contributors → API returns []; len → 0
      * 1 page (≤ per_page) → no Link header; len → actual count
      * Many pages → Link header present; rel='last' page number = count
      * anon=true denied → falls through to len fallback
    """
    try:
        body, headers = await github_get_with_headers(
            f"/repos/{_REPO}/contributors",
            params={"per_page": 1, "anon": "true"},
        )
        if body is None:
            return None
        link = headers.get("Link", "") or headers.get("link", "")
        for part in link.split(","):
            if 'rel="last"' in part:
                m = re.search(r"[?&]page=(\d+)", part)
                if m:
                    return int(m.group(1))
        # No Link header → response body is full list
        return len(body) if isinstance(body, list) else None
    except Exception:
        return None


async def get_github_stats() -> GitHubStats:
    now = time.time()

    # L1 fast path
    cached = _read_mem(now)
    if cached is not None:
        return cached  # type: ignore[return-value]

    # Single-flight: only one fetcher at a time after cold start
    async with _fetch_lock:
        # Re-check L1 after acquiring lock (someone may have populated it)
        cached = _read_mem(now)
        if cached is not None:
            return cached  # type: ignore[return-value]

        # L2: SQLite cache (survives process restart)
        sqlite_cached = await get_cached_github_stats(_CACHE_KEY, _CACHE_TTL_SEC)
        if sqlite_cached is not None:
            _mem_cache[_CACHE_KEY] = (now, sqlite_cached)
            return sqlite_cached  # type: ignore[return-value]

        # Cold path: hit GitHub
        repo, contrib = await asyncio.gather(_fetch_repo(), _fetch_contributor_count())

        # Codex bugfix: do NOT cache partial failures.
        # Original spec (new-positioning.md:173-175): "any API failure → return all-null".
        # Caching contributors=null for 24h would be wrong when repo succeeded.
        if repo is None or contrib is None:
            return _empty_stats()

        stats: GitHubStats = {
            "stars": repo.get("stargazers_count"),
            "contributors": contrib,
            "last_commit_iso": repo.get("pushed_at"),
            "fetched_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(now)),
        }
        _mem_cache[_CACHE_KEY] = (now, stats)
        await set_cached_github_stats(_CACHE_KEY, stats)
        return stats
```

#### B.4.3 在 `app.py` 注册端点(catch-all 之前,§B.5 同位置)

```python
from opencmo.web.github_stats import get_github_stats


@app.get("/api/v1/github-stats")
async def api_v1_github_stats():
    return JSONResponse(await get_github_stats())
```

**修订点**(对比首版):
- **加 SQLite L2 缓存**:撤销 §G #9。重启不丢缓存,部署期间不会击穿 GitHub
- **加 `asyncio.Lock` 单飞**:冷启动时多请求不会并发打 GitHub
- **修部分失败缓存中毒**:原代码 `repo=ok, contrib=null` 会把 `null` 缓存 24h。改为「任一失败 → 全 null,且不缓存」,匹配 `new-positioning.md:173-175`
- **走公开包装函数**:不直接 import `_` 私有名;复用 `_SEM` + `_rate_remaining`
- **不加 `OPENCMO_GITHUB_TOKEN`**(决议 §G #7 保留):未配置时走未登录 60 req/h,24h 缓存 + 单飞锁后单进程一天 ≤ 2 次调用

---

### B.5 后端 — 服务端 301 重定向(~30 min,Codex 修订)

#### B.5.1 注册位置

**必须在 catch-all 之前**:catch-all 在 `web/app.py:1377-1421`(`@app.get("/{full_path:path}")`)。FastAPI 路由是顺序匹配,任何注册在 catch-all 之后的路由都会被吞掉。**插入点:`app.py:1376` 之前**(catch-all 函数定义那一行的上方)。

#### B.5.2 实现 —— 工厂函数 + typed Request + **保留 locale 前缀** + 支持 HEAD

Codex round 2 修订:
- 首版 `async def _redirect(request, _new=new)` 的 `request` 没标类型 → FastAPI 当 query 参数 → 422。✅ 已修
- 首版只注册 `methods=["GET"]`,但 catch-all 同时声明 `GET` 和 `HEAD`(`app.py:1377-1380`),且 §D smoke 用 `curl -I`(HEAD)。**redirect 必须支持 GET + HEAD**
- 首版 `/en/b2b-leads` → `/services` 丢失 locale。**必须 → `/en/services`**(用户原本在 EN 站,redirect 后该留在 EN 站)

```python
from fastapi import Request
from fastapi.responses import RedirectResponse

# Legacy → new positioning. Keep for at least 6 months for inbound links.
_REDIRECTS_301 = {
    "b2b-leads":   "/services",
    "sample-data": "/services",
    "data-policy": "/",
    "seo-geo":     "/services",
}


def _make_redirect(target: str):
    """Factory captures `target` in closure scope safely (no late-binding)."""
    async def _redirect(request: Request) -> RedirectResponse:  # noqa: ARG001
        return RedirectResponse(url=target, status_code=301)
    return _redirect


def _build_target(prefix: str, new: str) -> str:
    """Preserve locale prefix on redirect target.
      prefix ∈ {"", "en/", "zh/"}, new ∈ {"/", "/services", ...}
    Examples:
      ("",     "/services") -> "/services"
      ("en/",  "/services") -> "/en/services"
      ("zh/",  "/")          -> "/zh"
      ("",     "/")          -> "/"
    """
    locale = prefix.rstrip("/")  # "" | "en" | "zh"
    if new == "/":
        return f"/{locale}" if locale else "/"
    return f"/{locale}{new}" if locale else new


# 必须紧贴 catch-all 之前注册
for old, new in _REDIRECTS_301.items():
    for prefix in ("", "en/", "zh/"):
        path = f"/{prefix}{old}"
        target = _build_target(prefix, new)
        app.add_api_route(path, _make_redirect(target), methods=["GET", "HEAD"])
```

#### B.5.3 测试要求(§C 必跑)

`tests/test_redirects.py` 必须断言:
- 12 条路径,GET **和** HEAD 都 `status_code == 301`(不是 422,不是 405)
- `Location` 头**保留 locale**:
  - `/b2b-leads` → `/services`
  - `/en/b2b-leads` → `/en/services`
  - `/zh/b2b-leads` → `/zh/services`
  - `/data-policy` → `/`
  - `/en/data-policy` → `/en`
  - `/zh/data-policy` → `/zh`
  - 其余 6 条同款映射
- closure late-binding 验证:4 种 old → 不同 new,目标不能全部一样

---

### B.6 前端 — 路由 / 导航 / 路径辅助函数(~30 min)

#### B.6.1 改 `frontend/src/content/marketing.ts:41-48`

```ts
export const PUBLIC_HOME_NAV: PublicNavItem[] = [
  { href: "/services",      label: "landing.navServices" },
  { href: "/open-source",   label: "landing.navOpenSource" },
  { href: "/sample-audit",  label: "landing.navAuditExample" },
  { href: "/blog",          label: "landing.navBlog" },
  { href: "/contact",       label: "landing.navContact" },
];
```

**路径辅助函数**:
- 删除:`getB2BLeadsPath()`、`getSampleDataPath()`、`getDataPolicyPath()`
- 重命名 + 改返回值:`getSeoGeoPath()` → `getServicesPath()`,返回 `/services`(语言前缀逻辑保留)
- 保留:`getOpenSourcePath()`、`getSampleAuditPath()`、`getContactPath()`
- 新增:`getHostedPath()` → 返回 `/hosted`

**全仓 grep + 改引用**:
```bash
grep -rn "getB2BLeadsPath\|getSampleDataPath\|getDataPolicyPath\|getSeoGeoPath" frontend/src/
```
预期都在 `LandingPage.tsx` / `Footer` / `Header` / `marketing.ts` 内,数量 < 15 处。

#### B.6.1.5 改 `frontend/src/utils/publicRoutes.ts`(Codex round 2 漏项修复)

该文件维护「哪些路由是公开 marketing 站」的清单(用于 locale 切换器、AppShell 行为分支等)。**必改:**
- 删除条目:`/b2b-leads`、`/sample-data`、`/data-policy`、`/seo-geo`(及其 `/en/*`、`/zh/*` 变体,如有列举)
- 新增条目:`/services`、`/hosted`(及对应 `/en/*`、`/zh/*` 变体)

落地步骤:
1. `cat frontend/src/utils/publicRoutes.ts` —— 看清结构(数组?Set?map?lines 50-65 是 Codex 给的范围)
2. 按现有结构替换(同 marketing.ts 的 `PUBLIC_HOME_NAV`)
3. `grep -rn "publicRoutes\." frontend/src/` —— 确认所有调用点不 break

#### B.6.2 改 `frontend/src/App.tsx:60-129`

**删除路由**(连同语言前缀变体共 3×4 = 12 条):
- `/b2b-leads`, `/en/b2b-leads`, `/zh/b2b-leads`
- `/sample-data`, `/en/sample-data`, `/zh/sample-data`
- `/data-policy`, `/en/data-policy`, `/zh/data-policy`
- `/seo-geo`, `/en/seo-geo`, `/zh/seo-geo`

**新增路由**(每条都有 3 个语言变体):
- `/services`, `/en/services`, `/zh/services` → 新 `<ServicesPage />`
- `/hosted`, `/en/hosted`, `/zh/hosted` → 新 `<HostedWaitlistPage />`

**保留**:其余全部不动。`/workspace` 保留(私有路由),只是从公开 nav 移除 —— B.6.1 的 `PUBLIC_HOME_NAV` 已没它。

#### B.6.3 改 `PublicServicePage.tsx`

删除 `kind` 分支:`b2b-leads`、`sample-data`、`data-policy`、`seo-geo`。
保留:`open-source`、`contact`。
`contact` 表单内的 inquiry type 选项删除「B2B leads」「Data policy」「Sample data」相关项,只留「Growth audit / Self-host help / Other」3 项(具体 key 落地时按真实代码改)。

---

### B.7 前端 — 新组件(~2h)

#### B.7.1 `frontend/src/api/client.ts` 扩展(Codex 修订)

**关键修正**:
- `apiJson` 已经在 `client.ts:3, 22` 自动加 `/api/v1` 前缀,新 wrapper 路径写 `/waitlist`(**不是**`/api/v1/waitlist`),否则会变成 `/api/v1/api/v1/waitlist`
- POST body 必须 `JSON.stringify(...)`,看现有 `frontend/src/api/keywords.ts:12-15` 同款写法

```ts
// 在 client.ts 末尾追加
export type WaitlistSource = "home_inline" | "hosted_page";

export async function submitWaitlist(
  email: string,
  source: WaitlistSource,
): Promise<{ ok: boolean; error?: string }> {
  return apiJson("/waitlist", {
    method: "POST",
    body: JSON.stringify({ email, source }),
  });
}

export interface GitHubStats {
  stars: number | null;
  contributors: number | null;
  last_commit_iso: string | null;
  fetched_at: string | null;
}

export async function getGitHubStats(): Promise<GitHubStats> {
  return apiJson("/github-stats");
}
```

#### B.7.2 新 hook `frontend/src/hooks/useGitHubStats.ts`(Codex 修订)

`@/` 别名在 `tsconfig.app.json` / `vite.config.ts` 都未配置 —— 用相对路径:

```ts
import { useQuery } from "@tanstack/react-query";
import { getGitHubStats, type GitHubStats } from "../api/client";

export function useGitHubStats() {
  return useQuery<GitHubStats>({
    queryKey: ["github-stats"],
    queryFn: getGitHubStats,
    staleTime: 24 * 60 * 60 * 1000, // 24h
    gcTime: 24 * 60 * 60 * 1000,    // 24h
    retry: 1,
  });
}
```

#### B.7.3 新组件 `frontend/src/components/landing/BuiltInOpen.tsx`

按 § 1.3 布局实现:
- H2 + sub
- 3 列 stat cards(stars / last commit / contributors)
- **任一 stat 为 null → 整个 stats 区域不渲染**,只显示 fallback「View on GitHub」link(Codex round 2 修订:首版 `allNull` 只检查 stars + contributors,漏掉 last_commit_iso,与文案不一致)
- 全部 null / 任一 null 时 fallback 都是单 anchor 到 `https://github.com/Lling0000/OpenCMO`
- "Last commit" 时间用 `utcDate()` from `utils/time.ts` 转本地 + relative format(`Intl.RelativeTimeFormat` 或现有 helper)

```tsx
// 关键骨架
const { data, isLoading, isError } = useGitHubStats();

// 严格:任一字段 null 都降级 fallback,与文案「any null → hide」一致
const anyNull =
  !data ||
  data.stars === null ||
  data.contributors === null ||
  data.last_commit_iso === null;

if (isLoading) return <Skeleton />;
if (isError || anyNull) return <FallbackBlock />;
return <ThreeStatsBlock data={data} />;
```

#### B.7.4 新组件 `frontend/src/components/landing/HostedWaitlist.tsx`

```tsx
import { useState } from "react";
import { submitWaitlist, type WaitlistSource } from "../../api/client";

interface Props { variant: "inline" | "page"; }

// variant ↔ source 映射(后端 Pydantic Literal 校验,见 §B.3)
const VARIANT_TO_SOURCE: Record<Props["variant"], WaitlistSource> = {
  inline: "home_inline",
  page:   "hosted_page",
};

// State machine: idle → submitting → success | error
// 客户端简单 regex 校验(与后端 _EMAIL_RE 一致),失败本地提示不发请求
// 提交时 source = VARIANT_TO_SOURCE[variant]
// 成功后整块替换为 success 文案 landing.hosted.success
// inline:无大标题,横向 flex;page:大标题 + 居中
```

**关键设计**:不弹 toast(避免引入新 dep);state 在组件内,不污染全局。**source 字段的目的**:Phase 1 之后能 `SELECT source, COUNT(*) FROM waitlist GROUP BY source` 区分主页内嵌 vs 独立页的转化。

#### B.7.5 新页面 `frontend/src/pages/ServicesPage.tsx`

Phase 1 只渲染:
- Hero(`service.audit.heroTitle` + `heroSubtitle`)
- 单个主 CTA → `/contact`(理由:Phase 1 `/services` 只是 skeleton,真实转化路径走 contact)
- `service.audit.placeholderNote` 一行 placeholder

后续 Phase 2 在此文件内展开 7 个 section。

#### B.7.6 新页面 `frontend/src/pages/HostedWaitlistPage.tsx`

```tsx
export default function HostedWaitlistPage() {
  return <PageShell><HostedWaitlist variant="page" /></PageShell>;
}
```

---

### B.8 前端 — 主页改写(~45 min)

#### B.8.1 改 `frontend/src/pages/LandingPage.tsx:189-231` Hero

替换 hero copy 引用的 i18n key — `landing.heroTitle/Subtitle/Eyebrow` 已在 B.1.3 改值,组件代码不需要改;但要更新 CTA 按钮目标:
- 主 CTA `landing.navPrimaryCta`("Get a growth audit") → `/contact`
- 次 CTA "View on GitHub" → `https://github.com/Lling0000/OpenCMO`(外链)

#### B.8.2 在 LandingPage.tsx 中

- **删除** B2B / Email-clean / SEO-GEO 三卡 services section(line 234+ 一带,`landing.serviceLeadsTitle/CleanTitle/...`)
- **删除** DevicePreview 的 B2B 表格预览(若 hardcoded 文案)—— 落地 grep 决定是改 prop 还是删整段
- **新增** `<BuiltInOpen />` 在 hero 之后
- **新增** `<HostedWaitlist variant="inline" />` 在主页中下部(BuiltInOpen 之后)

#### B.8.3 Footer

- 找到实际 footer key(grep `footer.` 在 `i18n/locales/en.ts` 里),按 § 1.5「Footer tagline + description」更新值
- 在 footer 链接列表里新增「Hosted (waitlist)」→ `/hosted`
- 删除 footer 里指向 `/b2b-leads` `/data-policy` `/sample-data` 的链接(若有)

#### B.8.4 Header

- 找 header 组件(估计 `frontend/src/components/layout/Header.tsx` 或类似)
- 主 CTA 按钮换为 "Get a growth audit"
- "Source code" 图标按钮(GitHub 外链,无数字)在右上保留 / 新增

---

### B.9 服务端 SEO + JSON-LD + 静态资源清理(Codex review 新增,~1h)

> **这一节是 Codex review 发现的最大遗漏**:`web/app.py` 给爬虫和首屏 SSR 注入的 meta + JSON-LD 还在硬编码 B2B 文案,只改 React 不改这里 → 部署后前端显示新定位、Google/AI 爬虫看到的是旧 B2B 文案,严重自相矛盾。同样,`frontend/public/sitemap.xml` 和 `llms.txt` 还在登记被删的 4 个路由。

#### B.9.1 改 `web/app.py` 服务端注入的 SEO 文案

**4 处必改**(精确行号见 §A):

| 位置 | 内容性质 | 处置 |
|---|---|---|
| `app.py:39-88` | 推测是 `SITE_META` / 默认页 metadata 字典 | 替换 title / description / keywords / og:* 字段为新定位文案(对应 `new-positioning.md` § 1.5「Meta title / description」) |
| `app.py:604-737` | 推测是按 route 拆的服务页 metadata | **删**对应 `/b2b-leads` `/sample-data` `/data-policy` `/seo-geo` 4 个 route 的 metadata 块;**新增** `/services` `/hosted` 的 metadata 块 |
| `app.py:808-843` | 推测是某段 SSR 注入的 HTML / 默认 hero | 替换 hero 文案为 § 1.5 锁定的 EN 文案 |
| `app.py:1101-1125` | 推测是 JSON-LD `Organization` / `WebSite` 结构化数据 | 检查并清理任何 B2B 关键词 + `sameAs` / 服务列表里的 B2B 项 |

**落地步骤**(每个文件先读再改):
1. `sed -n '39,88p' src/opencmo/web/app.py` —— 看清是什么数据结构
2. `sed -n '604,737p' src/opencmo/web/app.py` —— 同上
3. `sed -n '808,843p' src/opencmo/web/app.py` —— 同上
4. `sed -n '1101,1125p' src/opencmo/web/app.py` —— 同上
5. 按上述映射改;**改完用 `grep -n "B2B\|Overseas\|email lead\|sample-data\|data-policy\|b2b-leads\|seo-geo" src/opencmo/web/app.py` 应当 0 行**(legacy 重定向字典里的 key 除外,grep 时排除)

#### B.9.2 改 `frontend/public/sitemap.xml`

**删除**:
- `:19-44` 范围内 `/b2b-leads`、`/en/b2b-leads`、`/zh/b2b-leads` 三条 `<url>` 块
- `:64-104` 范围内 `/sample-data`、`/data-policy`、`/seo-geo` 各 3 条(中英文变体)

**新增**(放在合适语言分组下):
- `/services`、`/en/services`、`/zh/services`
- `/hosted`、`/en/hosted`、`/zh/hosted`
- 每条都要有 `<lastmod>` `<changefreq>weekly</changefreq>` `<priority>0.8</priority>`

#### B.9.3 改 `frontend/public/llms.txt`

**删除**(精确行号):
- `:15-22` 范围内 「B2B leads」/「Sample data」/「Data policy」相关条目
- `:45` 周边对 `/seo-geo` / `/b2b-leads` 的链接

**新增**:
- `/services` 一行简介(用 `service.audit.heroSubtitle` 内容)
- `/hosted` 一行简介(用 `landing.hosted.subtitle` 内容)
- `/open-source` 强化一行(指向 GitHub repo)

#### B.9.4 验证脚本(部署前必跑)

```bash
# 全仓 grep 旧 B2B 词,应当 0 行(排除本计划文档自身)
grep -rn "Overseas B2B\|B2B leads\|email verification" \
  src/ frontend/src/ frontend/public/ \
  --exclude-dir=node_modules --exclude-dir=dist | \
  grep -v "implementation-plan\|new-positioning\|current-state"

# 旧路由不应出现在已发布的 sitemap / llms 里
grep -E "(b2b-leads|sample-data|data-policy|seo-geo)" \
  frontend/public/sitemap.xml frontend/public/llms.txt
# 期望 0 行
```

---

## C. 测试(~1.5–2h,Codex 调高)

### C.1 后端测试

#### `tests/test_waitlist.py`(新建)
- `test_valid_email_accepted`
- `test_duplicate_email_idempotent`(连续 2 次 INSERT,第二次 `INSERT OR IGNORE` 成功,count=1)
- `test_invalid_email_rejected`(空字符串、`abc`、`@x`、超 254 字符)
- `test_email_normalized`(`FOO@x.COM` 与 `foo@x.com` 视为同一行)
- `test_source_whitelist`(`source="bogus"` 被静默归一化为 `""`,**不**返回 400 —— 因为前端 Pydantic 已校验,后端再防御)
- `test_source_recorded`(`source="home_inline"` 真的写入 row)
- 复用 `tmp_path` SQLite 模式

#### `tests/test_github_stats.py`(新建)
- `test_l1_memory_cache_hit`(填充 `_mem_cache`,验证不调用 httpx 也不读 SQLite)
- `test_l2_sqlite_cache_hit`(清空 mem,SQLite 有新鲜行,验证不调用 httpx)
- `test_cold_path_fetches_and_writes_both_layers`(mock httpx,验证 mem + sqlite 都被写入)
- `test_partial_failure_returns_nulls_and_does_not_cache`(repo 成功 + contributors 抛 ConnectionError → 返回全 null,**且** mem / sqlite 都未写入)
- `test_full_failure_returns_nulls`(两个都失败 → 全 null,无缓存)
- `test_contributor_count_no_link_header`(单页响应,len fallback 正确)
- `test_contributor_count_with_link_header`(rel="last" 解析正确)
- `test_contributor_count_zero`(空数组 → 0)
- `test_single_flight_lock`(并发 5 个 cold-path 请求,验证只调用 httpx 一次)

#### `tests/test_redirects.py`(新建)
- 用 FastAPI `TestClient`(`follow_redirects=False`)
- 对 `/b2b-leads` `/en/b2b-leads` `/zh/b2b-leads` `/sample-data` `/en/sample-data` `/zh/sample-data` `/data-policy` `/en/data-policy` `/zh/data-policy` `/seo-geo` `/en/seo-geo` `/zh/seo-geo` 全部 **12 条**断言:
  - `status_code == 301`(**特别确认不是 422** —— Codex 指出首版会因 `request` 没标类型变成 query 参数 → 422)
  - `Location` 头指向**正确**的目标(确认无 closure late-binding,4 种 old → 不同 new 都正确)

#### `tests/test_seo_copy_clean.py`(新建)
保护 §B.9 的清理不被回归:
- 全文件 grep:`grep -RIn "Overseas B2B\|email verification\|sample-data\|data-policy\|b2b-leads\|seo-geo" src/opencmo/web/app.py | grep -v "_REDIRECTS_301"` 应当 0 行
- `frontend/public/sitemap.xml` 不含被删路由
- `frontend/public/llms.txt` 不含被删路由

### C.2 前端 build smoke

```bash
cd frontend
npm run build
# 应当 0 TS error;dist 大小变化记录到 PR description
grep -r "B2B" dist/ | head -20    # 应当 0 行(或仅 vendor 内部 case-insensitive 假阳性)
grep -r "Overseas" dist/          # 应当 0 行
grep -r "data-policy" dist/       # 应当 0 行
```

### C.3 dev 视觉 smoke

```bash
cd frontend && npm run dev
```

逐个访问、肉眼确认:
- `/` —— 新 hero(B 文案) + Built in the open + Hosted waitlist + 5 项导航
- `/services` —— 占位 hero + 「即将上线」一行 + CTA → `/contact`
- `/hosted` —— Hosted waitlist 单页版
- `/open-source` —— 内容仍正常(`PublicServicePage kind="open-source"` 没改)
- `/contact` —— inquiry type 只剩 3 项,B2B 类全消失
- `/sample-audit` —— 完全不变
- `/blog`, `/blog/:slug` —— 完全不变

**Dev 模式无 301**(那是服务端逻辑),旧路径 `/b2b-leads` 在 dev 会显示 React Router 404,这是正常的。301 验证留给 §D。

### C.4 全套测试

```bash
pytest tests/ -v
# 与 baseline 对比:新增 3 个测试文件 ~12 个 case 全过;旧 case 0 回归
```

---

## D. 部署(~45 min,Codex 修订)

参考 CLAUDE.md「Deployment (newyork — aidcmo.com)」节。

### D.0 部署前必做:DB 备份(Codex 漏项修复)

新表会导致 `ensure_db()` 执行 `CREATE TABLE`(`waitlist`、`github_stats_cache` 各一)。理论上 idempotent,但 Phase 1 是新功能首次上线,**生产 DB 必须先备份**:

```bash
ssh newyork "sqlite3 ~/.opencmo/data.db \".backup '~/.opencmo/data.db.bak-$(date +%Y%m%d-%H%M%S)'\""
ssh newyork "ls -lh ~/.opencmo/data.db.bak-* | tail -3"   # 确认备份文件存在
```

回滚时直接 `cp data.db.bak-... data.db && systemctl restart opencmo`。

### D.1 部署

```bash
# Frontend(本地构建,避免服务端构建)
cd frontend && npm run build
rsync -avz --delete frontend/dist/ root@192.3.16.77:/opt/OpenCMO/frontend/dist/

# Backend
rsync -avz --delete \
  --exclude '.git' --exclude 'frontend/node_modules' \
  --exclude 'frontend/dist' --exclude '.venv' \
  ./ root@192.3.16.77:/opt/OpenCMO/

ssh newyork "cd /opt/OpenCMO && source .venv/bin/activate && pip install -e . -q && systemctl restart opencmo"
```

### D.1.5 nginx `limit_req` 配置(Codex 修订,撤销 §G #12 偷懒决定)

`/api/v1/waitlist` 是公开 unauth 写端点,必须前置限流。改 `/etc/nginx/sites-enabled/aidcmo.conf`:

```nginx
# 顶部 http {} 或 server {} 上方
limit_req_zone $binary_remote_addr zone=waitlist:10m rate=5r/m;

# server {} 内
location = /api/v1/waitlist {
    limit_req zone=waitlist burst=3 nodelay;
    limit_req_status 429;
    proxy_pass http://127.0.0.1:8081;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
}
```

每 IP 5 次/分钟 + burst 3,触发 429。部署:
```bash
ssh newyork "nginx -t && systemctl reload nginx"
```

### D.2 部署后 smoke(必跑)

```bash
# 1. 服务起来了
ssh newyork "systemctl status opencmo --no-pager"

# 2. 301 实际生效(关键) —— 注意 locale-preserving(决议 §G #17)
curl -I https://aidcmo.com/b2b-leads        # 期望 301 → /services
curl -I https://aidcmo.com/en/sample-data   # 期望 301 → /en/services    (保留 EN locale)
curl -I https://aidcmo.com/zh/seo-geo       # 期望 301 → /zh/services    (保留 ZH locale)
curl -I https://aidcmo.com/data-policy      # 期望 301 → /
curl -I https://aidcmo.com/en/data-policy   # 期望 301 → /en             (保留 EN locale)
curl -I https://aidcmo.com/zh/b2b-leads     # 期望 301 → /zh/services
# 顺便测 GET 也 301:
curl -sI -X GET https://aidcmo.com/b2b-leads | head -1   # 期望 HTTP/2 301

# 3. 新端点
curl https://aidcmo.com/api/v1/github-stats
# 期望 JSON: { "stars": <int>, "contributors": <int>, "last_commit_iso": "...", "fetched_at": "..." }

curl -X POST -H 'Content-Type: application/json' \
  -d '{"email":"smoke-test+'$(date +%s)'@example.com"}' \
  https://aidcmo.com/api/v1/waitlist
# 期望 200 { "ok": true }

ssh newyork "sqlite3 ~/.opencmo/data.db 'SELECT COUNT(*) FROM waitlist'"
# 期望 ≥ 1(刚插入的 smoke-test)

# 4. 主页加载
curl -s https://aidcmo.com/ | grep -q "Open-source growth tools"  # 期望 hit
curl -s https://aidcmo.com/ | grep -q "Overseas B2B" || echo "OK no B2B"  # 期望 OK

# 5. 删除 smoke-test 行,不污染真实 waitlist
ssh newyork "sqlite3 ~/.opencmo/data.db \"DELETE FROM waitlist WHERE email LIKE 'smoke-test+%@example.com'\""
```

### D.3 回滚预案

若 smoke 失败:
```bash
ssh newyork "cd /opt/OpenCMO && git log --oneline -5"
# 找到上一个稳定 commit hash
ssh newyork "cd /opt/OpenCMO && git checkout <hash> && systemctl restart opencmo"
# 前端 dist 同样:rsync 旧版本回去
```
SQLite `waitlist` 表在回滚后保留(无害,空表或有 1 行 smoke-test 数据)。

---

## E. 工作量估算(Codex review × 2:8.25h → 11h → 13.75h → **15.5h**)

| 阶段 | 首版 | R1 后 | **R2 后(本次)** | R2 调整原因 |
|---|---|---|---|---|
| B.1 i18n 五语言 | 1.5 h | 3 h | 3 h | 不变 |
| B.2 + B.3 waitlist 后端 | 1 h | 1 h | **1.25 h** | schema 改走 `_SCHEMA` 常量模式(需读 `_db.py` 先) |
| B.4 github-stats 后端 | 0.75 h | 2 h | **2.5 h** | `github_get_with_headers` 实现需重构 `_github_get` 内部 + 多 9 个 test case |
| B.5 服务端 301 | 0.25 h | 0.5 h | **0.75 h** | 加 locale-preserving 逻辑 + HEAD method + 12→ 24 条测试(GET+HEAD) |
| B.6 路由 / nav / 辅助函数 | 0.5 h | 0.5 h | **0.75 h** | 加 `publicRoutes.ts` 改造(R1 漏掉) |
| B.7 新组件 4 个 | 2 h | 2 h | 2 h | BuiltInOpen anyNull 修正成本忽略 |
| B.8 主页改写 | 0.75 h | 1 h | 1 h | 不变 |
| B.9 服务端 SEO + sitemap + llms.txt | — | 1 h | 1 h | 不变 |
| C 测试 | 1 h | 2 h | **2.25 h** | 加 HEAD method 测试 + locale-preserving 测试 |
| D 部署 | 0.5 h | 0.75 h | **1 h** | nginx 配置(限流) + DB 备份 + reload 验证 |
| **合计** | ~8.25 h | ~13.75 h | **~15.5 h** | 约 **2 个工作日** |

---

## F. 风险 & 范围外明确

### F.1 已知风险(本期接受)
- **ja/ko/es 显示 EN fallback** — `I18nProvider` 已有自动回退,体验为短暂英文界面;后续翻译 PR 补
- **GitHub API 不带 token,60 req/h 限流** — 24h 缓存 + 单飞锁 + L2 SQLite 后,单进程一天 ≤ 2 次实际调用,远低于限流
- **`/services` Phase 1 只是 skeleton** — 主 CTA 直接走 `/contact`;Phase 2 ship 时切回
- **waitlist 无双重 opt-in / 无验证邮件** — Phase 1 邮箱可能含 typo;**产品发布前必须做 §F.4 deliverability checklist**
- **CSRF 风险**:`/api/v1/waitlist` 是 unauth 写端点,**不**存在用户账户被盗用风险(账户系统不在公开端点);唯一风险是 spam 提交。已通过 nginx `limit_req` + `source` 白名单 + email regex + `INSERT OR IGNORE` 多层防御。结论:**CSRF 风险等级 = 低**

### F.2 明确不在本期范围
- 任何 OpenCMO 后端**功能性**改动(scan、agent、报告生成等)— 全不动
- Phase 2 的 `/services` 完整 7 section
- 翻译 ja/ko/es
- Stripe / 计费 / waitlist 双重 opt-in / 验证邮件
- 真实 social proof(用户提供 quote 后再补)
- Cloudflare bot / WAF
- 应用层 rate limit(slowapi 等新 dep)— nginx `limit_req` 已覆盖大部分场景

### F.3 部署后 24h 观察项

```bash
# 1. github-stats 稳定返回非 null
ssh newyork "for i in {1..6}; do curl -s https://aidcmo.com/api/v1/github-stats | jq '.stars'; sleep 600; done"
# 期望:6 次都是同一个 int,不是 null

# 2. waitlist 表增长节奏
ssh newyork "sqlite3 ~/.opencmo/data.db 'SELECT source, COUNT(*) FROM waitlist GROUP BY source'"
# 健康节奏:每天个位数;异常 = 被刷

# 3. 老 URL 重定向命中数(Codex 漏项修复)
ssh newyork "grep -E 'GET /(b2b-leads|sample-data|data-policy|seo-geo)' /var/log/nginx/access.log | wc -l"
# 跟踪 30 天,数据用于决定何时取消 301

# 4. 4xx/5xx 比例对比 baseline
ssh newyork "awk '{print \$9}' /var/log/nginx/access.log | sort | uniq -c | sort -rn"

# 5. 429(nginx limit_req 触发)
ssh newyork "grep ' 429 ' /var/log/nginx/access.log | grep waitlist | wc -l"
# 健康:接近 0;若大量,说明真被刷或限流过严
```

### F.4 Phase 2 邮件发送前的 deliverability checklist(Codex 漏项修复)

waitlist 发通知邮件之前必须完成,否则进垃圾箱率会很高:
- [ ] aidcmo.com 配置 **SPF**(`v=spf1 include:_spf.<provider>.com ~all`)
- [ ] aidcmo.com 配置 **DKIM**(provider 给的 selector + public key)
- [ ] aidcmo.com 配置 **DMARC**(`v=DMARC1; p=none; rua=mailto:...` 起步,稳定后切 `p=quarantine`)
- [ ] 现有 `tools/email_report.py:60-63` 的 `From` 字段改用专用 `noreply@aidcmo.com`,不用个人邮箱
- [ ] 第一封批量邮件先发自己 + 测试地址,确认 Gmail/Outlook 都进收件箱
- [ ] 邮件正文必须有清晰退订链接(即使 Phase 1 没收集 unsubscribe state,也至少给个 mailto)
- [ ] (可选)双重 opt-in:发送 confirmation 邮件后才标记 `confirmed=1`

---

## G. 决策一览(本文档锁定,含 Codex review 修订)

| # | 议题 | 首版决议 | **修订后决议(Codex review 后)** | 修订原因 |
|---|---|---|---|---|
| 8 | ja/ko/es 翻译策略 | EN fallback + 每 key 加 `[needs-translation]` 注释 | **只删旧 B2B keys,不新增 / 不加注释**,靠 `I18nProvider:43-51` 自动 EN 回退 | Provider 早就有自动回退,加注释是噪声 |
| 9 | github-stats 缓存层 | 仅进程内存 | **memory(L1) + SQLite(L2) + asyncio.Lock 单飞** | 撤销首版偷懒;原 `new-positioning.md:166-175` 锁定了 SQLite 缓存,且消除冷启动 / 多次部署的重复调用 |
| 10 | 主页主 CTA 目标 | `/contact` | `/contact`(保留) | `/services` Phase 1 是 skeleton,转化弱 |
| 11 | waitlist Phase 1 字段 | 仅 `email` + `created_at` | **加 `source TEXT DEFAULT ''`**,白名单 `{home_inline, hosted_page, ""}` | 不加无法区分两个入口转化;不存 IP(无 retention 政策) |
| 12 | 速率限制 | 不引入新 dep,真被刷再加 | **nginx `limit_req` 写进 §D 部署文档**,5r/min + burst 3 | 公开 unauth 写端点真被刷不是「再说」级别 |
| 13(新) | DB 备份 | — | **schema 变更前 `sqlite3 .backup`,见 §D.0** | Codex R1 漏项;Phase 1 是新功能首次 schema 改动 |
| 14(新) | 老 URL 监控 | — | **nginx access-log 跟踪 4 个老路由命中数**,见 §F.3 | 用于 30 天后决定是否取消 301 |
| 15(新) | 邮件 deliverability | — | **§F.4 checklist**(Phase 1 不阻塞,但发邮件前必须做) | DKIM/SPF/DMARC 缺一就大概率进垃圾箱 |
| **16(R2)** | redirect HTTP 方法 | 仅 GET | **GET + HEAD** | Codex R2:catch-all 同时声明 HEAD,`curl -I` smoke 也是 HEAD;只 GET 会 405 |
| **17(R2)** | redirect 是否保留 locale | 一律去掉 locale 前缀 | **保留**:`/en/b2b-leads` → `/en/services` | Codex R2:用户在 EN 站点击老链接,redirect 后该留在 EN 站,而非弹回根路径 |
| **18(R2)** | DB schema 注册位置 | 在 `ensure_db()` 内 ad-hoc `db.execute(CREATE TABLE...)` | **追加到 `_SCHEMA` 字符串常量**,通过 `executescript` 应用 | Codex R2:跟现有 `site_counters`(`_db.py:136-140`)等表的注册风格保持一致 |
| **19(R2)** | `publicRoutes.ts` 改造 | 未提及 | **必改**:删 4 个老路由,加 `/services` `/hosted`(见 §B.6.1.5) | Codex R2 漏项;不改会破坏 locale 切换器与 AppShell 行为 |

---

**Phase 1 单 PR 范围结束。Phase 2 的 `/services` 7-section 展开 + ja/ko/es 翻译 + waitlist 双重 opt-in 起独立 PR。**

---

## H. Codex Review 修复日志

### H.1 Round 1 修复(7+3+4+4 项)

| 类别 | 数量 | 摘要 |
|---|---|---|
| 🔴 必修 bug | 7 | §B.5 redirect typed Request + 工厂函数;§B.5 注册位置在 catch-all 之前;§B.7.1 apiJson 双前缀 + JSON.stringify;§B.7.2 移除 `@/` 别名;§B.4 部分缓存中毒修复;§B.9 服务端 SEO 文案清理(新增节);§B.9 sitemap.xml + llms.txt 清理 |
| 🟡 模式不一致 | 3 | waitlist 注册到 `storage/__init__.py`;`tools/github_api.py` 增加公开 `get_github_token` + `github_get_with_headers`;复用 `_SEM` 限流 |
| 🟠 决策推翻 | 4 | §G #8 / #9 / #11 / #12 全部按 Codex 反驳重写 |
| ⚪ 漏项补齐 | 4 | §D.0 DB 备份;§D.1.5 nginx limit_req;§F.3 老 URL access-log 监控;§F.4 邮件 deliverability checklist |
| 📏 工时调高 | 1 | 8.25h → 13.75h |

### H.2 Round 2 修复(4+2+1 项)

| 类别 | 数量 | 摘要 |
|---|---|---|
| 🔴 R1 修复后又发现的 bug | 4 | §B.5 redirect 漏 HEAD method(`curl -I` smoke 会 405);§B.5 redirect 丢失 locale 前缀(`/en/b2b-leads` 应 → `/en/services`);§B.3 unused `EmailStr` import → Ruff F401;§B.4 unused `get_github_token` import → Ruff F401;§B.7.3 BuiltInOpen `allNull` 漏检 last_commit_iso |
| 🟡 模式 / 契约 underspecified | 2 | §B.2.2 schema 注册改走 `_SCHEMA` 常量(不再 ad-hoc `db.execute()`);§B.4 `github_get_with_headers` 返回类型从 `Optional[dict]` 改为 `Optional[Any]` + 写明实现契约 |
| ⚪ 漏项 | 1 | §B.6.1.5 `frontend/src/utils/publicRoutes.ts` 必改 |
| 📏 工时再调高 | 1 | 13.75h → 15.5h(约 2 个工作日) |
| 🟢 R1 已确认正确 | 7 | apiJson 修复、`@/` 别名移除、catch-all 位置、partial cache 修复、§B.9 必要性、sitemap/llms 路由真存在、storage helper 风格匹配 |

### H.3 Round 3 修复(3 项,收敛)

| 类别 | 数量 | 摘要 |
|---|---|---|
| 🔴 文档不一致 | 3 | §B.4 wrapper 缺 `Optional` import 提示;§D.2 smoke 期望与 locale-preserving 决议矛盾;§B.1.4 末尾仍有「ja/ko/es 复制 EN + `[needs-translation]` 注释」的遗留 |
| 🟡 契约补充 | 1 | §B.4 加段说明 `_github_get` 仍 raise、`github_get_with_headers` 才 swallow,refactor 时不要改变 `_github_get` 公共契约 |
| 🟢 R2 已确认正确 | 8 | HEAD method、`_build_target` 12 case、`EmailStr` 移除、`get_github_token` 移除、`Optional[Any]` 返回、`anyNull` 三字段、`_SCHEMA` + `executescript`、`publicRoutes.ts` 真存在 |
| ✅ Codex verdict | — | "R2 technical direction converged; fix the three red doc/snippet issues before execution." 本轮已修完 |
