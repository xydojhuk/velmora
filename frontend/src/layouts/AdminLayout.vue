<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { RouterLink, useRoute, useRouter } from 'vue-router'
import AppIcon from '../components/AppIcon.vue'
import { authApi } from '../api/services.js'
import { useAppState } from '../composables/useAppState.js'
import { useToast } from '../composables/useToast.js'

const state = useAppState()
const toast = useToast()
const route = useRoute()
const router = useRouter()
const sidebarOpen = ref(false)
const passwordOpen = ref(false)
const passwordSaving = ref(false)
const passwordError = ref('')
const passwordForm = reactive({ current_password: '', new_password: '', repeat_password: '' })
const user = computed(() => state.authUser)
const isAdmin = computed(() => user.value?.role === 'admin')
const roleLabel = computed(() => isAdmin.value ? 'Administrator' : 'Moderator')
const sectionTitle = computed(() => ({
  admin: 'Overview', 'admin-orders': 'Orders', 'admin-order': 'Order', 'admin-order-new': 'New order',
  'admin-customers': 'Customers', 'admin-products': 'Products', 'admin-product-new': 'New product',
  'admin-product-edit': 'Edit product', 'admin-categories': 'Categories', 'admin-storefront': 'Storefront', 'admin-settings': 'Settings', 'admin-icons': 'Icons',
  'admin-users': 'Users', 'admin-logs': 'Audit log', 'admin-about': 'About Velmora'
}[route.name] || 'Admin panel'))

onMounted(async () => {
  if (state.authUser) return
  try { state.authUser = await authApi.me() }
  catch { router.replace({ name: 'login', query: { next: router.currentRoute.value.fullPath } }) }
})

async function logout() {
  try { await authApi.logout() } catch { state.authUser = null }
  state.authUser = null
  router.replace({ name: 'login' })
}

function closePassword() {
  passwordOpen.value = false
  passwordError.value = ''
  Object.assign(passwordForm, { current_password: '', new_password: '', repeat_password: '' })
}

async function changePassword() {
  passwordError.value = ''
  if (passwordForm.new_password.length < 12) { passwordError.value = 'The new password must contain at least 12 characters.'; return }
  if (passwordForm.new_password !== passwordForm.repeat_password) { passwordError.value = 'The new passwords do not match.'; return }
  passwordSaving.value = true
  try {
    await authApi.changePassword({ current_password: passwordForm.current_password, new_password: passwordForm.new_password })
    closePassword(); state.authUser = null
    toast.show('Password changed. All sessions were revoked — sign in again.')
    router.replace({ name: 'login' })
  } catch (error) {
    passwordError.value = typeof error.response?.data?.detail === 'string' ? error.response.data.detail : 'Could not change the password.'
  } finally { passwordSaving.value = false }
}
</script>

<template>
  <div class="admin-shell">
    <aside class="admin-sidebar" :class="{ 'is-open': sidebarOpen }">
      <RouterLink to="/admin" class="admin-brand" @click="sidebarOpen = false"><img src="/img/logo.png" alt="Velmora"><span><strong>VELMORA</strong><small>ADMIN</small></span></RouterLink>
      <nav class="admin-nav">
        <RouterLink to="/admin" exact-active-class="active" @click="sidebarOpen = false"><AppIcon name="pulse" />Overview</RouterLink>
        <RouterLink to="/admin/orders" active-class="active" @click="sidebarOpen = false"><AppIcon name="cart" />Orders</RouterLink>
        <RouterLink to="/admin/customers" active-class="active" @click="sidebarOpen = false"><AppIcon name="phone" />Customers</RouterLink>
        <RouterLink to="/admin/products" active-class="active" @click="sidebarOpen = false"><AppIcon name="connection" />Products</RouterLink>
        <RouterLink to="/admin/categories" active-class="active" @click="sidebarOpen = false"><AppIcon name="resize" />Categories</RouterLink>
        <RouterLink v-if="isAdmin" to="/admin/storefront" active-class="active" @click="sidebarOpen = false"><AppIcon name="video" />Storefront</RouterLink>
        <RouterLink v-if="isAdmin" to="/admin/settings" active-class="active" @click="sidebarOpen = false"><AppIcon name="shield" />Settings</RouterLink>
        <RouterLink v-if="isAdmin" to="/admin/icons" active-class="active" @click="sidebarOpen = false"><AppIcon name="resize" />Icons</RouterLink>
        <RouterLink v-if="isAdmin" to="/admin/users" active-class="active" @click="sidebarOpen = false"><AppIcon name="shield-check" />Users</RouterLink>
        <RouterLink v-if="isAdmin" to="/admin/logs" active-class="active" @click="sidebarOpen = false"><AppIcon name="radar" />Audit log</RouterLink>
        <div v-if="isAdmin" class="admin-nav__divider" aria-hidden="true"></div>
        <RouterLink v-if="isAdmin" to="/admin/about" active-class="active" @click="sidebarOpen = false"><AppIcon name="shield-check" />About project</RouterLink>
      </nav>
      <div class="admin-sidebar__bottom">
        <div class="admin-user-mini" v-if="user"><span>{{ user.display_name }}</span><small>{{ user.email }}</small><em>{{ roleLabel }}</em></div>
        <button class="admin-account-action" type="button" @click="passwordOpen = true">Change password</button>
        <button class="admin-logout" type="button" @click="logout">Sign out</button>
      </div>
    </aside>
    <div class="admin-main">
      <header class="admin-topbar">
        <button class="admin-menu" type="button" aria-label="Menu" @click="sidebarOpen = !sidebarOpen"><span></span><span></span><span></span></button>
        <div class="admin-topbar__copy"><small>VELMORA ADMIN</small><strong>{{ sectionTitle }}</strong></div>
        <div v-if="user" class="admin-topbar__user"><span>{{ roleLabel }}</span><strong>{{ user.display_name }}</strong></div>
      </header>
      <div class="admin-content"><slot /></div>
    </div>
    <button v-if="sidebarOpen" class="admin-sidebar-backdrop" type="button" aria-label="Close menu" @click="sidebarOpen = false"></button>

    <div v-if="passwordOpen" class="admin-dialog-layer" @click.self="closePassword">
      <form class="admin-dialog admin-panel" @submit.prevent="changePassword">
        <div class="admin-panel-head"><div><small>ACCOUNT SECURITY</small><h2>Change password</h2></div><button type="button" @click="closePassword">×</button></div>
        <label class="admin-field"><span>Current password</span><input v-model="passwordForm.current_password" type="password" autocomplete="current-password" maxlength="128" required></label>
        <label class="admin-field"><span>New password</span><input v-model="passwordForm.new_password" type="password" autocomplete="new-password" minlength="12" maxlength="128" required><small>At least 12 characters. The server validates the final password policy.</small></label>
        <label class="admin-field"><span>Repeat new password</span><input v-model="passwordForm.repeat_password" type="password" autocomplete="new-password" minlength="12" maxlength="128" required></label>
        <div v-if="passwordError" class="admin-alert">{{ passwordError }}</div>
        <button class="btn btn-primary admin-save" type="submit" :disabled="passwordSaving">{{ passwordSaving ? 'Saving…' : 'Change password' }}</button>
      </form>
    </div>
  </div>
</template>
