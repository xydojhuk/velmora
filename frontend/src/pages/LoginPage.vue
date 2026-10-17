<script setup>
import { reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { authApi } from '../api/services.js'
import { useAppState } from '../composables/useAppState.js'
import { useSeo } from '../composables/useSeo.js'

const state = useAppState()
const route = useRoute()
const router = useRouter()
const form = reactive({ email: '', password: '' })
const loading = ref(false)
const error = ref('')

useSeo({ title: 'Admin sign in | Velmora', description: 'Velmora administration sign-in.', path: '/login', noindex: true })

async function submit() {
  error.value = ''
  loading.value = true
  try {
    const result = await authApi.login(form)
    state.authUser = result.user
    const next = typeof route.query.next === 'string' && route.query.next.startsWith('/admin') ? route.query.next : '/admin'
    router.replace(next)
  } catch (requestError) {
    const status = requestError.response?.status
    const detail = requestError.response?.data?.detail
    if (status === 429) error.value = 'Too many attempts. Try again later.'
    else if (status === 422) error.value = typeof detail === 'string' ? detail : 'Check the email and password fields and try again.'
    else error.value = 'Invalid email or password.'
  } finally { loading.value = false }
}
</script>

<template>
  <section class="auth-page">
    <RouterLink to="/" class="auth-brand" aria-label="Velmora — home"><img src="/img/logo.png" alt="Velmora"><span><strong>VELMORA</strong><small>ADMIN PANEL</small></span></RouterLink>
    <form class="auth-card ui-card" @submit.prevent="submit">
      <div class="auth-card__head"><p>STAFF ACCESS</p><h1 class="ui-display">Sign in</h1><span>Only accounts created by an administrator can access this panel.</span></div>
      <label class="field"><span>Email</span><input v-model="form.email" type="email" autocomplete="username" required maxlength="254" placeholder="admin@example.com"></label>
      <label class="field"><span>Password</span><input v-model="form.password" type="password" autocomplete="current-password" required maxlength="128" placeholder="••••••••••••"></label>
      <div v-if="error" class="form-error" role="alert">{{ error }}</div>
      <button class="btn btn-primary auth-submit" type="submit" :disabled="loading">{{ loading ? 'Checking…' : 'Sign in' }}</button>
    </form>
    <p class="auth-foot">VELMORA / SECURE ACCESS</p>
  </section>
</template>
