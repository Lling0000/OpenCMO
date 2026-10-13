# aidCMO / OpenCMO 现状盘点

> 这份文档只记录代码里能直接证明的事实。每条结论都给出 `file:line` 引用,避免后续基于猜测做决策。
>
> 标记说明:**[WORKS]** 端到端跑通 · **[DEGRADED]** 关键依赖缺失时降级运行 · **[STUB]** 仅占位,无实现 · **[MISSING]** 完全没写

---

## 一、OpenCMO 真实能力边界

### 1. Agent 编排层(能力多,且基本都跑得通)

- **CMO 主编排器** — `src/opencmo/agents/cmo.py:151-374`,挂了 40+ 工具,负责把请求分发到平台专家。
- **核心情报 agents**(全部 [WORKS]):
  - SEO Audit Expert(`agents/seo.py`)
  - AI Visibility / GEO Agent(`agents/geo.py`)— 真实扫 Perplexity / You.com / Claude / ChatGPT / Gemini 5 个平台
  - Community Monitor(`agents/community.py`)
  - Trend Research Agent(`agents/trend.py`)
  - GitHub Outreach Agent(`agents/github.py`)
- **平台内容专家**(20 个,大部分用作 `as_tool` 给主编排器调用):
  - 海外:Twitter/X、Reddit、LinkedIn、Product Hunt、HN、Dev.to、Bluesky、YouTube、Blog/SEO、阮一峰周刊
  - 国内:知乎、小红书、V2EX、掘金、即刻、微信公众号、OSChina、GitCode、少数派、InfoQ
- 同一个文件里既有「能写文案的 agent」,也有「能扫数据的 agent」,**这是 OpenCMO 真正的差异点**。

### 2. 工具层(`src/opencmo/tools/`)— 区分清楚跑得通的和不跑的

| 模块 | 状态 | 备注 |
|---|---|---|
| `seo_audit.py` | **[WORKS]** | On-page SEO + Core Web Vitals(PageSpeed Insights) + robots / sitemap / schema 检测,有真实健康分 |
| `serp_tracker.py` | **[WORKS]** 需 DataForSEO 凭证 | 没凭证时返回空,不报错 |
| `geo.py` + `citability.py` + `brand_presence.py` | **[WORKS]** | AI 可见度扫描真实跑;Perplexity / You.com 免费,Claude / GPT / Gemini 需 key |
| `community.py` + `community_providers.py` | **[WORKS]** 6 个平台 | Reddit / HN / Dev.to / YouTube / Bluesky / Twitter 默认开启 |
| `community_providers.py:1648-2303` | **[STUB]** | LinkedIn / PH / WeChat / Xiaohongshu / Douyin 的发布层都是 stub,只有读没有写 |
| `ai_crawler_check.py` + `llmstxt.py` | **[WORKS]** | GPTBot / ClaudeBot / PerplexityBot 检测、`/llms.txt` 校验 + 生成 |
| `site_audit.py` + `keyword_suggest.py` + `cta_audit.py` + `content_frequency.py` | **[WORKS]** | 都依赖 crawl4ai + LLM,无外部 SaaS 依赖 |
| `graph_intel.py` | **[WORKS]** | 竞品图谱 / 关键词重叠 / SERP gap |
| `github_discovery.py` | **[WORKS]** | 用 GITHUB_TOKEN 抓 follower 链做 outreach 评分 |
| `publishers.py` | **[DEGRADED]** | Reddit / Twitter 发布默认 dry-run,真发要 `OPENCMO_AUTO_PUBLISH=1` + 平台凭证 |
| `gsc.py` | **[STUB]** | Google Search Console 需自己跑 OAuth,没做端到端流程 |
| `email_report.py` | **[WORKS]** 需 SMTP | scheduler 触发周报邮件 |

### 3. 扫描 / 监控工作流

- **SEO / GEO / Community / SERP 四类扫描** 都有真正的实现(`scheduler.py:83-157`),从 `web/app.py` 的 `/api/v1/projects/{id}/scan?type=...` 触发,或由 APScheduler 按 cron 执行。
- **APScheduler 是可选依赖**(`pyproject.toml:23`),没装就走优雅降级。装上之后默认开启,可用 `OPENCMO_ENABLE_SCHEDULER=0` 关。

### 4. 报告生成 — 这是 OpenCMO 真正能拿出来卖的东西

- **`reports.py` + `report_pipeline.py`**:周报走六阶段多 agent 流水线(Reflection → Insight Distiller → Outline Planner → Section Writers → Section Grader → Synthesizer),不是单次 LLM 调用。
- 输出 Markdown + HTML;评分 < 3.5/5 的章节最多重写一次。
- 邮件投递走 `email_report.py`,scheduler 触发,SMTP 缺失时只报错不发。

### 5. 前端 — 20 个页面,基本都跑得通真实数据

`frontend/src/pages/` 下 18+ 个 dashboard 页面全部连真实 DB,3D 知识图谱(`GraphPage`)从 `/api/v1/projects/{id}/graph` 拉真实节点 / 边,不是 mock。

---

## 二、🚨 关键风险:OpenCMO 还没准备好做「托管版」

> task.md 的新定位里有一层是「OpenCMO 托管版(用户付钱不想自己部署)」。**代码层面这个能力今天不存在**,需要明确告诉你这点。

按 `cmo.py / web/app.py / storage.py` 直接看代码:

| 维度 | 现状 | 引用 |
|---|---|---|
| **多租户隔离** | **[MISSING]** projects 表只有 `brand_name + url` 唯一约束,没有 `user_id` 列 | `storage.py` schema |
| **用户体系** | **[MISSING]** 没有 signup / OAuth / 团队 / 权限 | `web/app.py` 只有单 token |
| **认证** | **[MISSING]** 单 `OPENCMO_WEB_TOKEN`,所有人共享同一个登录 | `web/app.py` Bearer 校验 |
| **数据隔离** | **[MISSING]** 单一 SQLite 文件,任何 `project_id` 都能从任何 endpoint 查到 | `~/.opencmo/data.db` |
| **支付 / 计费** | **[MISSING]** 没有 Stripe、没有定价、没有用量配额 | 全代码无 stripe / billing |
| **限流 / 用量计量** | **[MISSING]** 没有 per-user rate limit,没有 scan 计数 | 无 |
| **API key 模型** | **BYOK only** ContextVar 方案是「每个请求带自己的 key」,**没有 platform key 兜底**;意味着托管版用户必须自带 OpenAI/Anthropic key,平台不能用自己的 key 给用户算 | `llm.py` |

**翻译成大白话**:

> 今天的 OpenCMO 是单租户、单 token、必须 BYOK 的个人 dashboard。如果你要卖「托管版」给一个不懂部署的用户,你要么:
> (a) 给每个客户单独跑一台 VM(成本不划算,客单价撑不起);
> (b) 写一遍多租户基础设施 — user 表 / 项目 owner / 行级隔离 / 计费 / 限流 / Stripe / 平台 key — 这是 4-6 周的工程量,不是「Phase 2 两周内」能搞完的。

**我的建议**(请确认):

把 task.md 第二步的三层结构调整为:

1. **免费层**:OpenCMO 开源自部署(GitHub) ← 今天可交付
2. **服务层**:增长咨询 + 人工解读报告(用 OpenCMO 跑数据,但**人来交付**) ← 今天可交付
3. **托管版**:列入 roadmap,**先做 waitlist 不做产品**,等多租户基础设施补完再放出来

这样 Phase 1 / Phase 2 都不需要写多租户;Phase 3 只是 landing page + Stripe 购买入口,不绑死交付时间。要硬上托管版,就要把 4-6 周的多租户重写当作显式 work item 列出来。

---

## 三、aidCMO 公开站现状

### 1. 路由结构(public 部分)

- `/` LandingPage — 当前主页
- `/b2b-leads` PublicServicePage(B2B 数据)
- `/seo-geo` PublicServicePage(SEO/GEO 服务)
- `/open-source` PublicServicePage(OpenCMO 项目)
- `/sample-data` PublicServicePage(样本申请)
- `/contact` PublicServicePage(联系表单)
- `/data-policy` PublicServicePage(数据合规说明)
- `/blog` + `/blog/:slug`
- `/sample-audit`
- 全部支持 `/en/*` 和 `/zh/*` 双语前缀

`/workspace` 及其子路由是**已认证 dashboard**,不是营销页。

### 2. 主页核心文案(`frontend/src/pages/LandingPage.tsx` + `i18n/locales/en.ts:408-635`)

- **Hero H1**:"Overseas B2B lead data and SEO/GEO growth services."
- **Hero 副标题**:"We help exporters, SaaS teams, manufacturers, and service companies find target overseas accounts by country, industry, role, and company type, then improve acquisition efficiency through search and AI visibility."
- **Eyebrow**:"Overseas B2B lead data + SEO/GEO growth services"
- **Meta title**:"aidCMO | Overseas B2B Leads and SEO/GEO Growth Services"
- **三卡片产品矩阵**:
  1. 海外 B2B 邮箱线索 → `/b2b-leads`
  2. 邮箱验证与数据清洗 → `/data-policy`
  3. SEO/GEO 增长服务 → `/seo-geo`

### 3. 顶部导航(`frontend/src/content/marketing.ts` PUBLIC_HOME_NAV)

```
B2B leads → /b2b-leads
SEO/GEO   → /seo-geo
OpenCMO   → /workspace          ← 注意:导航上叫 OpenCMO,链接到 dashboard
Data policy → /data-policy
Contact → /contact
Blog → /blog
```

右上角:语言切换 / `hello@aidcmo.com` 邮件按钮 / Source Code(GitHub 链接)/ "Get sample data" 主 CTA。

### 4. Footer(`SiteFooter.tsx` variant="public")

- Logo + tagline:"By OpenCMO technical support of B2B growth services"
- 描述:"Overseas B2B lead data and SEO/GEO growth services with OpenCMO technical support."
- Action 链接:邮件 / Blog / Get sample data
- 卡片:Email、GitHub 仓库、友链(Okara AI)
- Stats:从 API 拉的访问量 / UV

### 5. 全站 B2B 相关文案清单(需要被删 / 改的)

`frontend/src/i18n/locales/en.ts` 和 `zh.ts` 里至少有 **~700 个 B2B 相关 key**,主要分布在:

- `landing.heroTitle / heroEyebrow / heroSubtitle`(主 hero)— 第 423-428 行
- `landing.metaTitle / metaDescription`(SEO meta)— 409-410 行
- `landing.serviceLeadsTitle / serviceCleanTitle`(产品矩阵卡片)— 635-641 行
- `landing.b2bSection*`(B2B 说明区)— 656-680 行
- `service.b2b.*` 整页(`/b2b-leads`)— 682-723 行
- `service.sample.*` 整页(`/sample-data`)— 805-827 行
- `service.contact.*` 整页(`/contact`)— 843-875 行(含 4 类咨询入口里有 "B2B lead data")
- `service.policy.*` 整页(`/data-policy`)— 880-916 行
- `footer.publicTagline / publicDescription` — 189 行附近
- 中文 `zh.ts` 同结构镜像

### 6. OpenCMO 在公开站当前的呈现

- **导航第 3 项**叫 "OpenCMO" → `/workspace`(让访客直接看 dashboard 入口)
- **主页有一段** `LandingPage.tsx:363-402` 标题:"OpenCMO stays as the open-source growth system behind the method"
- **/open-source 整页** 已经存在,标题:"OpenCMO is the technical support behind our growth method"
- **Footer** 有 GitHub 卡片、tagline 写 "By OpenCMO technical support"
- **Header** "Source Code" 按钮直链 https://github.com/Lling0000/OpenCMO

**所以现状不是「OpenCMO 没出现」**,而是「OpenCMO 被定位成 B2B 数据生意的技术背书」。新定位需要把主从关系反过来。

### 7. 最近的提交 / 未提交改动

- **`b98873e feat: reposition public site for b2b growth services`**(2026-04-27)— 这就是当前 B2B 定位的来源。改了 13 个文件,LandingPage 重写(+1155 / -960),新建 `PublicServicePage.tsx`(548 行),i18n 加了 ~700 个 key。**这就是要回滚 / 重写的目标**。
- **`b5917e0 fix: route opencmo nav to workspace`** 把 OpenCMO 导航指向 `/workspace`
- **`9043e40 fix: describe opencmo as technical support`** 把文案改成「技术支持」
- **未提交改动**(可能跟本任务无关,是另一条线)
  - `frontend/src/components/layout/AppShell.tsx` — 背景色和 max-width 改动
  - `frontend/src/components/project/ProjectCommandCenter.tsx`
  - `frontend/src/pages/ProjectPage.tsx` — 重命名 ProjectCommandCenter → ProjectAgentGrid
  - `frontend/src/components/project/ProjectHero.tsx` — 新文件,5.6KB,Project hero 组件
  - 这些都在 `/workspace` 内部,**和公开站重新定位无直接冲突**,但需要在动手前先确认是否要保留。

---

## 四、历史待确认事项与归属更新

以下是原阶段的待确认事项；第 3 项归属已于 2026-10-13 核验并统一。

1. **托管版怎么办?** 接受我上面的「先做 waitlist、不做产品」建议?还是要 task.md 第二步原样输出三层结构?(后者我会在 Phase 2 / Phase 3 显式列出 4-6 周的多租户工程量)

2. **未提交的 ProjectHero / AppShell 改动** 要保留还是丢掉?这些是 dashboard 内部的样式重构,跟公开站重新定位是两条线。我建议先 stash 起来,Phase 1 完成后再回来收。

3. **GitHub 归属已确认**：OpenCMO 当前仓库为 `Lling0000/OpenCMO`，所有者与维护者是 Ling（`Lling0000`），本目录使用 Ling 的 `gh` 配置操作。该归属无需重复确认。主页 Stars / Forks 社会证明应读取当前仓库的真实数据，不使用编造数字。

仓库归属不再列为待确认项；其余事项仅保留为原阶段的历史记录。
