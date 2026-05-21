<div align="center">
  <img src="assets/logo.png" alt="OpenCMO Logo" width="120" />
</div>

<h1 align="center">OpenCMO</h1>

<p align="center">
  <strong>OpenCMO 是把 SEO、GEO、SERP 和社区监控整合在一起的开源增长系统。</strong><br/>
  <sub>面向开源项目和开发者产品。让你看清项目在哪里被发现、被讨论、被比较，然后把这些信号转成报告、Brief、审批和行动。</sub>
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
    <a href="https://www.aidcmo.com/">在线演示</a> · <a href="https://www.aidcmo.com/static/demo.mp4">观看视频</a>
  </h3>
</div>

<div align="center">
  <a href="https://www.aidcmo.com/">
    <img src="assets/screenshots/demo-cover.png" alt="OpenCMO 实战演示" width="850" />
  </a>
  <p><i>在一个开源工作区里，把可见性信号变成增长决策。</i></p>
</div>

<div align="center">
  <h3>加入 OpenCMO 交流群</h3>
  <img src="assets/community-qr.png" alt="OpenCMO 微信交流群二维码" width="240" />
  <p><i>有任何问题、想交流意见?用微信扫码进群沟通。</i></p>
</div>

---

## 真实生产示例

OpenCMO 每天都在真实项目上跑。两个线上扫描展示一次 URL 输入会被转化成什么。

### Coze — 监控一个全球 AI Agent 平台

- **自动识别的竞品**：Dify、FastGPT、OpenAI GPTs
- 跟踪 **50 个关键词**（例如 `coze 和 dify 哪个好用`、`coze vs chatgpt custom gpts`）
- 监测窗口内 **326 次 SERP 快照**
- **100 条社区讨论** — Hacker News 61、Bilibili 29、Dev.to 10
- 从相关仓库挖出 **153 位 GitHub 开发者** 作为潜在用户
- 自动捕获：*"Citability 分数下降 24 分"* — AI 搜索可见性回归，下一次定时扫描自动报警

### DigiGrow — 一家与 Checkatrade、Wix 竞争的英国 SaaS

- 跟踪 **54 个关键词**，**672 次 SERP 排名检查**
- **100 条社区讨论**，覆盖 Hacker News、Dev.to、Bilibili、V2EX
- 端到端生成 **34 条可执行洞察**
- 自动捕获（critical）：`digigrow.uk online marketing solutions` 在 24 小时内从 **第 #2 跌到 #16**（5/2 → 5/3）— 不需要人盯面板，下一次扫描自动推出可执行洞察

> 在 [线上 Demo](https://www.aidcmo.com/) 输入你自己的 URL，一次扫描，完整 pipeline，真实数据。

---

## OpenCMO 有什么不一样

- **它把增长当成系统，而不是零散任务**：SEO、GEO、SERP、社区讨论、竞品、报告和审批都在同一个闭环里。
- **它是为开源项目的现实处境设计的**：在你拥有营销团队之前，你已经需要被发现、被讨论、被建立信任。
- **它不只展示数据，还帮你行动**：把信号变成下一步动作、Brief、草稿和 human-in-the-loop 审批。

## OpenCMO 实际帮你做什么

- **看清项目的可见性**：监控搜索排名、AI 搜索表现、社区提及和爬虫可达性。
- **理解竞争格局**：在知识图谱里查看竞品、关键词重叠和社区上下文。
- **判断下一步该做什么**：找到最值得参与的讨论、最值得打的关键词和最该补的内容空白。
- **让执行建立在真实上下文之上**：从同一套项目上下文生成报告、Agent Brief 和待审批草稿。

## 增长闭环

1. **在首页输入你的 URL** — AI 分析你的品牌、类别、关键词和初始竞品上下文。
2. **按日 / 周 / 月计划持续监控 SEO、GEO、SERP 和社区信号**。
3. **把原始信号转成上下文**，通过报告、知识图谱和项目感知 AI 对话理解发生了什么。
4. **进入执行环节**，产出草稿、审批项和优先级明确的下一步动作。

## 点击"开始监控"后发生了什么

一个 URL 触发 6 阶段 AI 流水线，自动构建完整的增长画像：

| 阶段 | 名称 | 做什么 |
|:----:|------|--------|
| 1/6 | **Context Build** | 爬取你的 URL。三位 AI 专家（产品分析师、SEO 策略师、社区策略师）进行 3 轮辩论，提取品牌名、分类、关键词和竞品。 |
| 2/6 | **Signal Collect** | 并行执行 SEO 审计、GEO 可见度检测、社区搜索（Reddit、HN、Dev.to 等）、SERP 关键词追踪和 **GitHub 潜在用户发现**。 |
| 3/6 | **Signal Normalize** | 清洗和标准化原始数据：去重讨论、归一化评分、对齐关键词和竞品记录。 |
| 4/6 | **Domain Review** | 四位 AI 分析师独立审查信号：SEO 分析师、GEO 分析师、社区分析师、竞品分��师。 |
| 5/6 | **Strategy Synthesis** | AI 策略总监综合所有审查，生成按优先级排序的发现和可执行建议。 |
| 6/6 | **Persist & Publish** | 保存结果到数据库，生成战略报告，在仪表盘展示洞察。 |

> 首次扫描完成后，设置**每日 / 每周 / 每月**定时重扫，持续追踪变化趋势。

## 核心能力

- **SEO 审计**：Core Web Vitals、`llms.txt`、AI 爬虫检测、技术健康度。
- **GEO 可见度**：监控品牌在 ChatGPT、Claude、Gemini、Perplexity、You.com 等 AI 搜索场景中的表现。
- **SERP 追踪**：持续追踪关键词排名变化。
- **社区监控**：覆盖 Reddit、Hacker News、Dev.to、YouTube、Bluesky、Twitter/X，以及 V2EX、微博、B 站、雪球等中文平台。
- **知识图谱**：在一个可视化界面里探索竞品、关键词和社区连接关系。
- **报告系统**：生成版本化战略报告和周报，支持 Human Readout、Agent Brief、PDF 导出和邮件发送。
- **潜在用户发现**：根据产品关键词、竞品和相关仓库，自动从 GitHub 发现有联系方式的开发者。按技术栈匹配度和可触达性评分，支持生成个性化触达内容（邮件、Twitter 私信、GitHub Issue），通过审批队列人工确认后发送。
- **审批与 AI 对话**：在保持人工审核的前提下，使用项目上下文驱动的 AI agent 做分析、总结和起草。

## 深度报告

OpenCMO 已经内置正式报告系统。你可以在项目中打开 **Reports** 标签页，或直接访问 `/projects/<id>/reports`。

- **战略报告**：完整扫描后的定位、竞品格局、风险和建议。
- **周报**：最近 7 天的监控变化、风险、亮点和下一步动作。
- **双版本输出**：每份报告同时保存为 **Human Readout** 和 **Agent Brief**。
- **多智能体管线**：面向人的报告使用 6 阶段管线，而不是单次 prompt。
- **优雅降级**：深度管线失败时，会自动回退到更简单的生成路径，确保报告始终可用。

## 快速开始

OpenCMO 兼容 OpenAI 协议 API，包括 OpenAI、DeepSeek、NVIDIA NIM、Kimi 兼容网关、Ollama 等。

```bash
git clone https://github.com/study8677/OpenCMO.git
cd OpenCMO
pip install -e ".[all]"
crawl4ai-setup

cp .env.example .env
opencmo-web
```

然后打开 `http://localhost:8080`。

在首页输入项目 URL 即可开始第一次扫描。如果 LLM API Key 尚未配置，Settings 图标上的红点会引导你进入设置面板。

> 提示：也可以直接在 Web 仪表盘的 **Settings** 面板里配置 API Key，无需修改 `.env`。

<details>
<summary>前端开发（可选）</summary>

```bash
cd frontend
npm install
npm run dev
npm run build
```

开发态地址为 `http://localhost:5173`，会自动把 API 代理到 `:8080`。

</details>

## 平台接入

| 能力 | 平台 | 认证 |
| :--- | :--- | :--- |
| 监控 | SEO、GEO、SERP、Community | 可选 provider key |
| 社区来源（英文） | Reddit、HN、Dev.to、Bluesky、YouTube、Twitter/X | 可选 |
| 社区来源（中文） | V2EX、微博、B 站、雪球 | 免费（雪球需 Cookie） |
| 社区来源（预留） | 小红书、微信公众号、抖音 | 待实现（需 MCP/Docker） |
| 发布 | Reddit、Twitter/X | 必需 |
| 报告 | Web + 邮件 + PDF | 邮件需要 SMTP |
| LLM | OpenAI 兼容 API | 必需 |

## 路线图

- [x] AI CMO 战略扫描
- [x] SEO / GEO / SERP / 社区监控
- [x] 版本化战略报告与周报
- [x] 多智能体深度报告管线（6 阶段）
- [x] 带品牌标识的 PDF 导出
- [x] 3D 知识图谱
- [x] 审批流与受控发布
- [x] 中文社区平台监控（V2EX、微博、B 站、雪球）
- [x] 完整国际化支持（英语、中文、日语、韩语、西班牙语）
- [x] 语言感知 AI 响应（LLM 跟随 UI 语言设置）
- [x] LLM 指数退避重试（适配不稳定 provider）
- [x] 简化用户引导：首页输入 URL，无需配置即可开始
- [ ] 更多发布平台
- [ ] 品牌声音控制
- [ ] 更深度的企业级 SEO 爬取

## 贡献者

- [study8677](https://github.com/study8677) - 创建者与维护者
- [Lling0000](https://github.com/Lling0000) - 最主要贡献者
- [ParakhJaggi](https://github.com/ParakhJaggi) - Tavily 集成 ([#2](https://github.com/study8677/OpenCMO/pull/2), [#3](https://github.com/study8677/OpenCMO/pull/3))
- [BBear0115](https://github.com/BBear0115) - BYOK 密钥隔离、base_url 规范化及报告相关 Bug 修复 ([#9](https://github.com/study8677/OpenCMO/pull/9))
- 完整名单见 [CONTRIBUTORS.md](CONTRIBUTORS.md)

## 致谢

- [geo-seo-claude](https://github.com/zubair-trabzada/geo-seo-claude) by [@zubair-trabzada](https://github.com/zubair-trabzada)
- [last30days-skill](https://github.com/mvanhorn/last30days-skill) by [@mvanhorn](https://github.com/mvanhorn)
- [Agent-Reach](https://github.com/Panniantong/Agent-Reach) by [@Panniantong](https://github.com/Panniantong) — 中文平台集成灵感来源

## Star History

<a href="https://star-history.com/#study8677/OpenCMO&Date">
 <picture>
   <source media="(prefers-color-scheme: dark)" srcset="https://api.star-history.com/svg?repos=study8677/OpenCMO&type=Date&theme=dark" />
   <source media="(prefers-color-scheme: light)" srcset="https://api.star-history.com/svg?repos=study8677/OpenCMO&type=Date" />
   <img alt="Star History Chart" src="https://api.star-history.com/svg?repos=study8677/OpenCMO&type=Date" width="100%" />
 </picture>
</a>

## 友链

- [LINUX DO](https://linux.do/) — 真正的技术社区
