# aidCMO 新定位方案

> 基础事实见 `current-state.md`,以下不再重复盘点。
> 所有文案严格按 [WORKS] 标记的能力撰写,[STUB]/[MISSING] 不出现。
> CTA 优先级(全站统一):**Get a growth audit** > View on GitHub > Join waitlist > Self-host docs

---

## 1.1 主页 Hero 文案三个候选

每个候选给出英文 + 中文 + 副标题。三个方向:**激进**(押注开源 + 对立面)/ **稳健**(直接说人话)/ **技术向**(对开发者创始人)。

### 候选 A — 更激进(站队开源,挑明对立)

**EN H1**: An open-source AI CMO — and the team that runs it for you.
**EN sub**: OpenCMO is the source-available growth engine on GitHub. aidCMO is the team that uses it to deliver SEO, GEO, and content audits for founders who need answers, not another dashboard.

**ZH H1**: 开源的 AI CMO 系统,以及替你跑它的团队。
**ZH sub**: OpenCMO 是 GitHub 上开源的增长引擎。aidCMO 是用它替你交付 SEO、GEO、内容审计的团队 —— 给需要结论、而不是又一块仪表盘的创始人。

**站位**:挑明对立(99 美元 SaaS 黑箱 vs 我们开源)。最强差异化,但语气最有攻击性。

---

### 候选 B — 更稳健(直接,无攻击性)

**EN H1**: Open-source growth tools. Audits delivered by humans.
**EN sub**: OpenCMO scans your SEO, AI search visibility across Perplexity / ChatGPT / Gemini, and 6 community platforms. We set it up, run it, and turn the output into a growth plan.

**ZH H1**: 开源的增长工具,审计由我们交付。
**ZH sub**: OpenCMO 扫描你的 SEO、Perplexity / ChatGPT / Gemini 等 5 个 AI 平台的可见度,以及 6 个社区平台。我们替你跑工具,把结果变成增长计划。

**站位**:最直白,信息密度最高,把"开源"和"人工服务"分两句说清楚。

---

### 候选 C — 更技术向(对会读代码的创始人)

**EN H1**: Read the code. Read the audit. Both are written for founders.
**EN sub**: OpenCMO is a multi-agent SEO/GEO/community audit system, open on GitHub. We use it to deliver growth audits — same engine, with a human reading the output and writing the plan.

**ZH H1**: 先读代码,再读审计 —— 两者都是为创始人写的。
**ZH sub**: OpenCMO 是一套多 agent 的 SEO / GEO / 社区审计系统,开源在 GitHub。我们用它给你交付增长审计 —— 同一套引擎,由人读结果、写计划。

**站位**:把"代码"放到 H1,目标用户是会自己 clone repo 的工程师创始人。最窄,但转化质量最高。

> **决定:选 B(已锁定 2026-04-28)**。i18n 草稿见 1.5「Hero(锁定 B)」。A / C 作为后续 A/B 测试的备选,本期不实现。

---

## 1.2 三层结构落地到路由

### 路由处置(基于 `current-state.md` § 三盘点的现有路由)

| 现有路由 | 处置 | 原因 |
|---|---|---|
| `/` LandingPage | **重写** | 主页换 hero + 三层结构 + Built in the open |
| `/b2b-leads` | **删除 + 301 → `/services`** | 新定位不卖 B2B 数据,但保留 301 防外链 404 |
| `/sample-data` | **删除 + 301 → `/services`** | B2B 转化路径 |
| `/data-policy` | **删除 + 301 → `/`** | 整页都是 B2B 数据合规说明,新定位下没意义 |
| `/seo-geo` | **重命名 → `/services`,加 301 redirect** | URL 升级为通用「服务」,但保留旧链接 |
| `/open-source` | **保留并扩展** | 这就是 OpenCMO 项目页,新定位下要更突出 |
| `/contact` | **保留并精简** | 删掉 4 个 B2B 咨询类型,只留服务咨询 |
| `/sample-audit` | **保留** | 真实 demo audit,正好匹配新定位「show, don't tell」 |
| `/blog`, `/blog/:slug` | **保留** | 内容资产 |
| **新增** `/hosted` | 新建 | 托管版 waitlist 静态页(仅 Coming soon + 邮箱表单) |

### 服务层 landing page 信息架构(`/services`)

> **Phase 1 只实现** section 1 (Hero) + section 8 (CTA) 的占位版本(hero + 主 CTA + 一行「完整版即将上线」);section 2-7 留 Phase 2 展开(详见 1.8 Q3)。下面 IA 是 Phase 2 目标态。

```
1. Hero
   - H1: "Get a growth audit"
   - Sub: 一句话说清楚做什么、谁交付、用什么工具
   - 主 CTA: "Book a 30-min call" → /contact 或外部日历

2. Pain (3 card)
   - "We're invisible to ChatGPT and Perplexity"
   - "Traffic is flat and I can't tell why"
   - "I don't know which channel deserves my time next month"

3. What you actually get (sample artifact)
   - 截图或链接到 /sample-audit
   - 三个 deliverable bullets:
     a) 多 agent 6 阶段 SEO/GEO 报告(PDF + HTML)
     b) 5 个 AI 平台的可见度评分 + 改进项清单
     c) 30 天内可执行的内容/外链/技术改动 backlog

4. Process (4 step)
   - Brief → Run scans → Read & synthesize → Plan
   - 每步标注「by you」/「by us」,透明

5. What's under the hood (引导到 OpenCMO)
   - 一段简短文字 + "View OpenCMO on GitHub" link
   - 不重复「Built in the open」section,这里是简化版引流

6. Pricing (占位符)
   - One-time audit: $[user-supplied]
   - Monthly retainer: $[user-supplied]
   - Custom (multi-region / enterprise [user-supplied 是否要这个档])
   - **三档名字也由你定**(我列了占位)

7. FAQ
   - "Can I just self-host OpenCMO and skip the audit?" → "Yes, repo is here. The audit is when you'd rather not."
   - "Do I need to give you my analytics access?" → "Only Search Console (read-only) and your sitemap. No third-party platform passwords."
   - "Is there a refund?" → [user-supplied]
   - "How long until I see the report?" → [user-supplied,我建议 5 个工作日]
   - "Can you publish content for me?" → "Drafting yes. Auto-publishing only on Reddit and Twitter, with human approval. Other platforms we hand you the draft."

8. CTA
   - "Get a growth audit" → /contact
```

### 托管版 waitlist 的最简实现

**主页内嵌一节 + 独立 `/hosted` 静态页(同一组件,两处复用)。**

- **Phase 1**(本期):静态页 + 邮箱表单 → `POST /api/v1/waitlist` 自家端点 + SQLite `waitlist(email TEXT PRIMARY KEY, created_at TEXT)` 表。**无 mailto / Tally 兜底**(1.8 Q4 决议)。
- **Phase 2**:ready 时人工 `SELECT email FROM waitlist` 批量发一封通知邮件。**不接 Stripe,不做 drip 序列**。

文案诚实:
- "Coming soon" 不写时间
- 不放任何 fake 进度条 / "X people on waitlist" 数字
- 表单只收 email + 一个可选的「最想要的能力」复选框(SEO 审计 / 多平台监控 / 内容草稿生成 / 全部)

---

## 1.3 GitHub social proof 策略

### Hero 区(主页第一屏)

**只放**:`<a href="https://github.com/Lling0000/OpenCMO" />` + Star 图标 + 文案 "View on GitHub"
**不放**:数字。原因 task.md 已说明 —— 73 stars 在 hero 里太小,放了反而劝退。

### "Built in the open" 区块(主页第二屏)

**布局**:`H2 + sub + 3-col stat cards + CTA`

```
[H2]   Built in the open.
[sub]  OpenCMO is the open-source engine behind every audit we deliver.

┌─────────────────────┐ ┌─────────────────────┐ ┌─────────────────────┐
│   {N} stars         │ │   Last commit       │ │   {M} contributors  │
│   on GitHub         │ │   {relative time}   │ │                     │
└─────────────────────┘ └─────────────────────┘ └─────────────────────┘

[link]  See the code, file an issue, or fork it →
```

中文版镜像:
- H2: "在公开仓库里构建。"
- sub: "OpenCMO 是我们每份审计背后的开源引擎。"
- Stat 1: "{N} GitHub stars"
- Stat 2: "最近一次提交 · {relative time}"
- Stat 3: "{M} 位贡献者"
- link: "看代码、提 issue,或 fork →"

### 数据来源 + 缓存

**新增后端端点**:`GET /api/v1/github-stats`

实现:
```
1. 内存 + SQLite 缓存层,TTL = 24h
2. 缓存命中:直接返回
3. 缓存未命中:并发请求两个 GitHub API
   a. https://api.github.com/repos/Lling0000/OpenCMO
      → 取 stargazers_count / forks_count / open_issues_count / pushed_at
   b. https://api.github.com/repos/Lling0000/OpenCMO/contributors?per_page=1&anon=true
      → 解析 Link header 的 last page,得到贡献者总数
4. 异常处理:任一 API 失败 → 返回 { stars: null, contributors: null, last_commit: null }
   前端检测到 null → 整个 stat card 区域不渲染,只渲染 "View on GitHub" 链接
5. 缓存写入 SQLite(避免重启丢失) + 内存(避免每次都查 SQLite)
```

**前端 hook**:`useGitHubStats()` (TanStack Query, staleTime 24h, retry 1, 失败回 null,组件根据 null 决定降级渲染)

**为什么走后端代理而不是浏览器直连**:
- 共享缓存(所有访客共用 24h 缓存,不是每个浏览器各自缓存)
- 不暴露 IP 给 GitHub(60 req/h 免登录限流容易踩)
- 服务端可以加个可选 token 把限流提到 5000 req/h(`OPENCMO_GITHUB_TOKEN`,可选)

---

## 1.4 删除内容清单

> 引用行号基于 `current-state.md` § 三第 5 条(B2B 文案分布)。中英文同步删除。

### 整个 i18n 命名空间删除(EN + ZH)

| 命名空间 | 文件位置 | 影响页面 |
|---|---|---|
| `service.b2b.*` | `en.ts:682-723` / `zh.ts` 同结构 | `/b2b-leads` 整页 |
| `service.sample.*` | `en.ts:805-827` / `zh.ts` | `/sample-data` 整页 |
| `service.policy.*` | `en.ts:880-916` / `zh.ts` | `/data-policy` 整页 |

### 单 key 删除

| Key | 现内容 (EN 摘录) | 处置 |
|---|---|---|
| `landing.serviceLeadsTitle` | "Overseas B2B email leads" | 删 |
| `landing.serviceLeadsDescription` | "Filter target accounts by country, region, industry, job title, company size..." | 删 |
| `landing.serviceCleanTitle` | "Email verification and data cleaning" | 删 |
| `landing.serviceCleanDescription` | (邮箱清洗描述) | 删 |
| `landing.b2bSection*` (656-680 范围) | B2B 卡片标题、副标题、合规细则 | 删 |
| `landing.desktopPreviewTitle` | "A cleaner B2B lead table, not a spam tool." | 删 |
| `service.contact.b2bInquiry*` | 「B2B lead data」咨询类型卡片相关 | 删 |
| `nav.b2bLeads` | "B2B leads" | 删 |
| `nav.dataPolicy` | "Data policy" | 删 |

### 单 key 重写(不删 key,只改 value)

| Key | 现内容 | 新内容 |
|---|---|---|
| `landing.heroEyebrow` | "Overseas B2B lead data + SEO/GEO growth services" | (按 1.5) |
| `landing.heroTitle` | "Overseas B2B lead data and SEO/GEO growth services." | (按选定 hero 候选) |
| `landing.heroSubtitle` | (B2B 招客户副标题) | (按选定候选副标题) |
| `landing.metaTitle` | "aidCMO \| Overseas B2B Leads and SEO/GEO Growth Services" | (按 1.5) |
| `landing.metaDescription` | (含 B2B leads / email verification) | (按 1.5) |
| `footer.publicTagline` | "By OpenCMO technical support of B2B growth services" | (按 1.5) |
| `footer.publicDescription` | "Overseas B2B lead data and SEO/GEO growth services with OpenCMO technical support." | (按 1.5) |
| `service.seoGeo.*` | 整组(标题、卖点、流程) | 全套重写,见 1.5 服务页文案 |
| `service.openSource.*` | 整组(OpenCMO 介绍) | 重写为更详细的 OpenCMO 项目页文案 |
| `service.contact.*` | 整组(含 B2B 咨询类型) | 精简,删 B2B inquiry 类型,留服务咨询 |

---

## 1.5 新增内容清单(EN + ZH 双份)

### Hero(锁定 B,2026-04-28)

```ts
en: {
  heroEyebrow: "Open-source. Audit-first.",
  heroTitle: "Open-source growth tools. Audits delivered by humans.",
  heroSubtitle:
    "OpenCMO scans your SEO, AI visibility across 5 AI search engines (Perplexity, ChatGPT, Gemini, Claude, You.com), and 6 community platforms. We set it up, run it, and turn the output into a growth plan.",
  heroPrimaryCta: "Get a growth audit",
  heroSecondaryCta: "View on GitHub",
}

zh: {
  heroEyebrow: "开源 · 审计优先",
  heroTitle: "开源的增长工具,审计由我们交付。",
  heroSubtitle:
    "OpenCMO 扫描你的 SEO、5 个 AI 搜索引擎(Perplexity、ChatGPT、Gemini、Claude、You.com)的可见度,以及 6 个社区平台。我们替你跑工具,把结果变成增长计划。",
  heroPrimaryCta: "预约一次增长审计",
  heroSecondaryCta: "前往 GitHub",
}
```

**与 1.1 候选 B 的差异说明**:
- 副标题中 AI 平台从 3 个补全为 5 个(Perplexity / ChatGPT / Gemini / Claude / You.com),与 1.6 能力清单严格一致 —— 1.1 候选稿只列 3 个是为了节奏,落到 i18n 必须补全,否则等于在 hero 漏掉了 Claude 和 You.com 这两个 [WORKS] 平台
- 新增 `heroEyebrow`(短标语,在 H1 上方一行小字),原 i18n 已有该 key,沿用
- 主 / 次 CTA 拆成两个独立 key,方便组件单独引用

### Built in the open(新增 namespace `landing.builtInOpen.*`)

```ts
en: {
  builtInOpen: {
    title: "Built in the open.",
    subtitle: "OpenCMO is the open-source engine behind every audit we deliver.",
    statStars: "{count} GitHub stars",
    statLastCommit: "Last commit · {time}",
    statContributors: "{count} contributors",
    fallbackStat: "View on GitHub",
    cta: "See the code, file an issue, or fork it →",
  }
}

zh: {
  builtInOpen: {
    title: "在公开仓库里构建。",
    subtitle: "OpenCMO 是我们每份审计背后的开源引擎。",
    statStars: "{count} GitHub stars",
    statLastCommit: "最近一次提交 · {time}",
    statContributors: "{count} 位贡献者",
    fallbackStat: "前往 GitHub",
    cta: "看代码、提 issue,或 fork →",
  }
}
```

### Hosted waitlist(新增 namespace `landing.hosted.*` + 独立 `service.hosted.*`)

主页区块版(短):
```
EN
title: "Don't want to self-host? Get on the waitlist."
subtitle: "We're working on a hosted version of OpenCMO. No date yet — we'll only email when it's ready."
inputPlaceholder: "you@company.com"
submitButton: "Notify me"
note: "No drip sequences. One email when it ships."
```

```
ZH
title: "不想自己部署?加入 waitlist。"
subtitle: "OpenCMO 托管版正在做,还没有发布日期 —— ready 之后只发一封通知邮件。"
inputPlaceholder: "you@company.com"
submitButton: "提醒我"
note: "不会有营销邮件。发布时只发一封。"
```

### Footer tagline + description

```
EN
publicTagline: "Open-source AI growth tools. Audits delivered by humans."
publicDescription: "OpenCMO is open source on GitHub. aidCMO uses it to deliver SEO, GEO, and content audits for founders."

ZH
publicTagline: "开源的 AI 增长工具,审计由我们交付。"
publicDescription: "OpenCMO 在 GitHub 上开源,aidCMO 用它替创始人交付 SEO、GEO、内容审计。"
```

### Meta title / description

```
EN
metaTitle: "aidCMO — Open-source AI CMO with growth audits delivered by humans"
metaDescription: "OpenCMO is the open-source SEO/GEO/community audit engine. aidCMO uses it to deliver growth audits for founders who need answers, not another dashboard."

ZH
metaTitle: "aidCMO — 开源 AI CMO,代为交付的增长审计"
metaDescription: "OpenCMO 是开源的 SEO / GEO / 社区审计引擎。aidCMO 用它替创始人交付增长审计 —— 给需要结论而不是又一块仪表盘的人。"
```

### Service landing page(`service.seoGeo.*` 重写,Phase 2 真正落地;Phase 1 只占位)

主要 key 草稿(EN + ZH 同结构,中文写作要等定稿后给):
```
service.audit: {
  heroTitle: "Get a growth audit.",
  heroSubtitle: "Run by us. Powered by OpenCMO.",
  
  painsTitle: "Three reasons founders ship us a brief.",
  pain1: "We're invisible to ChatGPT and Perplexity.",
  pain2: "Traffic is flat and we can't tell why.",
  pain3: "We don't know which channel deserves the next month.",
  
  deliverableTitle: "What you get.",
  deliverable1: "A multi-agent SEO / GEO / community report (PDF + HTML).",
  deliverable2: "AI visibility scores across 5 platforms with a fix list.",
  deliverable3: "A 30-day backlog of content, links, and technical changes.",
  
  processTitle: "How we work.",
  process1: "Brief — you fill a 10-question form.",
  process2: "Run — we configure OpenCMO and run scans.",
  process3: "Read — we read the output and grade each section.",
  process4: "Plan — you get the report, the backlog, and one call.",
  
  pricingTitle: "Pricing.",
  pricing1Label: "Audit",
  pricing1Price: "[user-supplied]",
  pricing1Detail: "One-time, full report + 30-min walkthrough.",
  pricing2Label: "Monthly",
  pricing2Price: "[user-supplied]",
  pricing2Detail: "Monthly scan + monthly recommendation update.",
  pricing3Label: "Custom",
  pricing3Price: "Talk to us",
  pricing3Detail: "Multi-market, multi-language, or co-pilot setup.",
  
  ctaPrimary: "Get a growth audit",
  ctaSecondary: "View OpenCMO on GitHub",
}
```

### `/open-source` 页面文案补强(`service.openSource.*` 扩展)

新增 section:Self-host quick start(三步)、Roadmap(可选,链接到 GitHub)、Contributing(链接到 CONTRIBUTING.md)

---

## 1.6 OpenCMO 能力对外展示清单

> 严格基于 `current-state.md` 中标注 [WORKS] 的能力。
> 以下每条都可以放在 `/`、`/services`、`/open-source` 任意页面。
> [STUB] / [MISSING] 能力一律不出现。

### 允许写入文案的能力

**SEO / 站点诊断**
- On-page SEO 诊断 + Core Web Vitals(基于 PageSpeed Insights)
- robots.txt / sitemap.xml / schema.org 结构化数据检测
- 多页站点抓取 + 内链结构图 + meta 审计
- AI 爬虫识别(GPTBot / ClaudeBot / PerplexityBot)
- `/llms.txt` 校验和生成
- Landing page CTA 质量审计
- 关键词建议
- 内容更新频率检测

**GEO / AI 可见度**
- 5 个 AI 平台的可见度扫描:**Perplexity / You.com / Claude / ChatGPT / Gemini**
- 内容可被 AI 引用的可能性评分(citability)
- 品牌足迹扫描:**YouTube / Reddit / Wikipedia / Wikidata / LinkedIn**

**SERP**
- 关键词排名追踪(基于 DataForSEO)
- 关键词趋势 / SERP gap 分析
- 竞品图谱 / 关键词重叠

**社区监控(read-only)**
- 监控 6 个平台:**Reddit / Hacker News / Dev.to / YouTube / Bluesky / Twitter**
- 讨论详情抓取 + 历史快照对比

**内容生成(草稿,不自动发布)**
- 平台特化的草稿生成,覆盖 20 个平台 agent —— 海外:Twitter/X、Reddit、LinkedIn、Product Hunt、HN、Dev.to、Bluesky、YouTube、Blog、阮一峰周刊;国内:知乎、小红书、V2EX、掘金、即刻、公众号、OSChina、GitCode、少数派、InfoQ
- ⚠️ 注意措辞:**写「drafts content for」不是「publishes to」**

**发布(双重 gate,默认 dry-run)**
- 仅 Reddit + Twitter 支持真实发布,且需 `OPENCMO_AUTO_PUBLISH=1` + 平台凭证 + 人工 approve
- 文案上写:"Approval-first publishing for Reddit and Twitter"
- ⚠️ 不要泛化成「auto-publishes to all 20 platforms」—— 那是 [STUB]

**报告**
- 6 阶段多 agent 周报流水线(reflection → insight → outline → writers → grader → synthesizer)
- HTML + Markdown 输出
- SMTP 邮件投递
- 可由 APScheduler 自动定时触发

**3D 知识图谱**
- 竞品 / 关键词 / 讨论 / SERP 节点的 3D 渲染
- 实时 BFS 扩展

**GitHub outreach**
- GitHub 用户发现 + 评分(基于 follower 链)

### 严格禁止出现在文案里的内容

| 类别 | 禁止文案示例 |
|---|---|
| 多租户 | "Team workspaces", "SSO", "Enterprise plan", "SOC 2", "Multi-tenant" |
| SLA / uptime | "99.9% uptime", "24/7 support", "Production SLA" |
| 编造的 social proof | "Trusted by 100+ developers", "Loved by founders", "1,000+ teams use OpenCMO" |
| 编造的 testimonial | 任何带人名 / 公司名 / 头像的引语,除非用户明确给到真实素材 |
| 不存在的发布能力 | "Auto-publishes to LinkedIn / Product Hunt / WeChat / Xiaohongshu / Douyin" — 这 5 个平台是 [STUB] |
| Search Console 端到端 | "One-click Search Console import" — GSC 是 [STUB],只能写「读 sitemap」 |
| 计费 / 配额 | "Pay per scan", "Quota plans" — Stripe / billing 是 [MISSING] |
| 合规 | "GDPR compliant", "CCPA compliant" 单独出现等于暗示我们做了合规工作 —— 实际没做,放进文案要负法律责任 |
| 空话 | "赋能"、"一站式"、"全方位"、"打造"、"助力"、"empower"、"unlock"、"unleash" 全部禁用 |

---

## 1.7 导航重构

### 当前导航(要被替换)

`frontend/src/content/marketing.ts` 的 `PUBLIC_HOME_NAV`:
```
B2B leads → /b2b-leads
SEO/GEO → /seo-geo
OpenCMO → /workspace          ← 错误:营销链接到 dashboard,会让访客困惑
Data policy → /data-policy
Contact → /contact
Blog → /blog
```

### 新导航(5 项)

```
Services        → /services           (从 /seo-geo 重命名)
OpenCMO         → /open-source         ← 改为指向项目介绍页,不再指向 /workspace
Audit example   → /sample-audit
Blog            → /blog
Contact         → /contact
```

右上角不变,但内容更新:
- 语言切换(EN / ZH)
- "Source code" 图标按钮 → GitHub 仓库(外链,不带数字)
- 主 CTA 按钮:**"Get a growth audit"** → /services 或 /contact(等 1.5 定稿决定)

### 关键变更说明

1. **删除** "B2B leads" 和 "Data policy" —— 路由也删,加 301
2. **重命名** "SEO/GEO" → "Services",URL `/seo-geo` → `/services`(老 URL 加 301)
3. **修正** "OpenCMO" 链接 —— 当前指向 `/workspace`(已认证 dashboard),改为指向 `/open-source`(项目页)。原来的设计意图大概是「让人快速进入产品」,但访客没有账号会被弹去登录页,体验断裂
4. **新增** "Audit example" → `/sample-audit` —— 让访客在不掏钱的前提下看到真实交付物
5. **托管版 waitlist 不进顶部导航** —— 它是次级路径,放 footer 即可,避免与主 CTA 抢注意力

### 移动端

汉堡菜单内容相同,5 项 + 主 CTA 按钮 + 语言切换。`Source code` 在汉堡菜单底部作为脚注。

### Footer 导航补充

新增一栏 "Hosted version (waitlist)" 链接 → `/hosted`

---

## 1.8 决策表(2026-04-28 锁定)

| # | 议题 | 决议 | 影响 |
|---|---|---|---|
| 1 | Hero 候选 | **B**(稳健) | i18n 草稿见 1.5「Hero(锁定 B)」;A / C 留作未来 A/B 测试备选,本期不实现 |
| 2 | 服务定价档位名 | `Audit / Monthly retainer / Custom` | 1.5 `service.audit.pricing*` 已按此结构;价位字段保持 `[user-supplied]` 占位 |
| 3 | `/services` 落地节奏 | **Phase 1 只做 skeleton**(hero + 主 CTA + 「完整版即将上线」占位文案);Phase 2 展开 1.2 全部 7 个 section | 1.2 IA 视为 Phase 2 目标态 |
| 4 | Waitlist Phase 1 形态 | **(c) 自家 `/api/v1/waitlist` + SQLite `waitlist(email, created_at)` 表** | 不走 mailto / Tally 兜底,Phase 2 无迁移成本 |
| 5 | 引用真实社区 quote 作为 social proof | **Phase 1 不上**;等用户主动贴 Linux.do / HN / X 链接后再加 | 任务约束禁止编造 testimonial,真实引语合规但本期无素材 |
| 6 | `/workspace` 是否从公开导航拿掉 | **拿掉**;`OpenCMO` nav 项指向 `/open-source` | 见 1.7;`/workspace` 路由保留,但仅 `/login` 内部跳转可达 |
| 7 | `OPENCMO_GITHUB_TOKEN` 环境变量 | **不加** | 24h 缓存 + 单端点对 60 req/h 限流足够;后续真踩到限流再加 |

---

**1.1–1.8 全部锁定。implementation-plan.md 基于此文档撰写。**
