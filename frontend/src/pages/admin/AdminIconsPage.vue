<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import AppIcon from '../../components/AppIcon.vue'
import { adminApi } from '../../api/services.js'
import { useAppState } from '../../composables/useAppState.js'
import { useSeo } from '../../composables/useSeo.js'
import { useToast } from '../../composables/useToast.js'
import { systemIconOptions } from '../../icons/registry.js'

const state = useAppState()
const toast = useToast()
const loading = ref(true)
const saving = ref(false)
const error = ref('')
const search = ref('')
const createOpen = ref(false)
const editing = ref(null)
const createForm = reactive({ label: '', file: null })
const editForm = reactive({ label: '', file: null })

useSeo({ title: 'Icons | Velmora', description: 'Manage the icon library.', path: '/admin/icons', noindex: true })

const customIcons = computed(() => state.iconLibrary || [])
const filteredSystem = computed(() => {
  const q = search.value.trim().toLowerCase()
  return q ? systemIconOptions.filter(item => item.label.toLowerCase().includes(q)) : systemIconOptions
})
const filteredCustom = computed(() => {
  const q = search.value.trim().toLowerCase()
  return q ? customIcons.value.filter(item => item.label.toLowerCase().includes(q)) : customIcons.value
})

async function load() {
  loading.value = true
  error.value = ''
  try {
    state.iconLibrary = await adminApi.icons()
  } catch (requestError) {
    error.value = requestError.response?.data?.detail || 'Could not load the icon library.'
  } finally {
    loading.value = false
  }
}

function pickCreateFile(event) {
  createForm.file = event.target.files?.[0] || null
}

function pickEditFile(event) {
  editForm.file = event.target.files?.[0] || null
}

function resetCreate() {
  createOpen.value = false
  createForm.label = ''
  createForm.file = null
}

function openEdit(icon) {
  editing.value = icon
  editForm.label = icon.label
  editForm.file = null
}

function closeEdit() {
  editing.value = null
  editForm.label = ''
  editForm.file = null
}

async function createIcon() {
  if (!createForm.label.trim() || !createForm.file) {
    error.value = 'Enter a name and choose an SVG file.'
    return
  }
  saving.value = true
  error.value = ''
  try {
    await adminApi.createIcon(createForm.label.trim(), createForm.file)
    await load()
    resetCreate()
    toast.show('Icon added to the library.')
  } catch (requestError) {
    error.value = requestError.response?.data?.detail || 'Could not add the icon.'
  } finally {
    saving.value = false
  }
}

async function saveIcon() {
  if (!editing.value || !editForm.label.trim()) return
  saving.value = true
  error.value = ''
  try {
    await adminApi.updateIcon(editing.value.id, { label: editForm.label.trim() })
    if (editForm.file) await adminApi.replaceIconFile(editing.value.id, editForm.file)
    await load()
    closeEdit()
    toast.show('Icon updated.')
  } catch (requestError) {
    error.value = requestError.response?.data?.detail || 'Could not update the icon.'
  } finally {
    saving.value = false
  }
}

async function removeIcon(icon) {
  if (!confirm(`Delete icon “${icon.label}»?`)) return
  error.value = ''
  try {
    await adminApi.deleteIcon(icon.id)
    await load()
    toast.show('Icon deleted.')
  } catch (requestError) {
    error.value = requestError.response?.data?.detail || 'Could not delete the icon.'
  }
}

onMounted(load)
</script>

<template>
  <section class="admin-page admin-icons-page">
    <div class="admin-page-head">
      <div><p>VISUAL ASSETS</p><h1 class="ui-display">Icon library</h1><span>System icons are always available. Custom SVG icons can be uploaded, renamed, replaced and deleted.</span></div>
      <button class="btn btn-primary admin-create" type="button" @click="createOpen = true"><AppIcon name="plus" />Add icon</button>
    </div>

    <div v-if="error" class="admin-alert" role="alert">{{ error }}</div>
    <div class="admin-toolbar"><input v-model="search" class="admin-search" type="search" placeholder="Search icons"></div>
    <div v-if="loading" class="admin-loading">Loading icons…</div>

    <template v-else>
      <section class="admin-panel admin-icon-library-section">
        <div class="admin-panel-head"><div><small>SYSTEM</small><h2>Built-in icons</h2><p>Used by the interface and always available regardless of catalog settings.</p></div><span class="admin-counter">{{ filteredSystem.length }}</span></div>
        <div class="admin-icon-library-grid">
          <article v-for="icon in filteredSystem" :key="icon.name" class="admin-icon-library-card is-system">
            <span class="admin-icon-library-card__preview"><AppIcon :name="icon.name" :size="32" /></span>
            <div><strong>{{ icon.label }}</strong><small>System</small></div>
          </article>
        </div>
      </section>

      <section class="admin-panel admin-icon-library-section">
        <div class="admin-panel-head"><div><small>CUSTOM</small><h2>Uploaded icons</h2><p>For product specifications and benefits. Files are validated and sanitized on the server.</p></div><span class="admin-counter">{{ filteredCustom.length }}</span></div>
        <div v-if="filteredCustom.length" class="admin-icon-library-grid">
          <article v-for="icon in filteredCustom" :key="icon.id" class="admin-icon-library-card">
            <span class="admin-icon-library-card__preview"><AppIcon :name="icon.key" :size="32" /></span>
            <div class="admin-icon-library-card__copy"><strong>{{ icon.label }}</strong><small>{{ icon.original_name || 'SVG' }}</small></div>
            <div class="admin-icon-library-card__actions"><button type="button" @click="openEdit(icon)">Edit</button><button class="is-danger" type="button" @click="removeIcon(icon)">Delete</button></div>
          </article>
        </div>
        <div v-else class="admin-empty-state" style="padding: 14px 17px; color: var(--text-secondary);">No custom icons yet.</div>
      </section>
    </template>

    <div v-if="createOpen" class="admin-dialog-layer" @click.self="resetCreate">
      <form class="admin-dialog admin-panel admin-icon-dialog" @submit.prevent="createIcon">
        <div class="admin-panel-head"><div><small>NEW ICON</small><h2>Add to library</h2></div><button type="button" aria-label="Close" @click="resetCreate">×</button></div>
        <label class="admin-field"><span>Name</span><input v-model="createForm.label" maxlength="120" placeholder="For example: Antenna" required></label>
        <label class="admin-file-field"><input type="file" accept="image/svg+xml,.svg" required @change="pickCreateFile"><span><AppIcon name="plus" /><strong>{{ createForm.file?.name || 'Choose SVG file' }}</strong><small>Up to 128 KB. Scripts, external resources and unsafe elements are removed or blocked.</small></span></label>
        <button class="btn btn-primary admin-save" type="submit" :disabled="saving">{{ saving ? 'Adding…' : 'Add icon' }}</button>
      </form>
    </div>

    <div v-if="editing" class="admin-dialog-layer" @click.self="closeEdit">
      <form class="admin-dialog admin-panel admin-icon-dialog" @submit.prevent="saveIcon">
        <div class="admin-panel-head"><div><small>EDITING</small><h2>{{ editing.label }}</h2></div><button type="button" aria-label="Close" @click="closeEdit">×</button></div>
        <div class="admin-icon-dialog__preview"><AppIcon :name="editing.key" :size="42" /></div>
        <label class="admin-field"><span>Name</span><input v-model="editForm.label" maxlength="120" required></label>
        <label class="admin-file-field"><input type="file" accept="image/svg+xml,.svg" @change="pickEditFile"><span><AppIcon name="plus" /><strong>{{ editForm.file?.name || 'Replace SVG if needed' }}</strong><small>If no file is selected, only the name will change.</small></span></label>
        <button class="btn btn-primary admin-save" type="submit" :disabled="saving">{{ saving ? 'Saving…' : 'Save changes' }}</button>
      </form>
    </div>
  </section>
</template>
