<script setup>
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { installerApi } from '../api/services.js'

const loading = ref(true)
const status = ref(null)
const step = ref(0)
const error = ref('')
const databaseResult = ref(null)
const testingDatabase = ref(false)
const installing = ref(false)
const completed = ref(false)
const backendReady = ref(false)

const form = reactive({
  setupCode: '',
  database: {
    kind: 'bundled', host: '', port: 5432, name: 'velmora', user: 'velmora', password: '', sslmode: 'prefer'
  },
  store: {
    store_name: 'Velmora', brand_tagline: 'Signal Detection', phone: '', email: '', service_region: 'Worldwide',
    timezone: 'UTC', footer_description: 'Professional field electronics and signal-detection equipment.'
  },
  admin: { name: 'Administrator', email: '', password: '', confirm: '' },
  options: { demo_catalog: true }
})

const steps = ['Welcome', 'Database', 'Store', 'Administrator', 'Review', 'Install']
const progress = computed(() => Math.round((step.value / (steps.length - 1)) * 100))
const siteUrl = computed(() => status.value?.site_url || '')
const isLocal = computed(() => status.value?.mode === 'local')

function randomPassword() {
  const chars = 'ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz23456789!@#$%^&*_-+'
  const bytes = new Uint8Array(28)
  crypto.getRandomValues(bytes)
  return Array.from(bytes, b => chars[b % chars.length]).join('')
}


function databasePayload() {
  const base = {
    kind: form.database.kind,
    name: String(form.database.name || '').trim(),
    user: String(form.database.user || '').trim(),
    password: form.database.password
  }
  if (form.database.kind === 'external') {
    return {
      ...base,
      host: String(form.database.host || '').trim(),
      port: Number(form.database.port || 5432),
      sslmode: form.database.sslmode || 'prefer'
    }
  }
  return base
}

function generateDbPassword() { form.database.password = randomPassword() }
function generateAdminPassword() { const value = randomPassword(); form.admin.password = value; form.admin.confirm = value }

function messageFrom(errorObject, fallback) {
  const detail = errorObject?.response?.data?.detail
  if (Array.isArray(detail)) return detail.map(item => item.msg || 'Invalid value').join(' · ')
  return typeof detail === 'string' ? detail : fallback
}

async function loadStatus() {
  loading.value = true
  try {
    status.value = await installerApi.status()
    if (status.value.installed) {
      completed.value = true
      step.value = 5
      return
    }
    if (status.value.session) step.value = Math.max(step.value, 1)
    try { form.store.timezone = Intl.DateTimeFormat().resolvedOptions().timeZone || 'UTC' } catch {}
    if (!form.database.password) generateDbPassword()
  } catch (e) {
    error.value = messageFrom(e, 'Could not contact the installer service.')
  } finally { loading.value = false }
}

async function unlock() {
  error.value = ''
  try {
    await installerApi.unlock({ setup_code: form.setupCode })
    status.value = await installerApi.status()
    step.value = 1
  } catch (e) { error.value = messageFrom(e, 'Could not unlock the installer.') }
}

async function testDatabase() {
  error.value = ''; databaseResult.value = null; testingDatabase.value = true
  try {
    databaseResult.value = await installerApi.testDatabase(databasePayload())
  } catch (e) { error.value = messageFrom(e, 'Database connection failed.') }
  finally { testingDatabase.value = false }
}

function nextFromDatabase() {
  if (!databaseResult.value?.ok) { error.value = 'Test the database connection successfully before continuing.'; return }
  if (databaseResult.value.existing_velmora_schema) { error.value = 'Choose an empty PostgreSQL database for a new Velmora installation.'; return }
  error.value = ''; step.value = 2
}
function nextFromStore() {
  if (!form.store.store_name.trim()) { error.value = 'Store name is required.'; return }
  error.value = ''; step.value = 3
}
function nextFromAdmin() {
  if (!form.admin.email.trim() || !form.admin.name.trim()) { error.value = 'Administrator name and email are required.'; return }
  if (form.admin.password.length < 12) { error.value = 'Administrator password must contain at least 12 characters.'; return }
  if (form.admin.password !== form.admin.confirm) { error.value = 'Administrator passwords do not match.'; return }
  error.value = ''; step.value = 4
}

async function runInstall() {
  error.value = ''; installing.value = true; step.value = 5
  try {
    await installerApi.run({
      database: databasePayload(),
      store: { ...form.store },
      admin: { name: form.admin.name, email: form.admin.email, password: form.admin.password },
      options: { ...form.options }
    })
    completed.value = true
    for (let i = 0; i < 60; i += 1) {
      const result = await installerApi.ready().catch(() => ({ backend: false }))
      if (result.backend) { backendReady.value = true; break }
      await new Promise(resolve => setTimeout(resolve, 2000))
    }
  } catch (e) {
    step.value = 4
    error.value = messageFrom(e, 'Installation failed.')
  } finally { installing.value = false }
}

watch(() => form.database, () => { databaseResult.value = null; error.value = '' }, { deep: true })

onMounted(loadStatus)
</script>

<template>
  <div class="installer-shell">
    <header class="installer-brand">
      <img src="/img/logo.png" alt="Velmora">
      <div><strong>VELMORA</strong><span>Browser Installer</span></div>
      <em>v{{ status?.version || '0.1.0-alpha.1' }}</em>
    </header>

    <section v-if="loading" class="installer-card installer-loading">Preparing installer…</section>

    <template v-else>
      <aside class="installer-steps" aria-label="Installation progress">
        <div class="installer-progress"><i :style="{ width: `${progress}%` }"></i></div>
        <ol>
          <li v-for="(label,index) in steps" :key="label" :class="{active:index===step,done:index<step}"><span>{{ index + 1 }}</span><div><strong>{{ label }}</strong><small>{{ index < step ? 'Complete' : index === step ? 'Current step' : 'Waiting' }}</small></div></li>
        </ol>
      </aside>

      <section class="installer-card">
        <div v-if="error" class="installer-alert">{{ error }}</div>

        <template v-if="step===0">
          <p class="installer-eyebrow">SECURE SETUP</p><h1>Welcome to Velmora</h1>
          <p class="installer-lead">The browser installer will verify your environment, connect PostgreSQL, create the first administrator and configure the storefront.</p>
          <div class="installer-checks"><div v-for="item in status?.checks || []" :key="item.key" :class="{bad:!item.ok}"><span>{{ item.ok ? '✓' : '!' }}</span><div><strong>{{ item.key }}</strong><small>{{ item.message }}</small></div></div></div>
          <label class="installer-field"><span>One-time setup code</span><input v-model="form.setupCode" type="password" autocomplete="one-time-code" placeholder="Shown by the bootstrap command"><small>Required so nobody on the internet can claim an unconfigured installation.</small></label>
          <button class="btn btn-primary installer-primary" type="button" @click="unlock">Unlock installer</button>
        </template>

        <template v-else-if="step===1">
          <p class="installer-eyebrow">STEP 2 / DATABASE</p><h1>Connect PostgreSQL</h1>
          <p class="installer-lead">Use the bundled database or connect an existing PostgreSQL server. Credentials are tested before installation.</p>
          <div class="installer-choice-grid"><button type="button" :class="{active:form.database.kind==='bundled'}" @click="form.database.kind='bundled';databaseResult=null"><strong>Bundled PostgreSQL</strong><small>Recommended. Velmora manages the local database container.</small></button><button type="button" :class="{active:form.database.kind==='external'}" @click="form.database.kind='external';databaseResult=null"><strong>External PostgreSQL</strong><small>Use a managed or remote PostgreSQL database.</small></button></div>
          <div class="installer-grid">
            <label v-if="form.database.kind==='external'" class="installer-field span-2"><span>Database host</span><input v-model="form.database.host" placeholder="db.example.com"></label>
            <label v-if="form.database.kind==='external'" class="installer-field"><span>Port</span><input v-model.number="form.database.port" type="number" min="1" max="65535"></label>
            <label class="installer-field"><span>Database name</span><input v-model="form.database.name" autocomplete="off"></label>
            <label class="installer-field"><span>Database user</span><input v-model="form.database.user" autocomplete="off"></label>
            <label v-if="form.database.kind==='external'" class="installer-field"><span>SSL mode</span><select v-model="form.database.sslmode"><option v-for="item in ['prefer','require','verify-ca','verify-full','disable']" :key="item">{{ item }}</option></select></label>
            <label class="installer-field span-2"><span>Database password</span><div class="installer-input-action"><input v-model="form.database.password" type="password" autocomplete="new-password"><button v-if="form.database.kind==='bundled'" type="button" @click="generateDbPassword">Generate</button></div><small>The password is written to Velmora secret storage, not to the public configuration.</small></label>
          </div>
          <div v-if="databaseResult" class="installer-success"><strong>✓ Connection successful</strong><span>{{ databaseResult.message }} · {{ databaseResult.server }}</span><small v-if="databaseResult.existing_velmora_schema">Warning: this database already appears to contain Velmora tables.</small></div>
          <div class="installer-actions"><button type="button" class="btn" @click="step=0">Back</button><button type="button" class="btn" :disabled="testingDatabase" @click="testDatabase">{{ testingDatabase ? 'Testing…' : 'Test connection' }}</button><button type="button" class="btn btn-primary" @click="nextFromDatabase">Continue</button></div>
        </template>

        <template v-else-if="step===2">
          <p class="installer-eyebrow">STEP 3 / STOREFRONT</p><h1>Configure your store</h1><p class="installer-lead">These values can be changed later in Store Settings.</p>
          <div class="installer-grid"><label class="installer-field"><span>Store name</span><input v-model="form.store.store_name"></label><label class="installer-field"><span>Brand tagline</span><input v-model="form.store.brand_tagline"></label><label class="installer-field"><span>Phone</span><input v-model="form.store.phone" autocomplete="tel"></label><label class="installer-field"><span>Email</span><input v-model="form.store.email" type="email" autocomplete="email"></label><label class="installer-field"><span>Service region</span><input v-model="form.store.service_region"></label><label class="installer-field"><span>Timezone</span><input v-model="form.store.timezone" placeholder="Europe/Podgorica"></label><label class="installer-field span-2"><span>Footer description</span><textarea v-model="form.store.footer_description" rows="3"></textarea></label></div>
          <div class="installer-actions"><button type="button" class="btn" @click="step=1">Back</button><button type="button" class="btn btn-primary" @click="nextFromStore">Continue</button></div>
        </template>

        <template v-else-if="step===3">
          <p class="installer-eyebrow">STEP 4 / ADMINISTRATOR</p><h1>Create the first administrator</h1><p class="installer-lead">This account receives full access to products, orders, users and system settings.</p>
          <div class="installer-grid"><label class="installer-field"><span>Name</span><input v-model="form.admin.name" autocomplete="name"></label><label class="installer-field"><span>Email</span><input v-model="form.admin.email" type="email" autocomplete="email"></label><label class="installer-field"><span>Password</span><div class="installer-input-action"><input v-model="form.admin.password" type="password" autocomplete="new-password"><button type="button" @click="generateAdminPassword">Generate</button></div><small>12–128 characters and at least three character categories.</small></label><label class="installer-field"><span>Repeat password</span><input v-model="form.admin.confirm" type="password" autocomplete="new-password"></label></div>
          <div class="installer-actions"><button type="button" class="btn" @click="step=2">Back</button><button type="button" class="btn btn-primary" @click="nextFromAdmin">Continue</button></div>
        </template>

        <template v-else-if="step===4">
          <p class="installer-eyebrow">STEP 5 / REVIEW</p><h1>Ready to install</h1><p class="installer-lead">Review the configuration. Passwords are intentionally not shown here.</p>
          <div class="installer-review"><article><span>Site</span><strong>{{ siteUrl }}</strong><small>{{ isLocal ? 'Local development mode' : 'Production / HTTPS mode' }}</small></article><article><span>Database</span><strong>{{ form.database.kind==='bundled' ? 'Bundled PostgreSQL' : form.database.host }}</strong><small>{{ form.database.name }} · {{ form.database.user }}</small></article><article><span>Store</span><strong>{{ form.store.store_name }}</strong><small>{{ form.store.service_region }} · {{ form.store.timezone }}</small></article><article><span>Administrator</span><strong>{{ form.admin.name }}</strong><small>{{ form.admin.email }}</small></article></div>
          <label class="installer-option"><input v-model="form.options.demo_catalog" type="checkbox"><span><strong>Install demo catalog</strong><small>Add the bundled Sentinel products so the storefront is immediately populated.</small></span></label>
          <div class="installer-security-note"><strong>What happens next</strong><p>Velmora applies migrations, creates the administrator, writes runtime configuration and secrets, then permanently locks the installer.</p></div>
          <div class="installer-actions"><button type="button" class="btn" @click="step=3">Back</button><button type="button" class="btn btn-primary" @click="runInstall">Install Velmora</button></div>
        </template>

        <template v-else>
          <div v-if="installing" class="installer-final"><div class="installer-spinner"></div><p class="installer-eyebrow">INSTALLING</p><h1>Building your store</h1><p>Preparing PostgreSQL, applying migrations, creating the administrator and securing the installation…</p></div>
          <div v-else-if="completed" class="installer-final"><div class="installer-complete">✓</div><p class="installer-eyebrow">INSTALLATION COMPLETE</p><h1>Velmora is ready</h1><p v-if="backendReady">The backend is healthy and the storefront is ready.</p><p v-else>The installation is complete. Application services are finishing startup; this normally takes a few seconds.</p><div class="installer-actions installer-actions--center"><a class="btn" href="/">Open storefront</a><a class="btn btn-primary" href="/login">Open administration</a></div><small>The one-time setup code has been invalidated and <code>/install</code> is now locked.</small></div>
        </template>
      </section>
    </template>
  </div>
</template>
