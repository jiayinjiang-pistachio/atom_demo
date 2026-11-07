"""Offline templates used when no LLM key is configured.

These are static, hand-written source files. The server never executes them; they are
persisted through the same VFS + version pipeline as agent-generated code.
"""

from __future__ import annotations

import html
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Template:
    key: str
    title: str
    files: dict[str, str]


def pick_template(prompt: str) -> Template:
    lowered = prompt.lower()
    if any(word in lowered for word in ("看板", "任务", "待办", "todo", "task", "kanban")):
        return _kanban(prompt)
    if any(word in lowered for word in ("打卡", "习惯", "habit", "streak")):
        return _habit(prompt)
    if any(word in lowered for word in ("作品集", "个人主页", "简历", "portfolio", "resume")):
        return _portfolio(prompt)
    return _landing(prompt)


def _short_title(prompt: str) -> str:
    compact = " ".join(prompt.split())
    return html.escape(compact[:32] or "我的应用")


def _fill(source: str, prompt: str) -> str:
    return source.replace("__PROMPT__", html.escape(prompt)).replace(
        "__TITLE__", _short_title(prompt)
    )


_BASE_CSS = """
:root{--bg:#0f172a;--card:#111c33;--line:#243354;--text:#e2e8f0;--muted:#94a3b8;--accent:#6366f1}
*{box-sizing:border-box}
body{margin:0;min-height:100vh;background:radial-gradient(1200px 600px at 20% -10%,#312e81 0%,transparent 55%),var(--bg);color:var(--text);font-family:ui-sans-serif,system-ui,-apple-system,"PingFang SC",sans-serif}
::selection{background:var(--accent);color:#fff}
"""


def _kanban(prompt: str) -> Template:
    html_source = _fill(
        """<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>__TITLE__</title>
<link rel="stylesheet" href="styles.css">
</head>
<body>
<header>
  <div>
    <p class="eyebrow">任务看板 · 本地持久化</p>
    <h1>__TITLE__</h1>
    <p class="sub">__PROMPT__</p>
  </div>
  <button id="add" class="primary">+ 新建任务</button>
</header>
<main id="board" class="board"></main>
<footer id="status"></footer>
<script src="app.js"></script>
</body>
</html>
""",
        prompt,
    )
    css_source = (
        _BASE_CSS
        + """
header{display:flex;gap:24px;justify-content:space-between;align-items:flex-end;padding:48px 8vw 24px;flex-wrap:wrap}
.eyebrow{font-size:12px;letter-spacing:.2em;text-transform:uppercase;color:var(--muted)}
h1{margin:8px 0;font-size:clamp(28px,4vw,44px)}
.sub{margin:0;max-width:620px;color:var(--muted);line-height:1.7}
.primary{border:0;background:var(--accent);color:#fff;padding:12px 18px;border-radius:14px;font-size:14px;font-weight:600;cursor:pointer;box-shadow:0 10px 30px #6366f155}
.primary:hover{background:#4f46e5}
.board{display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:18px;padding:8px 8vw 40px}
.column{background:linear-gradient(180deg,var(--card),#0c1629);border:1px solid var(--line);border-radius:20px;padding:16px;min-height:260px;transition:.2x border-color}
.column.over{border-color:var(--accent)}
.column h2{display:flex;justify-content:space-between;font-size:14px;color:var(--muted);margin:2px 4px 14px}
.count{color:var(--text);background:#1e293b;border-radius:999px;padding:2px 8px;font-size:12px}
.card{background:#17223b;border:1px solid #2b3b5e;border-radius:14px;padding:12px 14px;margin-bottom:10px;cursor:grab;transition:.2s transform,.2s box-shadow}
.card:hover{transform:translateY(-2px);box-shadow:0 12px 24px #02061766}
.card.done .title{text-decoration:line-through;color:var(--muted)}
.card .title{font-weight:600;font-size:14px}
.card .meta{display:flex;justify-content:space-between;margin-top:10px;font-size:11px;color:var(--muted)}
.tag{border-radius:999px;padding:2px 8px;background:#312e81;color:#c7d2fe}
.del{border:0;background:transparent;color:#f87171;cursor:pointer;font-size:11px}
footer{padding:0 8vw 40px;color:var(--muted);font-size:12px}
@media(max-width:640px){header{padding-top:32px}.board{padding:8px 5vw 32px}}
"""
    )
    js_source = """
const KEY = 'atom-demo-kanban'
const COLUMNS = [
  { id: 'todo', name: '待开始' },
  { id: 'doing', name: '进行中' },
  { id: 'done', name: '已完成' },
]

function load() {
  try {
    const raw = localStorage.getItem(KEY)
    if (raw) return JSON.parse(raw)
  } catch (error) {
    console.warn('读取本地数据失败，使用内存状态', error)
  }
  return [
    { id: 1, title: '梳理需求与验收标准', column: 'todo', who: '产品' },
    { id: 2, title: '搭建页面结构与视觉', column: 'doing', who: '设计' },
    { id: 3, title: '完成交互并自测', column: 'todo', who: '开发' },
  ]
}

let tasks = load()
let dragId = null

function save() {
  try { localStorage.setItem(KEY, JSON.stringify(tasks)) } catch (error) { console.warn(error) }
}

function render() {
  const board = document.getElementById('board')
  board.innerHTML = ''
  COLUMNS.forEach((column) => {
    const items = tasks.filter((task) => task.column === column.id)
    const box = document.createElement('section')
    box.className = 'column'
    box.dataset.column = column.id
    box.innerHTML = '<h2>' + column.name + '<span class="count">' + items.length + '</span></h2>'
    items.forEach((task) => box.appendChild(card(task)))
    box.addEventListener('dragover', (event) => { event.preventDefault(); box.classList.add('over') })
    box.addEventListener('dragleave', () => box.classList.remove('over'))
    box.addEventListener('drop', () => {
      box.classList.remove('over')
      const task = tasks.find((item) => item.id === dragId)
      if (task) { task.column = column.id; save(); render() }
    })
    board.appendChild(box)
  })
  document.getElementById('status').textContent =
    '共 ' + tasks.length + ' 个任务 · 数据保存在当前浏览器 localStorage'
}

function card(task) {
  const el = document.createElement('article')
  el.className = 'card' + (task.column === 'done' ? ' done' : '')
  el.draggable = true
  el.innerHTML = '<div class="title"></div><div class="meta"><span class="tag"></span><button class="del">删除</button></div>'
  el.querySelector('.title').textContent = task.title
  el.querySelector('.tag').textContent = task.who || '未分配'
  el.querySelector('.del').addEventListener('click', () => {
    tasks = tasks.filter((item) => item.id !== task.id)
    save(); render()
  })
  el.addEventListener('dragstart', () => { dragId = task.id })
  return el
}

document.getElementById('add').addEventListener('click', () => {
  const title = window.prompt('任务标题')
  if (!title) return
  tasks.push({ id: Date.now(), title, column: 'todo', who: '未分配' })
  save(); render()
})

render()
"""
    return Template(
        key="kanban",
        title="团队任务看板",
        files={
            "index.html": html_source,
            "styles.css": css_source,
            "app.js": js_source,
        },
    )


def _habit(prompt: str) -> Template:
    html_source = _fill(
        """<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>__TITLE__</title>
<link rel="stylesheet" href="styles.css">
</head>
<body>
<header>
  <p class="eyebrow">习惯打卡 · 7 天视图</p>
  <h1>__TITLE__</h1>
  <p class="sub">__PROMPT__</p>
</header>
<main>
  <form id="form"><input id="name" placeholder="添加一个习惯，例如：阅读 20 分钟" maxlength="40"><button>添加</button></form>
  <section id="list" class="list"></section>
  <p id="summary" class="summary"></p>
</main>
<script src="app.js"></script>
</body>
</html>
""",
        prompt,
    )
    css_source = (
        _BASE_CSS
        + """
header{padding:48px 8vw 8px}
.eyebrow{font-size:12px;letter-spacing:.2em;text-transform:uppercase;color:#a5b4fc;margin:0}
h1{margin:10px 0 8px;font-size:clamp(28px,4vw,42px)}
.sub{margin:0;max-width:620px;color:var(--muted);line-height:1.7}
main{padding:24px 8vw 48px;max-width:880px}
form{display:flex;gap:10px;margin-bottom:22px}
input{flex:1;background:#111c33;border:1px solid var(--line);border-radius:14px;padding:13px 15px;color:var(--text);font-size:14px;outline:none}
input:focus{border-color:var(--accent)}
form button{border:0;border-radius:14px;background:var(--accent);color:#fff;padding:0 20px;font-weight:600;cursor:pointer}
.list{display:grid;gap:12px}
.habit{background:var(--card);border:1px solid var(--line);border-radius:18px;padding:16px;display:flex;gap:16px;align-items:center;justify-content:space-between;flex-wrap:wrap}
.habit strong{font-size:15px}
.days{display:flex;gap:8px}
.day{width:40px;height:40px;border-radius:12px;border:1px solid var(--line);background:#17223b;color:var(--muted);font-size:11px;cursor:pointer;display:grid;place-items:center;gap:2px}
.day.done{background:#312e81;border-color:#6366f1;color:#e0e7ff}
.del{border:0;background:transparent;color:#f87171;cursor:pointer;font-size:12px}
.summary{color:var(--muted);font-size:13px;margin-top:22px}
"""
    )
    js_source = """
const KEY = 'atom-demo-habits'
const LABELS = ['一', '二', '三', '四', '五', '六', '日']

function load() {
  try {
    const raw = localStorage.getItem(KEY)
    if (raw) return JSON.parse(raw)
  } catch (error) { console.warn(error) }
  return [
    { id: 1, name: '每天阅读 20 分钟', days: [1, 1, 0, 1, 0, 0, 0] },
    { id: 2, name: '喝够 8 杯水', days: [1, 1, 1, 1, 1, 0, 0] },
  ]
}

let habits = load()

function save() {
  try { localStorage.setItem(KEY, JSON.stringify(habits)) } catch (error) { console.warn(error) }
}

function render() {
  const list = document.getElementById('list')
  list.innerHTML = ''
  habits.forEach((habit) => {
    const card = document.createElement('div')
    card.className = 'habit'
    const title = document.createElement('strong')
    title.textContent = habit.name
    const days = document.createElement('div')
    days.className = 'days'
    LABELS.forEach((label, index) => {
      const day = document.createElement('button')
      day.type = 'button'
      day.className = 'day' + (habit.days[index] ? ' done' : '')
      day.innerHTML = '<span>' + label + '</span><span>' + (habit.days[index] ? '✓' : '·') + '</span>'
      day.addEventListener('click', () => {
        habit.days[index] = habit.days[index] ? 0 : 1
        save(); render()
      })
      days.appendChild(day)
    })
    const del = document.createElement('button')
    del.className = 'del'
    del.textContent = '删除'
    del.addEventListener('click', () => {
      habits = habits.filter((item) => item.id !== habit.id)
      save(); render()
    })
    card.append(title, days, del)
    list.appendChild(card)
  })
  const total = habits.reduce((sum, habit) => sum + habit.days.filter(Boolean).length, 0)
  document.getElementById('summary').textContent =
    '本周共打卡 ' + total + ' 次 · 数据保存在浏览器 localStorage'
}

document.getElementById('form').addEventListener('submit', (event) => {
  event.preventDefault()
  const input = document.getElementById('name')
  const name = input.value.trim()
  if (!name) return
  habits.push({ id: Date.now(), name, days: [0, 0, 0, 0, 0, 0, 0] })
  input.value = ''
  save(); render()
})

render()
"""
    return Template(
        key="habit",
        title="习惯打卡",
        files={
            "index.html": html_source,
            "styles.css": css_source,
            "app.js": js_source,
        },
    )


def _portfolio(prompt: str) -> Template:
    html_source = _fill(
        """<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>__TITLE__</title>
<link rel="stylesheet" href="styles.css">
</head>
<body>
<nav><span class="mark">◆</span><span>__TITLE__</span><a href="#contact">联系我</a></nav>
<header>
  <p class="eyebrow">作品集 · 关于 __TITLE__</p>
  <h1>把想法做成<br><span>可以使用的产品。</span></h1>
  <p class="sub">__PROMPT__</p>
  <div class="actions"><a class="primary" href="#work">查看作品</a><a class="ghost" href="#contact">聊聊合作</a></div>
</header>
<section id="work">
  <h2>精选项目</h2>
  <div class="grid">
    <article><p class="num">01</p><h3>智能任务看板</h3><p>支持拖拽与本地持久化的团队协作工具，专注真实工作流。</p><span>Vue · TypeScript</span></article>
    <article><p class="num">02</p><h3>习惯追踪</h3><p>一周节奏可视化，帮助使用者建立可持续的日常习惯。</p><span>Product · UX</span></article>
    <article><p class="num">03</p><h3>数据洞察面板</h3><p>把分散指标收敛成一张可行动的经营视图。</p><span>Python · MySQL</span></article>
  </div>
</section>
<section id="contact" class="contact">
  <h2>一起做点好东西</h2>
  <p>如果你有产品想法或合作意向，欢迎随时联系。</p>
  <button id="hello">复制邮箱</button>
</section>
<footer>用一句话生成 · Atom Demo</footer>
<script src="app.js"></script>
</body>
</html>
""",
        prompt,
    )
    css_source = (
        _BASE_CSS
        + """
nav{display:flex;align-items:center;gap:10px;padding:22px 8vw;color:var(--muted);font-size:13px}
.mark{color:var(--accent);font-size:18px}
nav a{margin-left:auto;color:var(--text);text-decoration:none;border-bottom:1px solid var(--line)}
header{padding:48px 8vw 64px;max-width:1000px}
.eyebrow{font-size:12px;letter-spacing:.2em;text-transform:uppercase;color:#a5b4fc;margin:0}
h1{font-size:clamp(34px,6vw,68px);line-height:1.1;margin:16px 0}
h1 span{background:linear-gradient(90deg,#818cf8,#22d3ee);-webkit-background-clip:text;background-clip:text;color:transparent}
.sub{max-width:640px;color:var(--muted);line-height:1.8;font-size:15px}
.actions{display:flex;gap:12px;margin-top:28px;flex-wrap:wrap}
.primary,.ghost{text-decoration:none;padding:12px 18px;border-radius:14px;font-size:14px;font-weight:600}
.primary{background:var(--accent);color:#fff}
.ghost{border:1px solid var(--line);color:var(--text)}
section{padding:40px 8vw}
h2{font-size:22px;margin:0 0 20px}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:16px}
article{background:var(--card);border:1px solid var(--line);border-radius:20px;padding:22px;transition:.2s transform}
article:hover{transform:translateY(-4px)}
.num{color:var(--accent);font-size:12px;letter-spacing:.2em}
h3{margin:12px 0 8px;font-size:18px}
article p{color:var(--muted);font-size:13px;line-height:1.7;min-height:66px}
article span{font-size:11px;color:#a5b4fc}
.contact{background:radial-gradient(600px 300px at 30% 0%,#312e81,transparent),#0c1629;border-top:1px solid var(--line);text-align:center;padding:72px 8vw}
.contact p{color:var(--muted)}
#hello{margin-top:18px;border:1px solid var(--accent);background:transparent;color:#c7d2fe;padding:11px 18px;border-radius:14px;cursor:pointer}
footer{text-align:center;color:#475569;font-size:12px;padding:24px}
"""
    )
    js_source = """
document.getElementById('hello').addEventListener('click', async (event) => {
  const button = event.currentTarget
  const email = 'hello@example.com'
  try {
    await navigator.clipboard.writeText(email)
    button.textContent = '已复制 ' + email
  } catch (error) {
    window.prompt('复制我的邮箱：', email)
  }
  setTimeout(() => { button.textContent = '复制邮箱' }, 2500)
})
"""
    return Template(
        key="portfolio",
        title="个人作品集",
        files={
            "index.html": html_source,
            "styles.css": css_source,
            "app.js": js_source,
        },
    )


def _landing(prompt: str) -> Template:
    html_source = _fill(
        """<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>__TITLE__</title>
<link rel="stylesheet" href="styles.css">
</head>
<body>
<header>
  <span class="badge">一句话生成 · 可交互原型</span>
  <h1>__TITLE__</h1>
  <p class="sub">__PROMPT__</p>
  <div class="actions"><a href="#demo" class="primary">开始体验</a><a href="#features" class="ghost">了解功能</a></div>
</header>
<section id="features" class="features">
  <article><h3>真实交互</h3><p>不是静态截图，所有按钮、输入与状态切换都可以直接操作。</p></article>
  <article><h3>本地持久化</h3><p>关键数据写入浏览器 localStorage，刷新后仍然保留。</p></article>
  <article><h3>离线可用</h3><p>不依赖外部 CDN、字体或接口，弱网环境下也能稳定打开。</p></article>
</section>
<section id="demo" class="demo">
  <div>
    <h2>快速记录</h2>
    <p>在下面写下一条想法，它会立即出现在列表中。</p>
  </div>
  <form id="form"><input id="idea" maxlength="80" placeholder="例如：把每周复盘做成一张卡片"><button>添加想法</button></form>
  <ul id="items"></ul>
</section>
<footer>由 Atom Demo 生成</footer>
<script src="app.js"></script>
</body>
</html>
""",
        prompt,
    )
    css_source = (
        _BASE_CSS
        + """
header{padding:56px 8vw 56px;max-width:1000px}
.badge{display:inline-block;font-size:12px;color:#c7d2fe;background:#312e81aa;border:1px solid #4f46e5;border-radius:999px;padding:6px 12px}
h1{font-size:clamp(32px,5vw,58px);line-height:1.12;margin:18px 0 14px}
.sub{max-width:650px;color:var(--muted);line-height:1.8}
.actions{display:flex;gap:12px;margin-top:26px}
.primary,.ghost{padding:12px 18px;border-radius:14px;text-decoration:none;font-size:14px;font-weight:600}
.primary{background:var(--accent);color:#fff}
.ghost{border:1px solid var(--line);color:var(--text)}
.features{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:16px;padding:0 8vw 40px}
article{background:var(--card);border:1px solid var(--line);border-radius:18px;padding:22px}
h3{margin:0 0 10px;font-size:17px}
article p{color:var(--muted);font-size:13px;line-height:1.7;margin:0}
.demo{margin:20px 8vw 48px;background:#0c1629;border:1px solid var(--line);border-radius:24px;padding:28px}
h2{margin:0 0 8px;font-size:22px}
.demo p{color:var(--muted);font-size:13px;margin:0 0 18px}
form{display:flex;gap:10px}
input{flex:1;background:#111c33;border:1px solid var(--line);border-radius:14px;padding:13px 15px;color:var(--text);outline:none}
input:focus{border-color:var(--accent)}
form button{border:0;border-radius:14px;background:var(--accent);color:#fff;padding:0 18px;font-weight:600;cursor:pointer}
ul{list-style:none;padding:0;margin:20px 0 0;display:grid;gap:10px}
li{background:#17223b;border:1px solid #2b3b5e;border-radius:12px;padding:12px 14px;font-size:13px;display:flex;justify-content:space-between;gap:12px}
li button{border:0;background:transparent;color:#f87171;cursor:pointer}
footer{text-align:center;color:#475569;font-size:12px;padding:20px}
"""
    )
    js_source = """
const KEY = 'atom-demo-ideas'
function load() {
  try { return JSON.parse(localStorage.getItem(KEY)) || ['把这个想法变成一个可以点击的产品'] }
  catch (error) { console.warn(error); return ['把这个想法变成一个可以点击的产品'] }
}
let items = load()
function save() {
  try { localStorage.setItem(KEY, JSON.stringify(items)) } catch (error) { console.warn(error) }
}
function render() {
  const list = document.getElementById('items')
  list.innerHTML = ''
  items.forEach((item, index) => {
    const row = document.createElement('li')
    const text = document.createElement('span')
    text.textContent = item
    const remove = document.createElement('button')
    remove.textContent = '删除'
    remove.addEventListener('click', () => {
      items.splice(index, 1); save(); render()
    })
    row.append(text, remove)
    list.appendChild(row)
  })
}
document.getElementById('form').addEventListener('submit', (event) => {
  event.preventDefault()
  const input = document.getElementById('idea')
  const value = input.value.trim()
  if (!value) return
  items.unshift(value); input.value = ''; save(); render()
})
render()
"""
    return Template(
        key="landing",
        title="创意原型",
        files={
            "index.html": html_source,
            "styles.css": css_source,
            "app.js": js_source,
        },
    )
