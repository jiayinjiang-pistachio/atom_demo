<script setup lang="ts">
import { ArrowLeft, Clock3, LoaderCircle, RefreshCw, Sparkles } from 'lucide-vue-next'
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'

import AgentChat from '@/components/workspace/AgentChat.vue'
import FilePanel from '@/components/workspace/FilePanel.vue'
import PreviewPanel from '@/components/workspace/PreviewPanel.vue'
import { useProjectsStore } from '@/stores/projects'
import { useWorkspaceStore } from '@/stores/workspace'

const route = useRoute()
const projects = useProjectsStore()
const workspace = useWorkspaceStore()
const projectId = computed(() => String(route.params.id ?? ''))
const project = computed(() => projects.current)
const selectedPath = ref<string | null>(null)

const updatedLabel = computed(() => {
  if (!project.value) {
    return ''
  }
  return new Intl.DateTimeFormat('zh-CN', {
    dateStyle: 'medium',
    timeStyle: 'short',
  }).format(new Date(project.value.updated_at))
})

const filePaths = computed(() => (project.value?.files ?? []).map((file) => file.path).join('|'))

async function load(): Promise<void> {
  if (!projectId.value) {
    return
  }
  await projects.loadProject(projectId.value)
  const loaded = projects.current
  if (loaded && loaded.id === projectId.value) {
    workspace.init(loaded)
    syncSelectedFile()
  }
}

function syncSelectedFile(): void {
  const files = project.value?.files ?? []
  if (files.length === 0) {
    selectedPath.value = null
    return
  }
  const exists = files.some((file) => file.path === selectedPath.value)
  if (!exists) {
    selectedPath.value =
      files.find((file) => file.path === 'index.html')?.path ?? files[0]?.path ?? null
  }
}

async function handleStart(): Promise<void> {
  if (!project.value) {
    return
  }
  await workspace.start(project.value.prompt, project.value.id)
}

async function handleSend(message: string): Promise<void> {
  if (!project.value) {
    return
  }
  await workspace.start(message, project.value.id)
}

watch(projectId, () => void load())
watch(filePaths, syncSelectedFile)
onMounted(() => void load())
onBeforeUnmount(() => workspace.reset())
</script>

<template>
  <main class="mx-auto w-full max-w-7xl px-4 py-6 sm:px-6">
    <div class="flex flex-wrap items-center justify-between gap-3">
      <RouterLink
        to="/"
        class="inline-flex items-center gap-2 text-sm font-medium text-slate-500 transition hover:text-slate-900 dark:text-slate-400 dark:hover:text-white"
      >
        <ArrowLeft class="size-4" />
        返回项目列表
      </RouterLink>
      <span class="font-mono text-[11px] text-slate-400">{{ projectId }}</span>
    </div>

    <div
      v-if="projects.currentLoading"
      class="mt-8 grid place-items-center rounded-3xl border border-slate-200 bg-white py-24 dark:border-slate-800 dark:bg-slate-900"
    >
      <LoaderCircle class="size-6 animate-spin text-indigo-500" />
      <p class="mt-3 text-sm text-slate-500 dark:text-slate-400">正在加载项目…</p>
    </div>

    <div
      v-else-if="projects.error || !project"
      class="mt-8 rounded-3xl border border-rose-200 bg-rose-50 p-8 text-center dark:border-rose-500/30 dark:bg-rose-500/10"
    >
      <p class="text-sm font-medium text-rose-700 dark:text-rose-300">
        {{ projects.error ?? '项目不存在或无权访问' }}
      </p>
      <div class="mt-4 flex justify-center gap-3">
        <button
          type="button"
          class="inline-flex items-center gap-1.5 rounded-xl border border-rose-300 px-3 py-2 text-xs font-medium text-rose-700 dark:border-rose-500/40 dark:text-rose-300"
          @click="load"
        >
          <RefreshCw class="size-3.5" />
          重试
        </button>
        <RouterLink
          to="/"
          class="rounded-xl bg-slate-900 px-3 py-2 text-xs font-medium text-white dark:bg-white dark:text-slate-900"
        >
          返回列表
        </RouterLink>
      </div>
    </div>

    <template v-else>
      <header class="mt-6 flex flex-wrap items-start justify-between gap-4">
        <div class="min-w-0">
          <div class="flex flex-wrap items-center gap-2">
            <h1 class="truncate text-2xl font-semibold tracking-tight text-slate-900 dark:text-white">
              {{ project.title }}
            </h1>
            <span
              v-if="project.current_version !== null"
              class="rounded-full bg-slate-100 px-2.5 py-1 text-[11px] font-medium text-slate-600 dark:bg-slate-800 dark:text-slate-300"
            >
              v{{ project.current_version }}
            </span>
          </div>
          <p class="mt-2 flex items-center gap-1.5 text-xs text-slate-500 dark:text-slate-400">
            <Clock3 class="size-3.5" />
            更新于 {{ updatedLabel }}
          </p>
        </div>
      </header>

      <section
        class="mt-6 rounded-2xl border border-indigo-200 bg-indigo-50/60 p-4 dark:border-indigo-500/30 dark:bg-indigo-500/10"
      >
        <div class="flex items-start gap-2">
          <Sparkles class="mt-0.5 size-4 shrink-0 text-indigo-600 dark:text-indigo-400" />
          <div>
            <p class="text-xs font-medium text-indigo-700 dark:text-indigo-300">应用描述</p>
            <p class="mt-1 text-sm leading-6 text-slate-700 dark:text-slate-300">
              {{ project.prompt }}
            </p>
          </div>
        </div>
      </section>

      <div
        class="mt-5 grid gap-4 lg:h-[calc(100vh-18rem)] lg:min-h-140 lg:grid-cols-[240px_minmax(0,1fr)_minmax(0,1.05fr)]"
      >
        <div class="min-h-105 lg:min-h-0">
          <FilePanel
            :files="project.files"
            :selected-path="selectedPath"
            @select="selectedPath = $event"
          />
        </div>
        <div class="min-h-115 lg:min-h-0">
          <AgentChat
            :messages="project.messages"
            :assistant-text="workspace.assistantText"
            :plan="workspace.plan"
            :events="workspace.events"
            :status="workspace.runStatus"
            :active="workspace.active"
            :mode="workspace.mode"
            :usage="workspace.usage"
            :error="workspace.error"
            :initial-prompt="project.prompt"
            :can-send="workspace.canStart"
            :has-files="project.files.length > 0"
            @start="handleStart"
            @send="handleSend"
            @cancel="workspace.cancel()"
          />
        </div>
        <div class="min-h-115 lg:min-h-0">
          <PreviewPanel
            :project-id="project.id"
            :version="workspace.previewVersion"
            :active="workspace.active"
            :status="workspace.runStatus"
          />
        </div>
      </div>
    </template>
  </main>
</template>
