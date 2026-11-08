<script setup lang="ts">
import {
  Activity,
  ArrowRight,
  CheckCircle2,
  Circle,
  Database,
  FolderOpen,
  LoaderCircle,
  RefreshCw,
  Server,
  Sparkles,
} from 'lucide-vue-next'
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'

import type { ProjectCreatePayload } from '@/api/types'
import CreateProjectForm from '@/components/projects/CreateProjectForm.vue'
import ProjectCard from '@/components/projects/ProjectCard.vue'
import { useGuestStore } from '@/stores/guest'
import { useProjectsStore } from '@/stores/projects'
import { useSystemStore } from '@/stores/system'

const router = useRouter()
const guest = useGuestStore()
const projects = useProjectsStore()
const system = useSystemStore()
const actionError = ref<string | null>(null)

const databaseOk = computed(() => system.health?.database === 'ok')
const runtimeLabel = computed(() => {
  if (system.loading) {
    return '检测中'
  }
  if (!system.health) {
    return '不可用'
  }
  return databaseOk.value ? '运行正常' : '数据库异常'
})
const runtimeDotClass = computed(() => {
  if (system.loading) {
    return 'bg-amber-400'
  }
  return databaseOk.value ? 'bg-emerald-500' : 'bg-rose-500'
})
const canCreate = computed(() => guest.error === null)

const milestones = [
  { label: 'M0 · 运行时骨架', done: true },
  { label: 'M1 · 匿名身份与项目管理', done: true },
  { label: 'M2 · DeepSeek 生成闭环', done: true },
  { label: 'M3 · 版本、分享与导出', done: true },
] as const

onMounted(() => {
  void system.refresh()
  void projects.refresh()
})

async function handleCreate(payload: ProjectCreatePayload): Promise<void> {
  actionError.value = null
  try {
    const project = await projects.create(payload)
    await router.push(`/p/${project.id}`)
  } catch (caught) {
    actionError.value = caught instanceof Error ? caught.message : '项目创建失败'
  }
}

async function handleRemove(projectId: string): Promise<void> {
  const project = projects.projects.find((item) => item.id === projectId)
  if (!project) {
    return
  }
  if (!window.confirm(`确认删除「${project.title}」？此操作不可恢复。`)) {
    return
  }
  actionError.value = null
  try {
    await projects.remove(projectId)
  } catch (caught) {
    actionError.value = caught instanceof Error ? caught.message : '项目删除失败'
  }
}
</script>

<template>
  <main class="mx-auto w-full max-w-6xl px-6 py-10 sm:py-14">
    <section
      class="relative overflow-hidden rounded-3xl border border-slate-200/80 bg-white p-8 shadow-sm sm:p-12 dark:border-slate-800 dark:bg-slate-900"
    >
      <div
        class="pointer-events-none absolute -right-24 -top-24 size-72 rounded-full bg-indigo-500/10 blur-3xl"
      />
      <div
        class="pointer-events-none absolute -bottom-32 -left-20 size-64 rounded-full bg-sky-500/10 blur-3xl"
      />

      <div class="relative max-w-3xl">
        <span
          class="inline-flex items-center gap-1.5 rounded-full border border-indigo-200 bg-indigo-50 px-3 py-1 text-xs font-medium text-indigo-700 dark:border-indigo-500/30 dark:bg-indigo-500/10 dark:text-indigo-300"
        >
          <Sparkles class="size-3.5" />
          M3 · 版本回滚、导出与只读分享已接入
        </span>

        <h1
          class="mt-5 text-3xl font-semibold tracking-tight text-slate-900 sm:text-5xl dark:text-white"
        >
          让一句话，
          <span
            class="bg-linear-to-r from-indigo-600 via-indigo-500 to-sky-500 bg-clip-text text-transparent"
          >
            成为一个应用。
          </span>
        </h1>

        <p class="mt-4 max-w-2xl text-sm leading-7 text-slate-600 sm:text-base dark:text-slate-400">
          描述你的想法，Atom Demo 会持久化项目，由 DeepSeek 智能体逐步写入文件；计划、工具调用与文件变更通过 SSE 实时展示，成品在隔离域名中预览。
        </p>

        <div class="mt-8">
          <CreateProjectForm
            :loading="projects.creating"
            :disabled="!canCreate"
            @submit="handleCreate"
          />
        </div>

        <div
          v-if="projects.error || actionError"
          class="mt-4 flex flex-wrap items-center justify-between gap-3 rounded-xl border border-rose-200 bg-rose-50 px-3 py-2.5 text-xs text-rose-700 dark:border-rose-500/30 dark:bg-rose-500/10 dark:text-rose-300"
        >
          <span>{{ actionError ?? projects.error }}</span>
          <button
            type="button"
            class="font-medium underline underline-offset-2"
            @click="projects.refresh()"
          >
            重试
          </button>
        </div>
      </div>
    </section>

    <section class="mt-10">
      <div class="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h2 class="text-lg font-semibold tracking-tight text-slate-900 dark:text-white">
            我的项目
          </h2>
          <p class="mt-1 text-xs text-slate-500 dark:text-slate-400">
            当前访客名下有 {{ projects.projects.length }} 个项目，数据保存在 MySQL。
          </p>
        </div>
        <button
          type="button"
          class="inline-flex items-center gap-1.5 rounded-xl border border-slate-200 px-3 py-1.5 text-xs font-medium text-slate-600 transition hover:border-slate-300 hover:text-slate-900 disabled:cursor-wait disabled:opacity-60 dark:border-slate-800 dark:text-slate-300 dark:hover:border-slate-700 dark:hover:text-white"
          :disabled="projects.listLoading"
          @click="projects.refresh()"
        >
          <RefreshCw class="size-3.5" :class="{ 'animate-spin': projects.listLoading }" />
          刷新列表
        </button>
      </div>

      <div v-if="projects.listLoading" class="mt-5 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        <div
          v-for="index in 3"
          :key="index"
          class="h-40 animate-pulse rounded-2xl border border-slate-200 bg-slate-100 dark:border-slate-800 dark:bg-slate-800/60"
        />
      </div>

      <div
        v-else-if="projects.projects.length === 0"
        class="mt-5 rounded-2xl border border-dashed border-slate-300 bg-white px-6 py-12 text-center dark:border-slate-700 dark:bg-slate-900"
      >
        <span
          class="mx-auto grid size-11 place-items-center rounded-2xl bg-indigo-50 text-indigo-600 dark:bg-indigo-500/10 dark:text-indigo-400"
        >
          <FolderOpen class="size-5" />
        </span>
        <p class="mt-4 text-sm font-medium text-slate-900 dark:text-white">还没有项目</p>
        <p class="mt-1 text-xs text-slate-500 dark:text-slate-400">
          在上方输入一句应用描述，创建第一个项目。
        </p>
      </div>

      <div v-else class="mt-5 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        <ProjectCard
          v-for="project in projects.projects"
          :key="project.id"
          :project="project"
          @remove="handleRemove"
        />
      </div>
    </section>

    <section class="mt-10 grid gap-4 lg:grid-cols-[1.2fr_0.8fr]">
      <div
        class="rounded-2xl border border-slate-200/80 bg-white p-5 shadow-sm dark:border-slate-800 dark:bg-slate-900"
      >
        <div class="flex flex-wrap items-center justify-between gap-3">
          <div class="flex items-center gap-2">
            <span
              class="grid size-9 place-items-center rounded-xl bg-emerald-50 text-emerald-600 dark:bg-emerald-500/10 dark:text-emerald-400"
            >
              <Activity class="size-4" />
            </span>
            <div>
              <h2 class="text-sm font-semibold text-slate-900 dark:text-white">运行时状态</h2>
              <p class="text-xs text-slate-500 dark:text-slate-400">实时读取 API 与数据库</p>
            </div>
          </div>
          <button
            type="button"
            class="inline-flex items-center gap-1.5 rounded-xl border border-slate-200 px-3 py-1.5 text-xs font-medium text-slate-600 transition hover:border-slate-300 hover:text-slate-900 disabled:cursor-wait disabled:opacity-60 dark:border-slate-800 dark:text-slate-300 dark:hover:border-slate-700 dark:hover:text-white"
            :disabled="system.loading"
            @click="system.refresh()"
          >
            <RefreshCw class="size-3.5" :class="{ 'animate-spin': system.loading }" />
            重新检测
          </button>
        </div>

        <div class="mt-4 grid gap-3 text-xs sm:grid-cols-3">
          <div class="rounded-xl bg-slate-50 px-3 py-2.5 dark:bg-slate-950/40">
            <p class="text-slate-500 dark:text-slate-400">状态</p>
            <p class="mt-1 flex items-center gap-2 font-medium text-slate-900 dark:text-white">
              <span class="size-2 rounded-full" :class="runtimeDotClass" />
              {{ runtimeLabel }}
              <LoaderCircle v-if="system.loading" class="size-3.5 animate-spin text-amber-500" />
            </p>
          </div>
          <div class="rounded-xl bg-slate-50 px-3 py-2.5 dark:bg-slate-950/40">
            <p class="flex items-center gap-1.5 text-slate-500 dark:text-slate-400">
              <Server class="size-3.5" />API
            </p>
            <p class="mt-1 font-medium text-slate-900 dark:text-white">
              {{ system.meta?.name ?? '—' }}
            </p>
          </div>
          <div class="rounded-xl bg-slate-50 px-3 py-2.5 dark:bg-slate-950/40">
            <p class="flex items-center gap-1.5 text-slate-500 dark:text-slate-400">
              <Database class="size-3.5" />MySQL
            </p>
            <p
              class="mt-1 font-medium"
              :class="databaseOk ? 'text-emerald-600 dark:text-emerald-400' : 'text-rose-600 dark:text-rose-400'"
            >
              {{ system.health?.database ?? '—' }}
              <span v-if="system.latencyMs !== null" class="ml-1 text-slate-400">
                · {{ system.latencyMs }} ms
              </span>
            </p>
          </div>
        </div>

        <p
          v-if="guest.error"
          class="mt-3 rounded-lg bg-rose-50 px-3 py-2 text-xs text-rose-700 dark:bg-rose-500/10 dark:text-rose-300"
        >
          访客身份创建失败：{{ guest.error }}
        </p>
      </div>

      <div
        class="rounded-2xl border border-slate-200/80 bg-white p-5 shadow-sm dark:border-slate-800 dark:bg-slate-900"
      >
        <h2 class="text-sm font-semibold text-slate-900 dark:text-white">交付路线</h2>
        <ul class="mt-3 space-y-2">
          <li
            v-for="milestone in milestones"
            :key="milestone.label"
            class="flex items-center gap-2 text-xs"
          >
            <CheckCircle2 v-if="milestone.done" class="size-4 text-emerald-500" />
            <Circle v-else class="size-4 text-slate-300 dark:text-slate-600" />
            <span :class="milestone.done ? 'text-slate-500 dark:text-slate-400' : 'font-medium text-slate-900 dark:text-white'">
              {{ milestone.label }}
            </span>
            <ArrowRight v-if="!milestone.done" class="size-3.5 text-slate-400" />
          </li>
        </ul>
      </div>
    </section>
  </main>
</template>
