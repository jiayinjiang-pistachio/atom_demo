# Backend Rules — FastAPI + MySQL

> 适用于 `backend/`。继承上级 `../CLAUDE.md`；冲突时以上级规则为准。

## 1. 技术栈（不要替换）

Python 3.12 + FastAPI + Pydantic v2 + SQLAlchemy 2.0 async + asyncmy + Alembic + httpx + tenacity + structlog + pytest。
包管理固定使用 `uv`；MySQL 8.0。
LLM：DeepSeek OpenAI 兼容 API，主模型 `deepseek-chat`。

## 2. 目录与分层

```
app/
├── api/           # 路由：HTTP / 鉴权 / SSE
├── schemas/       # Pydantic 请求与响应
├── services/      # 业务编排、事务边界
├── agent/         # orchestrator / tools / prompts / context
├── db/            # SQLAlchemy models / session
└── core/          # config / security / logging / errors
migrations/        # Alembic
tests/
```

- `routes` 不写业务逻辑、不写 SQL、不拼复杂查询。
- `services` 拥有事务边界；跨服务编排放在 service。
- `agent` 不得 import FastAPI；工具执行与 LLM 调用保持可单测。
- 依赖通过 FastAPI DI 注入；禁止模块级可变单例（DB session、HTTP client 必须按生命周期管理）。

## 3. 异步与数据库

- 所有 IO 使用 async；禁止 `requests`、`time.sleep`、同步 DB 驱动。
- HTTP 外呼使用共享 `httpx.AsyncClient`；设置 timeout 与连接池上限。
- 不要在持有数据库事务时调用 LLM 或长时间流式输出；先提交事务再进入生成。
- SQLAlchemy 2.0 类型化模型；禁止 `create_all`；所有 schema 变更走 Alembic。
- 查询显式 `order_by` + `limit`；避免 N+1；按 `docs/tech-plan.md` 建索引。
- 时间统一 UTC；项目 ID 用 ULID；事件 payload 用 JSON；文件内容用 MEDIUMTEXT。
- guest token 只存 SHA-256 哈希，禁止明文落库。
- 版本快照提交后不可修改；回滚创建新版本。

## 4. API 契约

- 前缀 `/api/v1`；请求/响应必须有 Pydantic Schema；不直接返回 ORM 模型。
- 统一错误结构 `{ code, message, request_id }`；不泄露堆栈、SQL、内部路径。
- 状态码语义正确：400/401/403/404/409/422/429/500。
- SSE：事件先落库并分配单调 `seq`，再发送；15s 心跳；`X-Accel-Buffering: no`；支持 `after_seq` / `Last-Event-ID` 回放。
- 预览路由：校验 Host 等于 `PREVIEW_HOST`；路径白名单；扩展名白名单；版本化资源可 `immutable` 缓存；设置 `frame-ancestors`；不要设置 `X-Frame-Options: DENY`。
- CORS：只允许 `FRONTEND_ORIGIN`；不做 `*`；允许 `Authorization` 与 `Content-Type`；不使用 Cookie。
- OpenAPI 必须与实际接口一致；禁止未文档化接口。

## 5. Agent 与 LLM

- LLM 只允许经 `services/llm` Gateway 调用；路由与 Agent 业务不得直接发 HTTP 到模型服务。
- Provider 抽象保留；MVP 固定 DeepSeek，可切换兼容服务而不改前端。
- 模型固定 `deepseek-chat`（tools + streaming）；`deepseek-reasoner` 不进入工具循环。
- 工具注册表 + JSON Schema；服务端校验参数；禁止 `eval` / `exec` / shell / 任意文件读写。
- 路径白名单：拒绝 `..` 与绝对路径；只允许 `html/css/js/json/svg/md/txt` 等白名单扩展名。
- 大小上限：单文件 32KB、单工程 256KB；超限拒绝。
- 循环预算：最多 24 个工具步、单次 `max_tokens` 上限、单 run 总 token 上限、墙上时间上限。
- 每处理一个流式 chunk / 工具调用前检查取消标志；取消不提交版本。
- 只对瞬时 LLM 错误（429/5xx）做指数退避重试，最多 2 次；校验失败不重试同一请求，允许一次带原因的修复轮。
- 上下文构建集中在 `agent/context.py`：稳定前缀（系统提示词 + 工具 + 文件清单）放最前；文件按需读取；旧工具结果超预算时裁剪。
- 提示词是代码：修改生成约束必须走代码评审，并同步更新 `docs/tech-plan.md` 的护栏说明。
- 生成校验：入口存在、非空、相对引用可解析；校验通过才快照。
- 兜底模板：LLM 不可用时套用预生成快照，并在响应中标记演示模式。
- 记录 usage / 耗时；默认不记录 prompt 全文与密钥。

## 6. 安全

- 服务端绝不执行生成代码；预览只读文件并设置正确 Content-Type。
- 所有外部输入在边界校验；拒绝超大请求体与超长路径。
- 按 guest + IP 限流；单项目单 run；配额可配置。
- 配置使用 pydantic-settings，启动时 fail-fast；密钥只在环境变量。
- `.env` 不进 Git；日志脱敏；错误信息不回显用户输入全文。
- 预览域 CORS 拒绝 API 调用；API 只信任 Bearer guest token。

## 7. 测试

- `pytest` + `pytest-asyncio` + `httpx.AsyncClient`。
- 单元测试：路径校验、大小限制、diff、状态机、上下文裁剪、配额。
- 集成测试使用真实 MySQL（Docker Compose），不要用 SQLite 替代；覆盖 run 创建、SSE 回放、版本恢复、预览路径穿越 404、Host/CORS 校验。
- Agent 测试使用 `FakeLLMProvider` 脚本化 tool_calls；CI 禁止调用真实 DeepSeek。
- 每个修复尽量补回归测试。
- CI 必过：`ruff check`、`ruff format --check`、`mypy`、`pytest`。

## 8. 禁止事项

- 异步路由中使用同步 DB / 同步 HTTP。
- 路由写业务逻辑、直接拼 SQL、返回 ORM 模型。
- `create_all`、手改已应用迁移、无索引的全表扫描。
- `eval` / `exec` / `subprocess` / 任意文件写入。
- 在日志或响应中输出密钥、token、prompt 全文。
- 绕过 LLM Gateway 直接调模型；绕过工具直接写生成文件。
- 裸 `except`、吞异常、`# type: ignore` 无理由。
- 未经说明新增运行时依赖。
