<template>
  <li>
    <span class="tree-node" :class="nodeClass">
      <template v-if="isRoot">Idea</template>
      <template v-else>
        <span class="tree-id">{{ node.id }}</span>
        <span class="tree-desc">{{ node.description }}</span>
        <span v-if="node.dependencies && node.dependencies.length" class="tree-deps">
          &rarr; {{ node.dependencies.join(', ') }}
        </span>
      </template>
    </span>
    <ul v-if="node.children && node.children.length">
      <DecompTree
        v-for="child in node.children"
        :key="child?.id"
        :node="child"
        :is-root="false"
      />
    </ul>
  </li>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  node: { type: Object, required: true },
  isRoot: { type: Boolean, default: false },
})

const nodeClass = computed(() => {
  if (props.isRoot) return 'tree-root'
  if (props.node.is_atomic === true) return 'tree-atomic'
  if (props.node.is_atomic === false) return 'tree-decomposed'
  return 'tree-pending'
})
</script>
