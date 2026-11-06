# Atom Demo — 全局规则

> 本文件是项目的最高优先级规则，适用于所有目录、所有 AI 工具与所有贡献者。
> 子目录规则（`frontend/CLAUDE.md`、`backend/CLAUDE.md`）不得与本文件冲突。
> 产品与技术方案见 `docs/tech-plan.md`。代码、契约、文档冲突时，先更新文档并说明原因，再改代码。

## 1. 产品目标（不可偏离）

- 用户用自然语言描述应用，Agent 生成可运行的多文件 Web 应用，并在可视化预览中展示。
- 必须具备：真实交互、MySQL 持久化、对话迭代、版本回滚、导出/分享。
- 无需注册：匿名 guest token。
- 交付优先级：P0 核心闭环必须可用；P1 延展能力可做；P2 加分项可砍。

## 2. 架构不变量（MUST / MUST NOT）

1. 生成的应用是**不可信代码**，绝不在服务端执行：不 `eval`、不 `exec`、不 `import`、不起子进程、不做 SSR。
2. 预览必须使用独立源 `preview.<domain>` + iframe sandbox；禁止把生成代码注入主站 DOM。
3. Agent 只能通过工具写虚拟文件系统（VFS）；禁止直接写服务器文件系统。
4. 每次成功 run 生成**不可变版本**；回滚等于恢复为新版本，禁止修改历史版本。
5. MySQL 是唯一事实源；MVP 不引入 Redis、消息队列、对象存储。
6. 前端不直接调用 LLM；所有 LLM 调用必须经后端 LLM Gateway。
7. `/api/v1` 与 SSE 事件表是稳定契约；改契约必须同步前端类型、后端 Schema、测试与文档。
8. 匿名身份使用 `Authorization: Bearer <guest_token>`（localStorage）；不用 Cookie；预览域无凭证。
9. 单项目同一时间只允许一个 run；同一 run 的事件 `seq` 单调递增且可回放。

## 3. 分层与边界

```
frontend:  views → components → stores/composables → api client
backend:   routes(HTTP) → services(business) → db / agent
```

- 路由层只做 HTTP 解析、鉴权、状态码与 SSE 输出，**不写业务逻辑、不直接写 SQL**。
- 前端组件不直接调用 HTTP/LLM，不做业务编排；统一走 store/composable 与 API 客户端。
- Agent 工具必须集中注册、集中校验；禁止在业务代码里零散执行工具。
- 新增模块前先确认属于哪一层；跨层调用必须给出理由。

## 4. 安全红线

- 路径校验：拒绝 `..`、绝对路径、非法字符；文件扩展名白名单。
- 大小上限：单文件 ≤ 32KB，单工程 ≤ 256KB；超限拒绝并返回明确错误。
- 所有用户输入与生成内容按不可信处理；Markdown 渲染必须经 DOMPurify。
- 密钥只存在服务端环境变量；禁止进入 Git、镜像、日志、前端包。
- 日志默认不记录 prompt 全文、guest token、API Key；调试需临时开启并脱敏。
- CORS 仅允许 `FRONTEND_ORIGIN`；预览路由校验 Host；设置 `frame-ancestors`。
- 按 guest 与 IP 做限流和配额，防止公网链接被刷。
- 错误响应不得泄露堆栈、SQL、内部路径或密钥。

## 5. 数据与契约

- 时间统一以 UTC 存储，前端按本地时区展示。
- 项目 ID 使用 ULID；事件 `seq` 单调递增。
- 所有表结构变更必须通过 Alembic migration；禁止 `create_all`、禁止手改已应用的迁移。
- 查询必须显式排序与限制数量；列表接口必须有分页或上限。
- 统一错误结构：`{ code, message, request_id }`。
- SSE 事件固定为：`run.status`、`assistant.delta`、`plan.updated`、`tool.start`、`file.updated`、`preview.ready`、`usage`、`error`。
- 新增/删除 SSE 事件类型，必须同时更新前端事件处理、后端类型与本文档。

## 6. 代码质量

- TypeScript 开启 `strict`；禁止 `any`、隐式 `any`、无理由的 `@ts-ignore`。
- Python 必须类型注解；Ruff、mypy、pytest 必须通过。
- 禁止裸 `except`、`except: pass`、吞异常。
- 运行时依赖最小化；新增依赖必须在提交说明中给出理由。
- 不提交调试代码、`console.log`、`print`、临时文件、`.env`、构建产物。
- 单个组件/模块建议 ≤ 300 行；超过则拆分，但不要为一次性逻辑造抽象。
- 命名：文件名 kebab-case；Vue 组件 PascalCase；Python 模块 snake_case；常量 UPPER_SNAKE。

## 7. AI 协作流程（本项目评分点）

1. 动手前先读 `docs/tech-plan.md` 与对应子目录规则。
2. 多文件改动、契约变更、数据库变更：先给方案，得到确认后再改。
3. 小步提交；每次提交应可通过 lint / typecheck / test。
4. 不臆造 API、字段、命令、库行为；不确定时先查代码或提问。
5. 改契约必须同步：Pydantic Schema、TS 类型、测试、文档。
6. 记录 AI 协作过程到 `docs/AI_USAGE.md`：关键 prompt、人工纠正、决策与取舍。
7. 不为了"看起来完整"造假数据、假进度、假功能；未实现项必须明确标注。
8. Definition of Done：可运行 + loading/error/empty 态完整 + 测试/校验通过 + 文档更新。

## 8. MVP 明确禁止

- 注册/登录、OAuth、支付、团队协作、复杂权限。
- 引入 Next/Nuxt、Django、LangChain/LangGraph、WebSocket、Redis、K8s。
- 在服务端执行生成代码或对生成应用做 SSR。
- 预览使用主站域、`srcdoc` 或未经 sandbox 的 iframe。
- 绕过 migration 直接改表；绕过工具直接写生成文件。
- 前端持有或传递 LLM API Key。

## 9. 目标命令（M0 落地后生效）

```bash
# frontend
pnpm dev
pnpm lint
pnpm typecheck
pnpm test
pnpm build

# backend
uv run uvicorn app.main:app --reload
uv run ruff check .
uv run ruff format --check .
uv run mypy app
uv run pytest
```

## 10. 规则维护

- 规则不是装饰：与实现冲突时，先修正规则或实现，不允许静默忽略。
- 修改本文件或子目录规则，需在提交说明中写清原因与影响范围。
