<template>
  <div class="po-exec">
    <div v-for="batch in store.execBatches" :key="batch.batch" class="exec-batch">
      <div class="exec-batch-label">Batch {{ batch.batch }}</div>
      <div
        v-for="task in batch.tasks"
        :key="task.id"
        class="exec-node"
        :class="execClass(task.id)"
        :style="taskClickable(task.id) ? 'cursor:pointer' : ''"
        @click="onTaskClick(task.id)"
      >
        <span class="tree-id">{{ task.id }}</span>
        <span class="exec-desc">{{ task.description }}</span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { usePipelineStore } from '../stores/pipeline.js'

const store = usePipelineStore()

const emit = defineEmits(['show-task-summary'])

function execClass(taskId) {
  const state = store.taskStates[taskId]
  const status = state ? state.status : 'pending'
  return `exec-${status}`
}

function taskClickable(taskId) {
  const state = store.taskStates[taskId]
  return state && state.status === 'completed' && state.summary
}

function onTaskClick(taskId) {
  const state = store.taskStates[taskId]
  if (state && state.status === 'completed' && state.summary) {
    emit('show-task-summary', taskId, state.summary)
  }
}
</script>
