<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import AppIcon from '../../components/AppIcon.vue'
import { adminApi } from '../../api/services.js'
import { useSeo } from '../../composables/useSeo.js'
import { useToast } from '../../composables/useToast.js'
import { formatDateTime } from '../../utils/format.js'

const toast = useToast()
const result = ref({ items: [], total: 0, page: 1, size: 25 })
const loading = ref(false)
const showCreate = ref(false)
const resetUser = ref(null)
const newPassword = ref('')
const createForm = reactive({ email: '', display_name: '', password: '', role: 'moderator' })
const search = ref('')

useSeo({ title: 'Users | Velmora Admin', description: 'Manage users.', path: '/admin/users', noindex: true })

async function load() {
  loading.value = true
  try {
    result.value = await adminApi.users({ page: 1, size: 100, search: search.value || undefined })
  } finally {
    loading.value = false
  }
}

async function createUser() {
  try {
    await adminApi.createUser({ ...createForm })
    Object.assign(createForm, { email: '', display_name: '', password: '', role: 'moderator' })
    showCreate.value = false
    toast.show('User created.')
    load()
  } catch (error) {
    toast.show(error.response?.data?.detail || 'Could not create user.', 'error')
  }
}

async function toggleUser(user) {
  try {
    await adminApi.updateUser(user.id, { is_active: !user.is_active })
    toast.show(user.is_active ? 'User disabled.' : 'User enabled.')
    load()
  } catch (error) {
    toast.show(error.response?.data?.detail || 'Could not update user.', 'error')
  }
}

async function changeRole(user) {
  const role = user.role === 'admin' ? 'moderator' : 'admin'
  const label = role === 'admin' ? 'Administrator' : 'Moderator'
  if (!confirm(`Change role for ${user.email} to “${label}”?`)) return
  try {
    await adminApi.updateUser(user.id, { role })
    toast.show('Role updated.')
    load()
  } catch (error) {
    toast.show(error.response?.data?.detail || 'Could not change role.', 'error')
  }
}

async function submitReset() {
  if (!resetUser.value || newPassword.value.length < 12) return
  try {
    await adminApi.resetPassword(resetUser.value.id, { new_password: newPassword.value })
    toast.show('Password changed and active sessions revoked.')
    resetUser.value = null
    newPassword.value = ''
  } catch (error) {
    toast.show(error.response?.data?.detail || 'Could not change password.', 'error')
  }
}

const activeCount = computed(() => result.value.items.filter(item => item.is_active).length)
onMounted(load)
</script>

<template>
  <section class="admin-page admin-users-page">
    <div class="admin-page-head"><div><p>ACCESS</p><h1 class="ui-display">Users</h1><span>User accounts can only be created by an administrator.</span></div><button class="btn btn-primary admin-create" type="button" @click="showCreate = true"><AppIcon name="plus" />Add user</button></div>
    <div class="admin-mini-stats"><div><small>Total</small><strong>{{ result.total }}</strong></div><div><small>Active</small><strong>{{ activeCount }}</strong></div><div><small>Roles</small><strong>2</strong></div></div>
    <div class="admin-toolbar"><input v-model="search" class="admin-search" type="search" placeholder="Email or name"><button class="admin-tool-button" type="button" @click="load">Search</button></div>
    <div class="admin-panel"><div class="admin-table-wrap"><table class="admin-table users-table"><thead><tr><th>User</th><th>Role</th><th>State</th><th>Last login</th><th>Attempts</th><th></th></tr></thead><tbody><tr v-for="user in result.items" :key="user.id"><td data-label="User"><strong>{{ user.display_name }}</strong><small>{{ user.email }}</small></td><td data-label="Role"><span class="role-badge">{{ user.role === 'admin' ? 'Administrator' : 'Moderator' }}</span></td><td data-label="Status"><span class="status-badge" :data-status="user.is_active ? 'completed' : 'cancelled'">{{ user.is_active ? 'Active' : 'Disabled' }}</span></td><td data-label="Last login">{{ formatDateTime(user.last_login_at) }}</td><td data-label="Attempts">{{ user.failed_login_attempts }}</td><td data-label="Actions"><div class="admin-row-actions"><button type="button" @click="changeRole(user)">Change role</button><button type="button" @click="resetUser = user">New password</button><button type="button" @click="toggleUser(user)">{{ user.is_active ? 'Disable' : 'Enable' }}</button></div></td></tr></tbody></table></div><p v-if="!loading && !result.items.length" class="users-empty">No matching users found.</p></div>

    <div v-if="showCreate" class="admin-dialog-layer" @click.self="showCreate = false"><form class="admin-dialog admin-panel" @submit.prevent="createUser"><div class="admin-panel-head"><div><small>NEW ACCOUNT</small><h2>New user</h2></div><button type="button" @click="showCreate = false">×</button></div><label class="admin-field"><span>Name</span><input v-model="createForm.display_name" minlength="2" maxlength="120" required></label><label class="admin-field"><span>Email</span><input v-model="createForm.email" type="email" required></label><label class="admin-field"><span>Password</span><input v-model="createForm.password" type="password" minlength="12" maxlength="128" required><small>At least 12 characters. The server also enforces the password policy.</small></label><label class="admin-field"><span>Role</span><select v-model="createForm.role"><option value="moderator">Moderator</option><option value="admin">Administrator</option></select></label><button class="btn btn-primary admin-save" type="submit">Create</button></form></div>

    <div v-if="resetUser" class="admin-dialog-layer" @click.self="resetUser = null"><form class="admin-dialog admin-panel" @submit.prevent="submitReset"><div class="admin-panel-head"><div><small>CHANGE PASSWORD</small><h2>{{ resetUser.email }}</h2></div><button type="button" @click="resetUser = null">×</button></div><p class="admin-dialog-copy">Changing the password revokes all active sessions for this user.</p><label class="admin-field"><span>New password</span><input v-model="newPassword" type="password" minlength="12" maxlength="128" required></label><button class="btn btn-primary admin-save" type="submit">Change password</button></form></div>
  </section>
</template>
