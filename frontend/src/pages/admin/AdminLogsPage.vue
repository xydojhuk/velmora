<script setup>
import { onMounted, reactive, ref, watch } from 'vue'
import { adminApi } from '../../api/services.js'
import { useSeo } from '../../composables/useSeo.js'
import { auditActionLabel, auditResourceLabel, formatDateTime } from '../../utils/format.js'

const result = ref({ items: [], total: 0, page: 1, size: 50 })
const loading = ref(false)
const expanded = ref(null)
const filters = reactive({ page: 1, size: 50, action: '', client_ip: '', success: '' })
let timer

useSeo({ title: 'Event log | Velmora Admin', description: 'Audit log.', path: '/admin/logs', noindex: true })

async function load() {
  loading.value = true
  try {
    result.value = await adminApi.logs({
      page: filters.page,
      size: filters.size,
      action: filters.action || undefined,
      client_ip: filters.client_ip || undefined,
      success: filters.success === '' ? undefined : filters.success === 'true'
    })
  } finally {
    loading.value = false
  }
}

function delayedLoad() {
  clearTimeout(timer)
  timer = setTimeout(() => { filters.page = 1; load() }, 350)
}

onMounted(load)
watch(() => [filters.page, filters.success], load)
watch(() => [filters.action, filters.client_ip], delayedLoad)
</script>

<template>
  <section class="admin-page">
    <div class="admin-page-head"><div><p>SECURITY & AUDIT</p><h1 class="ui-display">Event log</h1><span>Sign-ins, visits, data changes, IP addresses, user agents and request IDs.</span></div><div class="admin-counter">{{ result.total }} events</div></div>
    <div class="admin-toolbar"><input v-model="filters.action" class="admin-search" type="search" placeholder="Filter by technical action"><input v-model="filters.client_ip" class="admin-search admin-search--short" type="search" placeholder="IP"><select v-model="filters.success" class="admin-select"><option value="">All results</option><option value="true">Successful</option><option value="false">Failed</option></select></div>
    <div class="admin-panel"><div class="admin-table-wrap"><table class="admin-table admin-table--logs"><thead><tr><th>Time</th><th>Action</th><th>User</th><th>IP</th><th>Resource</th><th>Result</th><th></th></tr></thead><tbody><template v-for="item in result.items" :key="item.id"><tr><td>{{ formatDateTime(item.created_at) }}</td><td><strong class="log-action">{{ auditActionLabel(item.action) }}</strong><small>{{ item.method }} {{ item.path }}</small></td><td>{{ item.actor_email || 'Guest' }}</td><td><code>{{ item.client_ip || '—' }}</code></td><td>{{ auditResourceLabel(item.resource_type) }}<small>{{ item.resource_id || '' }}</small></td><td><span class="status-badge" :data-status="item.success ? 'completed' : 'cancelled'">{{ item.success ? 'Success' : 'Error' }}</span></td><td><button class="admin-row-link" type="button" @click="expanded = expanded === item.id ? null : item.id">{{ expanded === item.id ? 'Collapse' : 'Details' }}</button></td></tr><tr v-if="expanded === item.id" class="log-detail-row"><td colspan="7"><div class="log-detail"><div><small>Request ID</small><code>{{ item.request_id || '—' }}</code></div><div><small>User agent</small><p>{{ item.user_agent || '—' }}</p></div><div><small>Message</small><p>{{ item.message || '—' }}</p></div><div class="log-detail__json"><small>Details</small><pre>{{ JSON.stringify(item.details, null, 2) }}</pre></div></div></td></tr></template><tr v-if="!loading && !result.items.length"><td colspan="7" class="admin-empty-cell">No events found.</td></tr></tbody></table></div><div class="admin-pagination"><button type="button" :disabled="filters.page <= 1" @click="filters.page--">←</button><span>Page {{ filters.page }}</span><button type="button" :disabled="filters.page * result.size >= result.total" @click="filters.page++">→</button></div></div>
  </section>
</template>
