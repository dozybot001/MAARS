<template>
  <ProgressBar />
  <main>
    <section id="workspace">
      <LogViewer />
      <div class="panel-divider"></div>
      <ProcessViewer @show-modal="onShowModal" />
    </section>
  </main>
  <AppModal ref="modal" />
  <CommandPalette ref="cmdPalette" />
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import { usePipelineStore } from './stores/pipeline.js'
import { fetchStatus, checkDockerStatus } from './api.js'
import { useSSE } from './composables/useSSE.js'

import ProgressBar from './components/ProgressBar.vue'
import LogViewer from './components/LogViewer.vue'
import ProcessViewer from './components/ProcessViewer.vue'
import AppModal from './components/AppModal.vue'
import CommandPalette from './components/CommandPalette.vue'

const store = usePipelineStore()
const modal = ref(null)
const cmdPalette = ref(null)
const { connect: connectSSE } = useSSE()

let dockerInterval = null

function onShowModal(title, content) {
  modal.value?.open(title, content)
}

async function checkDocker() {
  try {
    const data = await checkDockerStatus()
    store.setDockerStatus(data.connected, data.error)
  } catch {
    store.setDockerStatus(false, 'Cannot check Docker status')
  }
}

onMounted(async () => {
  // Sync with backend state, then connect SSE
  try {
    const status = await fetchStatus()
    store.syncFromStatus(status)
  } catch { /* ignore */ }

  connectSSE()

  // Docker status polling
  checkDocker()
  dockerInterval = setInterval(checkDocker, 30000)
})

onUnmounted(() => {
  if (dockerInterval) clearInterval(dockerInterval)
})
</script>
