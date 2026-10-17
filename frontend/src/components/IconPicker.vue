<script setup>
import { computed, onMounted, ref } from 'vue'
import AppIcon from './AppIcon.vue'
import { publicApi } from '../api/services.js'
import { useAppState } from '../composables/useAppState.js'
import { mergeIconOptions, resolveIconName } from '../icons/registry.js'

const props = defineProps({
  modelValue: { type: String, default: '' },
  label: { type: String, default: 'Icon' }
})
const emit = defineEmits(['update:modelValue'])
const state = useAppState()
const open = ref(false)
const search = ref('')
const loading = ref(false)

const options = computed(() => mergeIconOptions(state.iconLibrary || []))
const current = computed(() => {
  const key = resolveIconName(props.modelValue)
  return options.value.find(item => item.name === key) || null
})
const filtered = computed(() => {
  const query = search.value.trim().toLowerCase()
  if (!query) return options.value
  return options.value.filter(item => `${item.label} ${item.system ? 'system' : 'custom'}`.toLowerCase().includes(query))
})
const canManage = computed(() => state.authUser?.role === 'admin')

async function loadCustomIcons() {
  loading.value = true
  try {
    state.iconLibrary = await publicApi.icons()
  } catch {
    state.iconLibrary = state.iconLibrary || []
  } finally {
    loading.value = false
  }
}

async function showPicker() {
  open.value = true
  if (!state.iconLibrary?.length) await loadCustomIcons()
}

function select(name) {
  emit('update:modelValue', name)
  open.value = false
  search.value = ''
}

onMounted(loadCustomIcons)
</script>

<template>
  <div class="admin-icon-field">
    <span>{{ label }}</span>
    <button class="admin-icon-select" type="button" @click="showPicker">
      <AppIcon :name="current?.name || 'pulse'" />
      <span>{{ current?.label || 'Choose icon' }}</span>
      <AppIcon name="arrow" class="admin-icon-select__arrow" />
    </button>
  </div>
  <div v-if="open" class="admin-icon-picker-layer" @click.self="open = false">
    <section class="admin-icon-picker admin-panel" role="dialog" aria-modal="true" aria-label="Icon picker">
      <div class="admin-icon-picker__head">
        <div><small>ICON LIBRARY</small><h2>Choose an icon</h2></div>
        <div class="admin-icon-picker__head-actions"><RouterLink v-if="canManage" to="/admin/icons" @click="open = false">Manage</RouterLink><button type="button" aria-label="Close" @click="open = false">×</button></div>
      </div>
      <input v-model="search" class="admin-search admin-icon-picker__search" type="search" placeholder="Search by name">
      <div v-if="loading" class="admin-loading">Loading icons…</div>
      <div v-else class="admin-icon-picker__grid">
        <button v-for="item in filtered" :key="item.name" type="button" :class="{ active: resolveIconName(modelValue) === item.name }" @click="select(item.name)">
          <AppIcon :name="item.name" :size="28" />
          <span>{{ item.label }}</span>
          <small>{{ item.system ? 'System' : 'Custom' }}</small>
        </button>
      </div>
      <p v-if="!loading && !filtered.length" class="admin-icon-picker__empty">No icons match this search.</p>
    </section>
  </div>
</template>
