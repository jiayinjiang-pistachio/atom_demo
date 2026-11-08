<script setup lang="ts">
import { ArrowLeft, LoaderCircle, RefreshCw } from 'lucide-vue-next'
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'

import type { ShareCreatePayload } from '@/api/types'
import AgentChat from '@/components/workspace/AgentChat.vue'
import DiffDialog from '@/components/workspace/DiffDialog.vue'
import PreviewPanel from '@/components/workspace/PreviewPanel.vue'
import ShareDialog from '@/components/workspace/ShareDialog.vue'
import WorkspaceSidebar from '@/components/workspace/WorkspaceSidebar.vue'
import WorkspaceToolbar from '@/components/workspace/WorkspaceToolbar.vue'
import { useProjectsStore } from '@/stores/projects'
import { useSharesStore } from '@/stores/shares'
import { useVersionsStore } from '@/stores/versions'
import { useWorkspaceStore } from '@/stores/workspace'

const route = useRoute()
const projects = useProjectsStore()
const workspace = useWorkspaceStore()
const versions = useVersionsStore()
const shares = useSharesStore()

const projectId = computed(() => String(route.params.id ?? ''))
const project = computed(() => projects.current)
const selectedPath = ref<string | null>(null)
const restoringNumber = ref<number | null>(null)
const diffOpen = ref(false)
const diffRange = ref<{ from: number; to: number } | null>(null)
const shareOpen = ref(false)

const updatedLabel = computed(() =>
  project.value
    ? new Intl.DateTimeFormat('zh-CN', { dateStyle: 'medium', timeStyle: 'short' }).format(
        new Date(project.value.updated_at),
      )
    : '',
)

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
    await versions.load(projectId.value)
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
  if (project.value) {
    await handleSend(project.value.prompt)
  }
}

async function handleSend(message: string): Promise<void> {
  if (project.value) {
    await workspace.start(message, project.value.id)
  }
}

async function handleRestore(number: number): Promise<void> {
  if (!project.value) {
    return
  }
  const confirmed = window.confirm(
    `回滚到 v${number}？这会创建一个 source=restore 的新版本，历史版本保持不变。`,
  )
  if (!confirmed) {
    return
  }
  restoringNumber.value = number
  try {
    const version = await versions.restore(project.value.id, number)
    if (version) {
      workspace.setPreviewVersion(version.number)
    }
  } finally {
    restoringNumber.value = null
  }
}

async function handleExport(number?: number): Promise<void> {
  if (!project.value) {
    return
  }
  await versions.exportVersion(project.value.id, number)
}

function openDiff(fromVersion: number, toVersion: number): void {
  diffRange.value = { from: fromVersion, to: toVersion }
  diffOpen.value = true
  if (project.value) {
    void versions.loadDiff(project.value.id, fromVersion, toVersion)
  }
}

function retryDiff(): void {
  if (!project.value || !diffRange.value) {
    return
  }
  void versions.loadDiff(project.value.id, diffRange.value.from, diffRange.value.to)
}

function closeDiff(): void {
  diffOpen.value = false
  diffRange.value = null
  versions.clearDiff()
}

async function openShare(): Promise<void> {
  if (!project.value) {
    return
  }
  shareOpen.value = true
  await Promise.all([shares.load(project.value.id), versions.load(project.value.id)])
}

async function refreshShares(): Promise<void> {
  if (project.value) await shares.load(project.value.id)
}

async function handleCreateShare(payload: ShareCreatePayload): Promise<void> {
  if (project.value) {
    await shares.create(project.value.id, payload)
  }
}

async function handleRevokeShare(slug: string): Promise<void> {
  if (project.value) {
    await shares.revoke(project.value.id, slug)
  }
}

function refreshVersions(): void {
  if (project.value) {
    void versions.load(project.value.id)
  }
}

watch(projectId, () => {
  versions.reset()
  shares.reset()
  void load()
})
watch(filePaths, syncSelectedFile)
watch(
  () => project.value?.current_version,
  (version, previous) => {
    if (project.value && version !== previous && !versions.loading) {
      void versions.load(project.value.id)
    }
  },
)
onMounted(() => void load())
onBeforeUnmount(() => {
  workspace.reset()
  versions.reset()
  shares.reset()
})
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
      <WorkspaceToolbar
        :title="project.title"
        :prompt="project.prompt"
        :version="project.current_version"
        :updated-label="updatedLabel"
        :exporting="versions.exporting"
        @export="handleExport()"
        @share="openShare"
      />

      <div
        class="mt-5 grid gap-4 lg:h-[calc(100vh-18rem)] lg:min-h-140 lg:grid-cols-[260px_minmax(0,1fr)_minmax(0,1.05fr)]"
      >
        <WorkspaceSidebar
          :files="project.files"
          :selected-path="selectedPath"
          :versions="versions.items"
          :versions-loading="versions.loading"
          :version-error="versions.error"
          :restoring-number="restoringNumber"
          :exporting="versions.exporting"
          @select="selectedPath = $event"
          @refresh-versions="refreshVersions"
          @diff="openDiff"
          @restore="handleRestore"
          @export="handleExport"
        />

        <div class="min-h-115 lg:min-h-0">
          <AgentChat
            :messages="project.messages"
            :assistant-text="workspace.assistantText"
            :plan="workspace.plan"
            :events="workspace.events"
            :status="workspace.runStatus"
            :active="workspace.active"
            :replying="workspace.replying"
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

    <DiffDialog
      :open="diffOpen"
      :diff="versions.diff"
      :loading="versions.diffLoading"
      :error="versions.error"
      @close="closeDiff"
      @retry="retryDiff"
    />

    <ShareDialog
      :open="shareOpen"
      :current-version="project?.current_version ?? null"
      :versions="versions.items"
      :shares="shares.items"
      :loading="shares.loading"
      :creating="shares.creating"
      :revoking="shares.revoking"
      :error="shares.error"
      @close="shareOpen = false"
      @refresh="refreshShares"
      @create="handleCreateShare"
      @revoke="handleRevokeShare"
    />
  </main>
</template>
