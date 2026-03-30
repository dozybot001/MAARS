<template>
  <div class="pipeline-progress">
    <div
      class="docker-indicator"
      :class="`docker-${store.dockerStatus}`"
      :title="store.dockerTitle"
    >Docker</div>
    <div class="progress-track">
      <template v-for="(node, i) in store.NODE_ORDER" :key="node">
        <div class="progress-node" :data-state="store.nodeStates[node]">
          <span>{{ nodeLabels[node] }}</span>
        </div>
        <div
          v-if="i < store.NODE_ORDER.length - 1"
          class="progress-line"
          :data-filled="store.nodeStates[node] === 'done' ? 'true' : 'false'"
        ></div>
      </template>
    </div>
  </div>
</template>

<script setup>
import { usePipelineStore } from '../stores/pipeline.js'

const store = usePipelineStore()

const nodeLabels = {
  refine: 'Refine',
  calibrate: 'Calibrate',
  strategy: 'Strategy',
  decompose: 'Decompose',
  execute: 'Execute',
  evaluate: 'Evaluate',
  write: 'Write',
}
</script>
