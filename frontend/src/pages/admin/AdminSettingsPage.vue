<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { adminApi } from '../../api/services.js'
import { useSeo } from '../../composables/useSeo.js'
import { useToast } from '../../composables/useToast.js'
import { formatMoney } from '../../utils/format.js'
import { dayDefinitions, defaultBusinessHours, formatBusinessHours, normalizeBusinessHours } from '../../utils/businessHours.js'

const toast = useToast()
const loading = ref(true)
const saving = ref(false)
const tab = ref('general')
const error = ref('')
const shipping = ref([])
const payments = ref([])
const editingShipping = ref(null)
const editingPayment = ref(null)
const businessHours = ref(defaultBusinessHours())
const timezoneOptions = ref(['UTC', 'Europe/Podgorica', 'Europe/Kyiv', 'Europe/London', 'Europe/Berlin', 'America/New_York', 'America/Los_Angeles', 'Asia/Dubai', 'Asia/Tokyo'])
const hourOptions = Array.from({ length: 24 }, (_, index) => String(index).padStart(2, '0'))
const minuteOptions = ['00', '15', '30', '45']

const settings = reactive({
  store_name: '',
  brand_tagline: '',
  footer_description: '',
  phone: '',
  email: '',
  working_hours: '',
  timezone: 'UTC',
  service_region: '',
  seo_title: '',
  seo_description: '',
  seo_og_image: '',
  maintenance_mode: false,
  maintenance_title: '',
  maintenance_message: '',
  orders_enabled: true,
  notification_email_enabled: false,
  notification_email_to: '',
  notification_telegram_enabled: false,
  notification_telegram_chat_id: ''
})

const shippingForm = reactive({ code: '', name: '', description: '', carrier: '', requires_city: true, requires_branch: false, requires_address: false, price_amount: 0, is_active: true, sort_order: 0 })
const paymentForm = reactive({ code: '', name: '', description: '', instructions: '', is_active: true, sort_order: 0 })
const tabs = [
  ['general', 'General'],
  ['hours', 'Business hours'],
  ['seo', 'SEO'],
  ['system', 'Store status'],
  ['shipping', 'Shipping'],
  ['payment', 'Payment'],
  ['notifications', 'Notifications']
]

const hoursPreview = computed(() => formatBusinessHours(businessHours.value, settings.timezone || 'UTC'))
useSeo({ title: 'Settings | Velmora Admin', description: 'Store settings.', path: '/admin/settings', noindex: true })

function resetShipping() {
  Object.assign(shippingForm, { code: '', name: '', description: '', carrier: '', requires_city: true, requires_branch: false, requires_address: false, price_amount: 0, is_active: true, sort_order: 0 })
  editingShipping.value = null
}
function resetPayment() {
  Object.assign(paymentForm, { code: '', name: '', description: '', instructions: '', is_active: true, sort_order: 0 })
  editingPayment.value = null
}
function editShipping(row) {
  editingShipping.value = row.id
  Object.assign(shippingForm, { ...row, price_amount: (row.price_minor || 0) / 100 })
}
function editPayment(row) {
  editingPayment.value = row.id
  Object.assign(paymentForm, row)
}
function timeHour(value) { return String(value || '09:00').split(':')[0] || '09' }
function timeMinute(value) { return String(value || '09:00').split(':')[1] || '00' }
function setTimePart(row, field, part, value) {
  const hour = part === 'hour' ? value : timeHour(row[field])
  const minute = part === 'minute' ? value : timeMinute(row[field])
  row[field] = `${hour}:${minute}`
}
function resetBusinessHours() { businessHours.value = defaultBusinessHours() }
function copyMondayToWeekdays() {
  const monday = businessHours.value.find(item => item.day === 'mon')
  if (!monday) return
  for (const row of businessHours.value) {
    if (['mon', 'tue', 'wed', 'thu', 'fri'].includes(row.day)) Object.assign(row, { enabled: monday.enabled, open: monday.open, close: monday.close })
  }
}

async function load() {
  loading.value = true
  error.value = ''
  try {
    const [a, b, c] = await Promise.all([adminApi.settings(), adminApi.shippingMethods(), adminApi.paymentMethods()])
    Object.assign(settings, a)
    businessHours.value = normalizeBusinessHours(a.business_hours)
    shipping.value = b
    payments.value = c
  } catch {
    error.value = 'Could not load settings.'
  } finally {
    loading.value = false
  }
}

async function saveSettings() {
  saving.value = true
  error.value = ''
  try {
    const payload = {
      store_name: settings.store_name,
      brand_tagline: settings.brand_tagline,
      footer_description: settings.footer_description,
      phone: settings.phone,
      email: settings.email,
      service_region: settings.service_region,
      business_hours: businessHours.value,
      timezone: settings.timezone || 'UTC',
      seo_title: settings.seo_title,
      seo_description: settings.seo_description,
      seo_og_image: settings.seo_og_image,
      maintenance_mode: settings.maintenance_mode,
      maintenance_title: settings.maintenance_title,
      maintenance_message: settings.maintenance_message,
      orders_enabled: settings.orders_enabled,
      notification_email_enabled: settings.notification_email_enabled,
      notification_email_to: settings.notification_email_to,
      notification_telegram_enabled: settings.notification_telegram_enabled,
      notification_telegram_chat_id: settings.notification_telegram_chat_id
    }
    const updated = await adminApi.updateSettings(payload)
    Object.assign(settings, updated)
    businessHours.value = normalizeBusinessHours(updated.business_hours)
    toast.show('Store settings saved.')
  } catch (e) {
    const detail = e.response?.data?.detail
    error.value = typeof detail === 'string' ? detail : Array.isArray(detail) ? detail.map(item => item.msg).join(' · ') : 'Could not save settings.'
  } finally {
    saving.value = false
  }
}

async function saveShipping() {
  const payload = { ...shippingForm, price_minor: Math.max(0, Math.round(Number(shippingForm.price_amount || 0) * 100)) }
  delete payload.price_amount
  try {
    if (editingShipping.value) await adminApi.updateShippingMethod(editingShipping.value, payload)
    else await adminApi.createShippingMethod(payload)
    resetShipping()
    shipping.value = await adminApi.shippingMethods()
    toast.show('Shipping method saved.')
  } catch (e) {
    error.value = typeof e.response?.data?.detail === 'string' ? e.response.data.detail : 'Could not save shipping settings.'
  }
}
async function removeShipping(row) {
  if (!confirm(`Delete “${row.name}”?`)) return
  await adminApi.deleteShippingMethod(row.id)
  shipping.value = await adminApi.shippingMethods()
}
async function savePayment() {
  try {
    if (editingPayment.value) await adminApi.updatePaymentMethod(editingPayment.value, { ...paymentForm })
    else await adminApi.createPaymentMethod({ ...paymentForm })
    resetPayment()
    payments.value = await adminApi.paymentMethods()
    toast.show('Payment method saved.')
  } catch (e) {
    error.value = typeof e.response?.data?.detail === 'string' ? e.response.data.detail : 'Could not save payment settings.'
  }
}
async function removePayment(row) {
  if (!confirm(`Delete “${row.name}”?`)) return
  await adminApi.deletePaymentMethod(row.id)
  payments.value = await adminApi.paymentMethods()
}

onMounted(() => {
  if (typeof Intl.supportedValuesOf === 'function') {
    timezoneOptions.value = Intl.supportedValuesOf('timeZone')
  }
  load()
})
</script>

<template>
<section class="admin-page">
  <div class="admin-page-head">
    <div>
      <p>CONFIGURATION</p>
      <h1 class="ui-display">Store settings</h1>
      <span>Store identity, contacts, working hours, SEO, availability, checkout and notifications.</span>
    </div>
    <a class="admin-back" href="/" target="_blank" rel="noopener">Open storefront ↗</a>
  </div>

  <div v-if="error" class="admin-alert">{{ error }}</div>
  <div v-if="loading" class="admin-loading">Loading…</div>

  <template v-else>
    <div class="settings-tabs">
      <button v-for="item in tabs" :key="item[0]" type="button" :class="{ active: tab === item[0] }" @click="tab = item[0]">{{ item[1] }}</button>
    </div>

    <form v-if="['general', 'hours', 'seo', 'system', 'notifications'].includes(tab)" class="admin-panel settings-panel" @submit.prevent="saveSettings">
      <template v-if="tab === 'general'">
        <div class="admin-panel-head settings-section-head">
          <div><small>IDENTITY</small><h2>Store identity & contacts</h2><p>These values are published on the storefront immediately after saving and reloading the public page.</p></div>
        </div>
        <div class="settings-grid">
          <label class="admin-field"><span>Store name</span><input v-model="settings.store_name" maxlength="160" required></label>
          <label class="admin-field"><span>Brand tagline</span><input v-model="settings.brand_tagline" maxlength="120" placeholder="YOUR TAGLINE"></label>
          <label class="admin-field"><span>Phone</span><input v-model="settings.phone" maxlength="40" autocomplete="tel"></label>
          <label class="admin-field"><span>Email</span><input v-model="settings.email" type="email" maxlength="320" autocomplete="email"></label>
          <label class="admin-field"><span>Service region</span><input v-model="settings.service_region" maxlength="120" placeholder="Worldwide"></label>
          <div class="admin-info-box">Phone, email and service region are used by the header, footer and contact dialog. Empty contact fields are hidden from customers.</div>
          <label class="admin-field admin-field--wide"><span>Footer description</span><textarea v-model="settings.footer_description" rows="3" maxlength="800"></textarea><small>Shown under the store logo in the footer.</small></label>
        </div>
      </template>

      <template v-if="tab === 'hours'">
        <div class="admin-panel-head settings-section-head">
          <div><small>AVAILABILITY</small><h2>Business hours</h2><p>Choose opening and closing times for every day. The storefront receives a generated compact summary.</p></div>
        </div>
        <div class="business-hours-toolbar">
          <label class="admin-field business-hours-timezone"><span>Timezone</span><input v-model="settings.timezone" list="velmora-timezones" maxlength="64" placeholder="UTC"><datalist id="velmora-timezones"><option v-for="zone in timezoneOptions" :key="zone" :value="zone"></option></datalist></label>
          <div class="business-hours-actions"><button type="button" @click="copyMondayToWeekdays">Copy Monday to weekdays</button><button type="button" @click="resetBusinessHours">Reset schedule</button></div>
        </div>
        <div class="business-hours-list">
          <article v-for="(dayDef, index) in dayDefinitions" :key="dayDef[0]" class="business-hours-row" :class="{ 'is-closed': !businessHours[index].enabled }">
            <label class="business-hours-day"><input v-model="businessHours[index].enabled" type="checkbox"><span><strong>{{ dayDef[1] }}</strong><small>{{ businessHours[index].enabled ? 'Open' : 'Closed' }}</small></span></label>
            <div v-if="businessHours[index].enabled" class="business-hours-time">
              <span>From</span>
              <select :value="timeHour(businessHours[index].open)" @change="setTimePart(businessHours[index], 'open', 'hour', $event.target.value)"><option v-for="hour in hourOptions" :key="hour" :value="hour">{{ hour }}</option></select>
              <span>:</span>
              <select :value="timeMinute(businessHours[index].open)" @change="setTimePart(businessHours[index], 'open', 'minute', $event.target.value)"><option v-for="minute in minuteOptions" :key="minute" :value="minute">{{ minute }}</option></select>
              <span class="business-hours-divider">to</span>
              <select :value="timeHour(businessHours[index].close)" @change="setTimePart(businessHours[index], 'close', 'hour', $event.target.value)"><option v-for="hour in hourOptions" :key="hour" :value="hour">{{ hour }}</option></select>
              <span>:</span>
              <select :value="timeMinute(businessHours[index].close)" @change="setTimePart(businessHours[index], 'close', 'minute', $event.target.value)"><option v-for="minute in minuteOptions" :key="minute" :value="minute">{{ minute }}</option></select>
            </div>
            <div v-else class="business-hours-closed">Not working</div>
          </article>
        </div>
        <div class="business-hours-preview"><small>STOREFRONT PREVIEW</small><strong>{{ hoursPreview }}</strong><span>Saved summary currently: {{ settings.working_hours || '—' }}</span></div>
      </template>

      <template v-if="tab === 'seo'">
        <div class="admin-panel-head settings-section-head"><div><small>DISCOVERY</small><h2>SEO metadata</h2><p>Default metadata used by the home page and social previews.</p></div></div>
        <div class="settings-grid settings-grid--single">
          <label class="admin-field"><span>SEO title</span><input v-model="settings.seo_title" maxlength="240" placeholder="Your store — official website"></label>
          <label class="admin-field"><span>SEO description</span><textarea v-model="settings.seo_description" rows="4" maxlength="500"></textarea></label>
          <label class="admin-field"><span>Open Graph image (OG)</span><input v-model="settings.seo_og_image" maxlength="500" placeholder="/media/... or https://..."></label>
          <div class="admin-info-box">Product pages generate their own title, description and product price metadata. These values are the store-wide fallback.</div>
        </div>
      </template>

      <template v-if="tab === 'system'">
        <div class="admin-panel-head settings-section-head"><div><small>STORE STATUS</small><h2>Availability controls</h2><p>Pause checkout or replace the public storefront with a maintenance screen without affecting the admin panel.</p></div></div>
        <div class="settings-grid settings-grid--single">
          <label class="settings-switch"><input v-model="settings.maintenance_mode" type="checkbox"><span><strong>Maintenance mode</strong><small>The storefront shows the maintenance page while the admin panel stays available.</small></span></label>
          <label class="admin-field"><span>Maintenance title</span><input v-model="settings.maintenance_title" maxlength="240"></label>
          <label class="admin-field"><span>Maintenance message</span><textarea v-model="settings.maintenance_message" rows="5" maxlength="2000"></textarea></label>
          <label class="settings-switch"><input v-model="settings.orders_enabled" type="checkbox"><span><strong>Accept orders</strong><small>When disabled, product pages remain public but checkout buttons and order creation are blocked.</small></span></label>
        </div>
      </template>

      <template v-if="tab === 'notifications'">
        <div class="admin-panel-head settings-section-head"><div><small>ORDER ALERTS</small><h2>Notifications</h2><p>Choose which configured server-side notification channels should receive new-order alerts.</p></div></div>
        <div class="settings-grid settings-grid--single">
          <label class="settings-switch"><input v-model="settings.notification_email_enabled" type="checkbox"><span><strong>Email notifications</strong><small>New orders will be sent to the recipient address below when SMTP is configured on the server.</small></span></label>
          <label class="admin-field"><span>Recipient email</span><input v-model="settings.notification_email_to" type="email" maxlength="320"></label>
          <label class="settings-switch"><input v-model="settings.notification_telegram_enabled" type="checkbox"><span><strong>Telegram notifications</strong><small>New orders will be sent to the specified chat when a bot token is configured on the server.</small></span></label>
          <label class="admin-field"><span>Telegram chat ID</span><input v-model="settings.notification_telegram_chat_id" maxlength="120"></label>
          <div class="admin-info-box">SMTP passwords and Telegram bot tokens stay in server secrets and are never returned to the browser. Store Settings only enable a channel and select its destination.</div>
        </div>
      </template>

      <div class="settings-savebar"><div><small v-if="tab === 'hours'">{{ hoursPreview }}</small></div><button class="btn btn-primary" type="submit" :disabled="saving">{{ saving ? 'Saving…' : 'Save changes' }}</button></div>
    </form>

    <div v-if="tab === 'shipping'" class="settings-manage-grid">
      <section class="admin-panel">
        <div class="admin-panel-head"><div><small>SHIPPING METHODS</small><h2>Available to customers</h2><p>Only active methods are shown during checkout.</p></div></div>
        <div class="settings-method-list"><article v-for="row in shipping" :key="row.id"><div><strong>{{ row.name }}</strong><span>{{ row.description }}</span><small>{{ row.code }} · {{ row.is_active ? 'active' : 'disabled' }}<template v-if="row.price_minor"> · {{ formatMoney(row.price_minor) }}</template></small></div><div><button type="button" @click="editShipping(row)">Edit</button><button type="button" @click="removeShipping(row)">Delete</button></div></article><div v-if="!shipping.length" class="settings-empty">No shipping methods configured.</div></div>
      </section>
      <form class="admin-panel settings-editor" @submit.prevent="saveShipping">
        <div class="admin-panel-head"><div><small>{{ editingShipping ? 'EDITING' : 'NEW METHOD' }}</small><h2>Shipping</h2></div><button v-if="editingShipping" type="button" @click="resetShipping">Cancel</button></div>
        <label class="admin-field"><span>Code</span><input v-model="shippingForm.code" pattern="[a-z0-9-]+" required></label>
        <label class="admin-field"><span>Name</span><input v-model="shippingForm.name" required></label>
        <label class="admin-field"><span>Customer description</span><textarea v-model="shippingForm.description" rows="3"></textarea></label>
        <label class="admin-field"><span>Carrier</span><input v-model="shippingForm.carrier"></label>
        <label class="admin-field"><span>Price</span><input v-model.number="shippingForm.price_amount" type="number" min="0" step="0.01"></label>
        <label class="admin-field"><span>Sort order</span><input v-model.number="shippingForm.sort_order" type="number" min="-10000" max="10000"></label>
        <div class="settings-checks"><label><input v-model="shippingForm.requires_city" type="checkbox">City</label><label><input v-model="shippingForm.requires_branch" type="checkbox">Branch</label><label><input v-model="shippingForm.requires_address" type="checkbox">Address</label><label><input v-model="shippingForm.is_active" type="checkbox">Active</label></div>
        <button class="btn btn-primary" type="submit">Save method</button>
      </form>
    </div>

    <div v-if="tab === 'payment'" class="settings-manage-grid">
      <section class="admin-panel">
        <div class="admin-panel-head"><div><small>PAYMENT METHODS</small><h2>Available to customers</h2><p>Only active methods are shown during checkout.</p></div></div>
        <div class="settings-method-list"><article v-for="row in payments" :key="row.id"><div><strong>{{ row.name }}</strong><span>{{ row.description }}</span><small>{{ row.code }} · {{ row.is_active ? 'active' : 'disabled' }}</small></div><div><button type="button" @click="editPayment(row)">Edit</button><button type="button" @click="removePayment(row)">Delete</button></div></article><div v-if="!payments.length" class="settings-empty">No payment methods configured.</div></div>
      </section>
      <form class="admin-panel settings-editor" @submit.prevent="savePayment">
        <div class="admin-panel-head"><div><small>{{ editingPayment ? 'EDITING' : 'NEW METHOD' }}</small><h2>Payment</h2></div><button v-if="editingPayment" type="button" @click="resetPayment">Cancel</button></div>
        <label class="admin-field"><span>Code</span><input v-model="paymentForm.code" pattern="[a-z0-9-]+" required></label>
        <label class="admin-field"><span>Name</span><input v-model="paymentForm.name" required></label>
        <label class="admin-field"><span>Description</span><textarea v-model="paymentForm.description" rows="3"></textarea></label>
        <label class="admin-field"><span>Instructions after selection</span><textarea v-model="paymentForm.instructions" rows="4"></textarea></label>
        <label class="admin-field"><span>Sort order</span><input v-model.number="paymentForm.sort_order" type="number" min="-10000" max="10000"></label>
        <label class="settings-switch"><input v-model="paymentForm.is_active" type="checkbox"><span><strong>Active</strong><small>Show this method to customers during checkout.</small></span></label>
        <button class="btn btn-primary" type="submit">Save method</button>
      </form>
    </div>
  </template>
</section>
</template>
