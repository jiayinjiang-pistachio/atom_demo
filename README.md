# Atom Demo

一个 Atom-like 的智能体建站 Demo：用一句话描述需求，由 Agent 逐个写入文件并实时预览生成的应用。

> 当前进度：**M3 版本、导出与只读分享**。已可创建项目、发起生成、查看 Agent 计划/工具/文件事件流，并在隔离预览域运行生成结果；支持版本列表、版本 diff、回滚为新版本、ZIP 导出与带有效期的只读分享链接。未配置 `LLM_API_KEY` 时自动进入演示模式（界面与事件会明确标注），不伪造真实模型输出。在线代码编辑按计划推迟，不计入本阶段范围。

## 技术栈

- 前端：Vue 3 + TypeScript（strict）+ Vite + Pinia + Vue Router + Tailwind CSS 4
- 后端：Python 3.13 + FastAPI + Pydantic v2 + SQLAlchemy 2.0 async + asyncmy + Alembic
- 数据库：MySQL 8.0（唯一事实源；不使用 Redis）
- LLM：DeepSeek `deepseek-chat`（OpenAI 兼容，流式 + tool calling）
- 部署：Docker Compose + Caddy，双域名 `app.` / `preview.`，香港轻量服务器

## 目录

```
backend/    FastAPI 应用、Agent、Alembic 迁移、测试
frontend/   Vue 3 SPA
deploy/     Caddyfile、nginx.conf、deploy.sh
local/      tech-plan.md（技术方案与里程碑）、guide.md（使用与验证）
```

详细设计见 [local/tech-plan.md](local/tech-plan.md)，项目规则见 [CLAUDE.md](CLAUDE.md)。

## 本地启动

### 1. 启动 MySQL

```bash
cp .env.example .env          # 按需修改密码
docker compose up -d mysql      # 宿主机端口 3307，避免占用本机已有 MySQL
```

### 2. 启动后端

```bash
cd backend
cp .env.example .env          # DATABASE_URL 默认指向 127.0.0.1:3307
uv sync
uv run alembic upgrade head
uv run uvicorn app.main:app --reload --port 8000
```

验证：

```bash
curl http://127.0.0.1:8000/healthz
curl http://127.0.0.1:8000/api/v1/meta
```

### 3. 启动前端

```bash
cd frontend
pnpm install
pnpm dev                      # http://localhost:5173，/api 与 /healthz 代理到 8000
```

## 一键容器启动

```bash
cp .env.example .env          # 填域名、MySQL 密码、DeepSeek Key
docker compose build
docker compose up -d
```

- `app.<domain>`：前端页面，`/api/*` 与 `/healthz` 转发到 API
- `preview.<domain>`：仅 `/preview/*` 与 `/share-preview/*` 提供生成应用的隔离预览
- MySQL 只绑定本机，不暴露公网

服务器更新：`./deploy/deploy.sh`。

## 生成流程

1. 访客进入首页，前端自动获取 guest token（`Authorization: Bearer`，库里只存 SHA-256）。
2. `POST /api/v1/projects/{id}/runs` 创建 run，单项目同时只允许一个活跃 run。
3. 前端通过 `GET /api/v1/runs/{id}/events?after_seq=0` 订阅 SSE：`run.status`、`assistant.delta`、`plan.updated`、`tool.start`、`file.updated`、`preview.ready`、`usage`、`error`；断线可用 `Last-Event-ID` 续传。
4. Agent 通过工具（`update_plan` / `write_file` / `read_file` / `list_files` / `delete_file` / `finish`）写入 MySQL 中的虚拟文件系统；校验入口与引用后生成不可变版本快照（保留最近 20 个）。
5. `preview.ready` 后前端在 `preview.` 域名下以 iframe sandbox 加载 `/preview/{projectId}/{version}/index.html`。

### 版本、导出与分享（M3）

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/api/v1/projects/{id}/versions` | 版本列表（倒序，含文件数与总字节） |
| GET | `/api/v1/projects/{id}/versions/{a}/diff/{b}` | a→b diff，`a=0` 表示空白基线 |
| POST | `/api/v1/projects/{id}/versions/{n}/restore` | 恢复为新版本，历史版本不变 |
| GET | `/api/v1/projects/{id}/export?version=n` | 导出指定版本 ZIP，默认当前版本 |
| POST | `/api/v1/projects/{id}/shares` | 创建分享，有效期 7 / 30 天或永久 |
| GET | `/api/v1/projects/{id}/shares` | 有效分享列表 |
| DELETE | `/api/v1/projects/{id}/shares/{slug}` | 撤销分享（幂等） |
| GET | `/api/v1/shares/{slug}` | 公开只读元数据（无效 / 撤销 / 过期统一 404） |

分享页固定版本，预览走 `preview.` 域的 `/share-preview/{slug}/*`，响应 `Cache-Control: no-store`，撤销或到期立即失效。每个项目最多 10 个有效分享；版本裁剪时会保留仍被有效分享引用的旧版本。

LLM 模式由 `LLM_MODE` 控制：`auto`（默认，有 Key 用 DeepSeek，否则演示模板）、`live`（必须配置 Key）、`demo`（强制离线模板）。演示模式会在界面与事件中标注。

## 质量检查

```bash
cd backend
uv run ruff check .
uv run mypy app
uv run pytest -q

cd ../frontend
pnpm lint
pnpm typecheck
pnpm test
pnpm build
```

## 里程碑

| 阶段 | 内容 | 状态 |
|---|---|---|
| M0 | 工程骨架、健康检查、数据模型、Docker/Caddy 部署 | 完成 |
| M1 | 匿名 guest、项目 CRUD、工作台布局、版本模型 | 完成 |
| M2 | DeepSeek Agent 循环、VFS 工具、SSE 实时事件、隔离预览 | 完成 |
| M3 | 版本列表 / diff / 回滚、ZIP 导出、只读分享（在线编辑推迟） | 完成 |

## 安全边界（摘要）

- 生成代码只在预览域 iframe 中运行，服务端从不执行生成代码。
- 项目文件存 MySQL，所有写入走 VFS 工具与路径/大小白名单校验。
- Guest token 仅存 SHA-256 哈希，通过 `Authorization: Bearer` 传递，不使用 Cookie。
- 版本快照不可变；回滚生成新版本。
