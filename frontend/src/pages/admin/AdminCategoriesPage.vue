<script setup>
import { onMounted, reactive, ref } from 'vue'
import { adminApi } from '../../api/services.js'
import { useSeo } from '../../composables/useSeo.js'
import { useToast } from '../../composables/useToast.js'

useSeo({ title: 'Categories | Velmora Admin', description: 'Organize the catalog.', path: '/admin/categories', noindex: true })
const toast = useToast()
const categories = ref([])
const busy = ref(false)
const error = ref('')
const draft = reactive({ slug: '', name: '', description: '', is_active: true, sort_order: 0 })
const edits = reactive({})

async function refresh() {
  error.value = ''
  try {
    categories.value = await adminApi.categories()
    for (const item of categories.value) edits[item.slug] = { name: item.name, description: item.description, is_active: item.is_active, sort_order: item.sort_order }
  } catch (e) { error.value = e.response?.data?.detail || 'Cannot load categories.' }
}
async function create() {
  if (busy.value) return
  busy.value = true; error.value = ''
  try {
    await adminApi.createCategory({ ...draft, slug: draft.slug.trim().toLowerCase(), name: draft.name.trim() })
    Object.assign(draft, { slug: '', name: '', description: '', is_active: true, sort_order: 0 })
    await refresh(); toast.show('Category created.')
  } catch (e) { error.value = e.response?.data?.detail || 'Cannot create the category.' }
  finally { busy.value = false }
}
async function save(slug) {
  if (busy.value) return
  busy.value = true; error.value = ''
  try { await adminApi.updateCategory(slug, edits[slug]); await refresh(); toast.show('Category saved.') }
  catch (e) { error.value = e.response?.data?.detail || 'Cannot update the category.' }
  finally { busy.value = false }
}
async function remove(item) {
  if (busy.value || !confirm(`Delete category “${item.name}”? Categories with products cannot be deleted.`)) return
  busy.value = true; error.value = ''
  try { await adminApi.deleteCategory(item.slug); await refresh(); toast.show('Category deleted.') }
  catch (e) { error.value = e.response?.data?.detail || 'Move products out of this category before deleting.' }
  finally { busy.value = false }
}
onMounted(refresh)
</script>

<template>
  <section class="admin-page categories-page">
    <div class="admin-page-head"><div><p>CATALOG</p><h1 class="ui-display">Categories</h1><span>Manage the names, order and visibility of product groups. Existing products keep their category slugs.</span></div><RouterLink to="/admin/products" class="btn btn-secondary">Back to products</RouterLink></div>
    <p v-if="error" class="admin-alert" role="alert">{{ error }}</p>
    <form class="admin-panel category-create" @submit.prevent="create">
      <div class="admin-panel-head"><div><small>NEW CATEGORY</small><h2>Add a category</h2></div></div>
      <div class="category-form-grid">
        <label class="admin-field"><span>Name</span><input v-model="draft.name" required minlength="2" maxlength="100" placeholder="Accessories"></label>
        <label class="admin-field"><span>Slug (permanent)</span><input v-model="draft.slug" required minlength="2" maxlength="80" pattern="[a-z0-9]+(-[a-z0-9]+)*" placeholder="accessories"></label>
        <label class="admin-field"><span>Order</span><input v-model.number="draft.sort_order" type="number" min="-100000" max="100000"></label>
      </div>
      <label class="admin-field"><span>Description (optional)</span><textarea v-model="draft.description" maxlength="500" rows="2"></textarea></label>
      <label class="category-checkbox"><input v-model="draft.is_active" type="checkbox"> Visible in storefront filters</label>
      <button class="btn btn-primary" type="submit" :disabled="busy">Create category</button>
    </form>
    <p v-if="!categories.length" class="admin-panel category-empty">No categories yet. Create the first one above.</p>
    <div v-else class="category-cards">
      <form v-for="item in categories" :key="item.slug" class="admin-panel category-editor" @submit.prevent="save(item.slug)">
        <div class="category-editor__head"><strong>{{ item.slug }}</strong><span>{{ item.is_active ? 'Visible' : 'Hidden' }}</span></div>
        <div class="category-form-grid">
          <label class="admin-field"><span>Display name</span><input v-model="edits[item.slug].name" required minlength="2" maxlength="100"></label>
          <label class="admin-field"><span>Sort order</span><input v-model.number="edits[item.slug].sort_order" type="number" min="-100000" max="100000"></label>
        </div>
        <label class="admin-field"><span>Description</span><textarea v-model="edits[item.slug].description" maxlength="500" rows="2"></textarea></label>
        <label class="category-checkbox"><input v-model="edits[item.slug].is_active" type="checkbox"> Visible to customers</label>
        <div class="category-editor__actions"><button class="btn btn-primary" :disabled="busy" type="submit">Save changes</button><button class="btn btn-secondary" type="button" :disabled="busy" @click="remove(item)">Delete</button></div>
      </form>
    </div>
  </section>
</template>
