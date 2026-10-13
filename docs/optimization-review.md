# OpenCMO 优化审查与实施记录

> 2026-10-13 · 维护者 Ling（`Lling0000`） · 审查基线 `49f0c3c`。本次覆盖前端加载、后台任务、RAG、容器构建和回归工作流；这是有代码与测试依据的一轮改进，不是完整渗透测试或生产性能认证。

[架构说明与图](architecture.md) · [项目介绍](../README_zh.md)

后续 CI 修复（公网抓取、邮件幂等、生产回归认证与循环 chunk）及最新验证见 [CI/CD 故障修复记录](ci-debug-20261013.md)。本文件中的旧扫描结果为当时记录。

## 1. 本次结果

本次已实现三组运行层改进和三项构建/验收修正：减少首页初始资源、让任务系统在瞬时错误和租约变更后正确处理、让 RAG 检索更少阻塞且严格守住上下文预算。所有完成项都列出验证范围；未实现项集中在第 4 节。

| 区域 | 已实现 | 直接收益 |
| --- | --- | --- |
| 前端 | 全部工作台页面/AppShell 按需加载；显式可选库分包 | 首页不再预载工作台带来的图表/Markdown 依赖 |
| 前端 | 路由 ErrorBoundary 与五语言恢复提示 | 页面或 chunk 失败时提供刷新恢复入口 |
| 后端 | 队列恢复/领取与守护查询瞬时失败后继续轮询；释放领取失败占用的槽 | 临时数据库故障不再永久停掉 Worker |
| 后端 | 租约被回收或其他 Worker 接管后取消旧执行 | 降低旧执行继续消耗模型/抓取资源的风险 |
| RAG | BM25/实体召回分词移至线程 | jieba 冷启动或慢分词不再直接阻塞异步事件循环 |
| RAG | 对最终拼接上下文精确计数 | 分隔符与 tokenizer 边界变化不再突破检索上下文预算 |
| 构建 | 新增 `.dockerignore` | 排除本地密钥、Git、依赖、数据与缓存构建上下文 |
| 构建 | Docker 浏览器安装步骤取消 `|| true` | 安装失败会使构建失败，避免悄悄生成缺环境的镜像 |
| 验收 | 生产回归步骤显式 `shell: bash` | Python 非零退出不再被 `tee` 掩盖；失败后仍尝试生成摘要与上传结果 |

## 2. 前端优化与测量

### 2.1 原因与改动

原版已经按需加载 Graph/Reports/Chat/Performance，Three.js 原本就不属于首页的静态加载链。但其他工作台页面和 AppShell 直接进入入口；旧对象式 `manualChunks` 还会吸收共享依赖，导致 `vendor-charts` 与 `vendor-markdown` 被首页预载。

改动将工作台组件统一改为模块级 `lazy`，保留公开页面直接加载以维持现有语言与 metadata 行为。Vite 使用函数式 `manualChunks` 与 `onlyExplicitManualChunks`，只将指定库放入可选 vendor；React 等共享依赖留在正常公共入口。没有给 AppShell 增加 pathname key，健康的路由切换不会因此额外重挂。

代码：[App.tsx](../frontend/src/App.tsx)、[vite.config.ts](../frontend/vite.config.ts)、[RouteErrorBoundary.tsx](../frontend/src/components/common/RouteErrorBoundary.tsx)。

### 2.2 同机生产构建产物

| 指标 | 基线 | 优化后 | 变化 |
| --- | ---: | ---: | ---: |
| 首页初始 JS，未压缩 | 1,969,021 B | 1,125,329 B | −42.8% |
| 同一 gzip 算法汇总 | 557,675 B | 339,801 B | −39.1% |
| 初始 JS 文件 | 入口 + charts + markdown | 仅入口 | 两个可选库移出初始链 |

统计基于 `dist/index.html` 的脚本/modulepreload 及其静态 JS 依赖闭包；gzip 使用同一 Python `gzip.compress` 方法，不能与 Vite 的单文件展示值混用。基线通过临时复制基线源码重建核对；lockfile 未改变。精简原始测量见 [frontend-bundle-measurements.json](assets/frontend-bundle-measurements.json)。

这些数值不包含 CSS、图片、字体、API 响应，也不是实测 LCP、交互耗时或网络传输量。总 JS 仍存在，只是在业务页面需要时加载。入口仍约 1.13 MB，需要继续优化公共内容与语言字典。

本地 Node 26 / npm 11 完成 TypeScript 与 Vite 构建；仓库 CI 使用 Node 20，其结果应单独查看。Chrome 静态预览已检查 `/zh`、`/zh/services` 正常显示，未登录访问 `/projects/1/graph` 保留跳转 `/signup?next=...`。没有借此声称登录后的工作台、真实后端或 chunk 故障恢复已完成端到端验收。

## 3. 后端、RAG 与构建改进

### 3.1 Worker 轮询与租约

之前 `recover_stale_tasks()` 或 `claim_next_task()` 的一次异常会直接结束后台轮询；领取失败还会留住已取得的全局并发槽。现在在相关边界记录错误、等待下一轮重试，并释放槽。

旧执行的 watcher 原先主要看取消状态。现在同时核对 `worker_id` 和队列状态：回收为 queued、任务不存在或其他 Worker 接管后，请求取消旧协程；heartbeat/watch 查询的瞬时异常允许下一轮重试，finally 收尾不会跳过并发槽释放。

代码：[worker.py](../src/opencmo/background/worker.py)。新增回归：[test_background_worker.py](../tests/test_background_worker.py)，覆盖恢复/领取首轮 SQLite 异常、回收到 queued、其他 Worker 接管；Worker/storage/service 相关 **22 项通过**。

取消仍是协作式的，默认约每秒检查一次。同步阻塞无法立即终止，已发出的外部请求不能撤回；发布/发送/写入仍需要业务幂等，不应将这一改动描述为 exactly-once。

### 3.2 RAG 事件循环与预算

BM25 和标题/实体查询原本在 async 函数内直接执行分词；现在用 `asyncio.to_thread` 执行，回归通过故意延迟分词证明另一个事件循环心跳可以推进。这不是检索吞吐量或 P95 的线上实测。

打包上下文原本累加每块 token 数，未精确处理 `\n\n` 分隔及非可加的 tokenizer 边界。回归复现 **708-token 预算得到 709 tokens**；现在每接受一块前，对实际拼接文本计数，必要时使用完整 child 片段或跳过，保留引用原始偏移。

代码：[store.py](../src/opencmo/rag/store.py)、[retrieval.py](../src/opencmo/rag/retrieval.py)。新增回归：[test_rag.py](../tests/test_rag.py)。RAG 套件 **39 passed, 1 skipped**；跳过需要真实 server Qdrant 的集成用例，模型调用仍是 fixture。

### 3.3 容器与工作流

- [`.dockerignore`](../.dockerignore) 排除 `.env`、Git、node_modules、虚拟环境、数据文件和本地知识目录。之前没有此文件意味着这些本地文件可能进入 build context，不代表已被 COPY 到最终镜像。
- [Dockerfile](../Dockerfile) 移除浏览器环境安装失败的吞错。当前环境没有运行 Docker daemon，**本次未完成实际镜像构建或启动验收**。
- [生产回归 workflow](../.github/workflows/prod-chat-regression.yml) 显式使用 Bash 的 pipefail。按 [GitHub shell 规则](https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax#jobsjob_idstepsshell)，默认 `bash -e` 与显式 Bash 的行为不同。本地用真实 run 脚本与模拟退出 42 的 Python 可执行文件做故障注入：原行为退出 0；修复后退出 42，且 `tee` 仍保存诊断文件。摘要和 artifact 步骤使用 `always()`，允许处理失败、缺文件或不完整 JSON 行。没有触发真实生产聊天或产生模型费用。

## 4. 后续优化清单

以下项目本次**未实现**。优先级按隔离、可靠性和可观察性排，而不是按拆分文件数量排。

| 优先级 | 有代码依据的现状 | 建议优化 | 验收条件 |
| --- | --- | --- | --- |
| P1 | [AuthProvider](../frontend/src/components/auth/AuthProvider.tsx) 在 401 时取消 Query，登录/账号 payload 变化时 invalidate；未在这些路径清掉旧账号缓存 | 在账号身份变更/失效时取消请求并清理或按 account 命名空间隔离；补跨账号前端测试 | A→401→B 登录期间不出现 A 的项目/报告缓存，后台 403 仍有效 |
| P1 | [background/service.py](../src/opencmo/background/service.py) 给非 knowledge 任务加入 `_byok_keys`，storage 将 payload JSON 持久化 | 评估用凭据引用替代任务内原始 key，并设计轮换、保留时间、备份访问保护 | DB/任务事件/日志不保留不必要的原始 key；排队任务在轮换后有明确语义 |
| P1 | [llm.py](../src/opencmo/llm.py) 对所有普通 Exception 走同类重试，客户端每次创建 | 按 400/401/403、429、5xx、连接/超时分类；有总 deadline；明确客户端复用和 close | 永久错误立即进入可解释的失败/failover；临时错误仍重试；取消不被吞掉 |
| P1 | [rag/integration.py](../src/opencmo/rag/integration.py) 的聊天用途依赖英/中文关键词，`Create a LinkedIn campaign using Acme customer results` 未匹配 content | 为聊天生成增加显式用途契约，跨语言约束对外来源使用；不要仅追加词表后声称解决权限 | 中/英/日/韩/西对外生成不能引用 `external_use=false`；内部分析仍可访问授权私有来源 |
| P1 | [scheduler.py](../src/opencmo/scheduler.py) 直接执行定时扫描，绕过 Worker 的租约/并发与账号上下文恢复 | 统一扫描入口，同时审查账号凭据、配额与多实例重复触发；保留知识维护入队语义 | 手动/定时扫描共享额度、事件和取消契约，不重复调度、不混用账号配置 |
| P1 | Worker 的同 kind 待执行任务已经占全局槽；外部发送不属于数据库事务 | 按可执行 kind 公平领取；在发布/邮件等副作用边界加幂等键与明确恢复规则 | 长任务类型不会饿死其他类型；故障重试不重复发送 |
| P1 | [AI crawler 工具](../src/opencmo/tools/ai_crawler_check.py)与 [llms.txt 工具](../src/opencmo/tools/llmstxt.py)直接请求动态 URL 并自动重定向 | 定义公开扫描的域名/协议、DNS/IP 与逐跳策略，限制响应体并设置整个工具 deadline；与已加固的 RAG URL 获取逻辑一致评审 | 内网/保留地址及重定向链被按策略拒绝；慢响应与大响应有整体界限 |
| P1 | [health](../src/opencmo/web/app.py) 返回 `ok: true` 与 scheduler 状态，不核验 Worker loop/DB readiness | 分离 liveness/readiness，报告队列年龄、Worker 状态、数据库可用性；模型配置错误单列 | Worker 退出/DB 不可用时 readiness 失败，但外部 provider 暂时失败不误判存活 |
| P2 | [rag/retrieval.py](../src/opencmo/rag/retrieval.py) 在检索成功后直接 await usage 写入 | 明确非关键遥测与权威引用持久化的不同失败策略 | 注入遥测写失败时仍返回已持久化的合法检索；引用保存失败仍可解释 |
| P2 | [rag/providers.py](../src/opencmo/rag/providers.py) 按 `(base,key)` 缓存 HTTP client 到 shutdown | 设容量和闲置回收；维持账号状态隔离，避免简单按 base 混用 | 多账号/密钥轮换时资源有界；关闭与并发调用无竞态 |
| P2 | [rag/ingestion.py](../src/opencmo/rag/ingestion.py) 的 `path.read_bytes()` 在 `to_thread` 参数求值时仍同步发生 | 把读取和解析完整放入线程；审查剩余索引/元数据更新 CPU 阻塞 | 最大文档入库期间 API/SSE 心跳持续推进，任务取消行为明确 |
| P2 | 首页入口仍约 1.13 MB；公网页与五种语言字典一起进入入口 | 分离公开博客内容与按语言字典加载；保留 metadata 和 locale 一致性 | 对比同机产物和真实网络 LCP/INP，检查语言切换无闪烁或缺键 |
| P2 | [web/app.py](../src/opencmo/web/app.py)、[_db.py](../src/opencmo/storage/_db.py)、[chat router](../src/opencmo/web/routers/chat.py) 体量较大；`on_event` 有弃用警告 | 按生命周期/公开 SEO/认证/聊天编排模块分离；统一 lifespan | 行为和迁移回归不变，多实例启动/关闭无重复任务 |
| P2 | SQLite 每次 `get_db()` 开连接/配置 WAL；多进程 Worker 和 Scheduler 有运行成本与全局并发边界 | 先测 DB 争用与任务排队，再明确 Scheduler 单实例策略，最后决定独立 Worker 或迁移数据库 | 基于队列年龄/锁等待/吞吐的实测门槛，而不是仅为“微服务”拆分 |

这些条目描述具体代码路径与设计风险。未做真实账号渗透、线上压测或完整数据外泄验证，不能据此宣称已经发现并利用全部安全漏洞。

## 5. 本次验证记录

| 检查 | 结果与限制 |
| --- | --- |
| 全量后端测试 | **706 passed, 4 skipped**，本地 Python 3.14，295.97 秒 |
| Ruff | `ruff check src/ tests/` 通过 |
| 前端生产构建 | `tsc -b && vite build` 通过；仍有入口/图谱大 chunk 提示 |
| 产物 HTTP 检查 | 69 个优化后 JS 文件返回 200，与磁盘产物一致 |
| 浏览器 | Chrome 静态 preview：中文首页/服务页正常，未登录受保护路由正常转到注册页 |
| 后端新增回归 | 数据库瞬时失败、全局槽释放、租约回收/接管停止旧执行 |
| RAG 新增回归 | 慢分词不直接堵塞事件循环、拼接上下文精确预算与引用可回读 |
| workflow 故障注入 | 模拟 Python 退出 42，pipefail 正确传播，诊断产物保留 |
| 架构文档与图 | 基于实际模块/注册/存储关系，SVG 可编辑，PNG 预览已生成 |
| GitHub 功能 CI | [代码提交 `71f8588` 的 CI](https://github.com/Lling0000/OpenCMO/actions/runs/38368559671)：frontend、backend Python 3.11/3.12 均 success |
| Docker / 生产 | Docker daemon 不可用，镜像构建未验收；未部署生产、未调用真实模型或发布/发信 |

模型质量、真实 Qdrant server、生产运行版本和线上性能需要各自的验收，不由 fixture、静态 preview 或 GitHub 推送替代。四个跳过项包含真实 server Qdrant 与历史页面用例。

### GitHub 安全扫描：仍有既有告警

[代码提交 `71f8588` 的 Trustabl 扫描](https://github.com/Lling0000/OpenCMO/actions/runs/38368559850)仍为 failure：**44 条规则告警，3 high、4 medium、36 low、1 info**。与 [基线 `49f0c3c` 的扫描](https://github.com/Lling0000/OpenCMO/actions/runs/38356425445)对比 `(rule_id, severity, file_path, tool_name, start_line)`，告警集合相同。未降低扫描门槛或关闭规则。

- 3 条 high 的 OAI-005 指向 `check_llms_txt`、`validate_llmstxt`、`generate_llmstxt`。代码实际已在 `httpx.AsyncClient(timeout=15)` 设置客户端超时，不能把扫描标签直接当作“完全无网络超时”。仍应补整个工具的总 deadline、响应体上限，并核对规则是否识别客户端级配置。
- 3 条 medium 的 OAI-018 是上述工具的动态 URL。代码仍需审查公开地址/DNS/IP/自动重定向策略；RAG 的公开 URL 加固不能自动覆盖这些工具。
- 1 条 medium 的 OAI-009 指向 `send_email_report`。当前发送路径无报告发送幂等键；这已纳入副作用幂等优化，未以多发邮件的方式测试。
- 其余以 tool 错误恢复契约和配置可分析性提示为主，仍需按业务语义逐条评审，不能将 44 条规则报告等同于 44 个已利用漏洞。

功能 CI 通过与安全 gate 通过是两件事。本次优化并未解决全部既有安全告警，也未把静态标签作为生产受攻击证据。

## 6. 复现与跟进

```bash
pip install -e ".[all]" pytest pytest-asyncio ruff
pytest tests/ -q
ruff check src/ tests/
cd frontend
npm ci
npm run build
```

server Qdrant 验证见 [RAG 指南](rag.md)，需要单独设置测试服务地址。该 suite 的模型调用依然是 fixture。

建议下一轮先处理第 4 节的账号缓存、任务凭据与模型错误分类，再建立 readiness/队列指标及副作用幂等验收；架构拆分以这些指标为依据。
