<script setup>
import { computed } from 'vue'
import { iconMarkup } from '../icons/registry.js'
import { useAppState } from '../composables/useAppState.js'

const props = defineProps({
  name: { type: String, required: true },
  size: { type: [String, Number], default: null },
  stroke: { type: [String, Number], default: null }
})

const state = useAppState()
const markup = computed(() => iconMarkup(props.name, state.iconLibrary || []))
</script>

<template>
  <span class="icon" :style="{ '--icon-size': size ? `${size}px` : undefined, '--icon-stroke': stroke || undefined }" aria-hidden="true" v-html="markup"></span>
</template>
