# Frontend Rules — Vue 3

> 适用于 `frontend/`。继承上级 `../CLAUDE.md`；冲突时以上级规则为准。

## 1. 技术栈（不要替换）

Vue 3 + TypeScript（strict）+ Vite + Pinia + Vue Router + Tailwind CSS + shadcn-vue + lucide-vue-next + CodeMirror 6 + `@microsoft/fetch-event-source` + markdown-it + DOMPurify。
包管理器固定使用 `pnpm`。

测试：Vitest；核心链路可用 Playwright 冒烟。

## 2. 目录约定

```
src/
├── api/           # HTTP 客户端、SSE 客户端、OpenAPI 类型
├── stores/        # Pinia：projects / workspace / runs
├── views/         # DashboardView / WorkspaceView / ShareView
├── components/    # Chat / FileTree / Preview / VersionPanel / RunTimeline
├── composables/   # useRunStream / usePreview / useResizableLayout
├── router/
├── types/
└── styles/
```

- 一个组件一个文件；视图以 `View.vue` 结尾。
- 文件 kebab-case；组件 PascalCase；composable 以 `use` 开头；store 以 `useXStore` 命名。
- 不在 `components/` 里直接写 HTTP 请求或业务规则。

## 3. Vue 约定

- 只用 `<script setup lang="ts">` + Composition API；禁止 Options API。
- Props：`defineProps<Props>()`；事件：`defineEmits<{...}>()`；禁止 `any`。
- 优先 `computed`，避免 watch 链；跨组件状态放 Pinia，不放模块级可变变量。
- 组件卸载必须清理副作用：SSE abort、timer、事件监听。
- 路由级懒加载 Workspace；不做登录守卫（无注册）。
- 非空断言 `!` 仅在确实不可能为空时使用，并写明原因。

## 4. API 与状态

- 所有 HTTP 必须走 `src/api/client.ts`；组件内禁止直接 `fetch` / `axios`。
- guest token 存 localStorage；请求统一附加 `Authorization: Bearer`；禁止打印 token。
- SSE 必须走 `src/api/events.ts`，使用 `fetch-event-source`：
  - 支持 `after_seq` 断线续传；
  - 处理 `run.status` / `assistant.delta` / `plan.updated` / `tool.start` / `file.updated` / `preview.ready` / `usage` / `error`；
  - 组件卸载时 abort，禁止泄漏连接。
- API 类型优先由 OpenAPI 生成到 `src/api/types.ts`；手写类型必须与后端 Pydantic 保持一致，禁止重复定义多套模型。
- Pinia 负责服务端状态与缓存；组件只读 store/computed，不复制一份本地状态。
- 所有异步页面必须有 loading / error / empty / success 四态；错误必须可重试。

## 5. 预览（安全关键）

- 只允许 iframe 预览：`sandbox="allow-scripts allow-same-origin allow-forms allow-modals"`。
- 禁止添加 `allow-top-navigation`、`allow-downloads`、`allow-popups-to-escape-sandbox`。
- src 只能来自 `PREVIEW_ORIGIN`，格式 `/preview/{projectId}/{version}/index.html`。
- 禁止 `srcdoc`、禁止 `v-html` 注入生成代码、禁止把生成代码挂到主站 DOM。
- 版本化 URL 是刷新机制；不要用 postMessage 向生成应用注入脚本。
- 加载时显示遮罩；失败时保留上一可用版本。

## 6. UI 与体验

- 仅使用主题 token / Tailwind 语义色；禁止散落硬编码颜色；暗色模式用 CSS 变量。
- 响应式：≥1280 三栏；768–1279 两栏；<768 使用 Chat / Preview / Code 三个 Tab。
- 无障碍：表单有 label；图标按钮有 `aria-label`；键盘可操作；焦点可见。
- Markdown：`markdown-it` 渲染 + `DOMPurify` 清洗；外链加 `rel="noopener noreferrer"`。
- 运行过程展示真实事件（Plan、工具、文件 diff），不做假进度条。
- 预览刷新做 debounce，只切到成功版本，避免半成品闪烁。
- 图标统一使用 `lucide-vue-next`；UI 文案中文，代码标识英文。

## 7. 质量门槛

- `pnpm lint`、`pnpm typecheck`、`pnpm test`、`pnpm build` 必须通过。
- 禁止 `any`、未使用变量、无理由的 `@ts-ignore`。
- 单组件 ≤ 300 行；超出拆分。
- store/composable 有 Vitest 覆盖；核心流程可加 Playwright 冒烟。
- 新增依赖必须说明理由；禁止为一次性逻辑引入大库。

## 8. 禁止事项

- Options API、直接 fetch、未消毒 `v-html`。
- 在主站域嵌入生成应用、使用 `srcdoc`。
- 前端持有 LLM Key、打印 guest token、把 token 放进 URL。
- 伪造加载进度、伪造统计数据、把未实现功能伪装成可用。
- 绕过 API 直接修改生成文件或数据库状态。
