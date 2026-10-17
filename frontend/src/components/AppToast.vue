<script setup>
import { useAppState } from '../composables/useAppState.js'
const state = useAppState()
</script>

<template>
  <Transition name="toast">
    <div v-if="state.toast" class="app-toast" :class="`app-toast--${state.toast.type}`" role="status">{{ state.toast.message }}</div>
  </Transition>
</template>
