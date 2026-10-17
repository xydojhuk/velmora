<script setup>
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { RouterLink, useRoute } from 'vue-router'
import AppIcon from '../components/AppIcon.vue'
import { publicApi } from '../api/services.js'
import { useAppState } from '../composables/useAppState.js'
import { useSeo } from '../composables/useSeo.js'
import { useStoreInfo } from '../composables/useStoreInfo.js'
import { storeInfo } from '../state/fallback.js'
import { formatMoney, normalizeImage } from '../utils/format.js'

const route = useRoute()
const state = useAppState()
const store = useStoreInfo()
// SSR data is only valid for the route that originally rendered the page.
// Vue Router navigation from / must fetch the checkout product itself.
const product = ref(state.pageData.product?.slug === route.params.slug ? state.pageData.product : null)
const productLoading = ref(!product.value && !state.pageData.productMissing)
const productNotFound = ref(Boolean(state.pageData.productMissing && !product.value))
const productError = ref('')
let latestLoad = 0
async function loadCheckoutProduct(slug) {
  if (!slug) return
  const requestId = ++latestLoad
  productLoading.value = true
  productNotFound.value = false
  productError.value = ''
  product.value = null
  try {
    const found = await publicApi.product(slug)
    if (latestLoad !== requestId) return
    product.value = found
    state.apiOnline = true
  } catch (error) {
    if (latestLoad !== requestId) return
    if (error.response?.status === 404) productNotFound.value = true
    else productError.value = 'Could not load this product. Please retry.'
  } finally {
    if (latestLoad === requestId) productLoading.value = false
  }
}
watch(() => route.params.slug, slug => {
  quantity.value = 1
  success.value = null
  checkoutAttempt.value = null
  loadCheckoutProduct(slug)
})
const quantity = ref(1)
const submitting = ref(false)
const error = ref('')
const success = ref(null)
const form = reactive({
  customer_name: '', customer_phone: '', customer_email: '', shipping_method: '', shipping_city: '', shipping_branch: '', shipping_address: '', payment_method: '', customer_note: '', website: ''
})
const selectedShipping = computed(() => store.value.shippingMethods.find(item => item.code === form.shipping_method) || null)
const selectedPayment = computed(() => store.value.paymentMethods.find(item => item.code === form.payment_method) || null)
const shippingPrice = computed(() => selectedShipping.value?.price_minor || 0)
const inStock = computed(() => !product.value?.track_inventory || product.value.stock_quantity >= quantity.value)
const fulfillmentAvailable = computed(() => store.value.shippingMethods.length > 0 && store.value.paymentMethods.length > 0)
const shippingFieldCount = computed(() => {
  const method = selectedShipping.value
  if (!method) return 0
  return Number(Boolean(method.requires_city)) + Number(Boolean(method.requires_branch)) + Number(Boolean(method.requires_address))
})
const shippingFieldsStacked = computed(() => Boolean(selectedShipping.value?.requires_address) && !selectedShipping.value?.requires_branch)
const total = computed(() => (product.value?.price_minor || 0) * quantity.value + shippingPrice.value)

useSeo({ title: product.value ? `Checkout — ${product.value.title} | ${store.value.name}` : `Checkout | ${store.value.name}`, description: 'Complete your order.', path: route.path, noindex: true })

onMounted(async () => {
  if (!product.value) await loadCheckoutProduct(route.params.slug)
  const requestedQuantity = Number.parseInt(String(route.query.quantity || ''), 10)
  if (Number.isInteger(requestedQuantity)) quantity.value = Math.min(99, Math.max(1, requestedQuantity))
  if (!state.pageData.storeConfig) {
    try { state.pageData.storeConfig = await publicApi.config() } catch { state.apiOnline = false }
  }
  const firstShipping = store.value.shippingMethods[0]
  const firstPayment = store.value.paymentMethods[0]
  if (!form.shipping_method && firstShipping) form.shipping_method = firstShipping.code
  if (!form.payment_method && firstPayment) form.payment_method = firstPayment.code
})

function idempotencyKey() {
  return typeof crypto !== 'undefined' && crypto.randomUUID ? crypto.randomUUID() : `${Date.now()}-${Math.random().toString(36).slice(2)}`
}

const checkoutAttempt = ref(null)

async function submit() {
  if (!product.value || !state.apiOnline || !store.value.ordersEnabled || !fulfillmentAvailable.value || !inStock.value) return
  error.value = ''
  success.value = null
  if (!form.shipping_method || !form.payment_method) {
    error.value = 'Choose a shipping and payment method.'
    return
  }
  if (selectedShipping.value?.requires_city && !form.shipping_city.trim()) { error.value = 'Enter a city for the selected shipping method.'; return }
  if (selectedShipping.value?.requires_branch && !form.shipping_branch.trim()) { error.value = 'Enter a branch or parcel locker.'; return }
  if (selectedShipping.value?.requires_address && !form.shipping_address.trim()) { error.value = 'Enter a delivery address.'; return }
  submitting.value = true
  try {
    const orderPayload = {
      customer_name: form.customer_name,
      customer_phone: form.customer_phone,
      customer_email: form.customer_email || null,
      items: [{ product_slug: product.value.slug, quantity: quantity.value }],
      shipping_method: form.shipping_method,
      shipping_city: form.shipping_city || null,
      shipping_branch: form.shipping_branch || null,
      shipping_address: form.shipping_address || null,
      payment_method: form.payment_method,
      customer_note: form.customer_note || null,
      website: form.website || null
    }
    const payloadSignature = JSON.stringify(orderPayload)
    if (checkoutAttempt.value?.signature !== payloadSignature) {
      checkoutAttempt.value = { signature: payloadSignature, key: idempotencyKey() }
    }
    success.value = await publicApi.order(orderPayload, checkoutAttempt.value.key)
  } catch (e) {
    const detail = e.response?.data?.detail
    error.value = typeof detail === 'string' ? detail : 'Could not create the order. Check the details and try again.'
  } finally { submitting.value = false }
}
</script>

<template>
  <section v-if="productLoading" class="checkout-page checkout-feedback" role="status" aria-live="polite">
    <p class="checkout-kicker">CHECKOUT</p><h1 class="ui-display">Loading product…</h1>
  </section>
  <section v-else-if="product" class="checkout-page">
    <nav class="checkout-breadcrumbs" aria-label="Navigation">
      <RouterLink to="/">Home</RouterLink>
      <span>›</span>
      <RouterLink :to="`/product/${product.slug}`">{{ product.title }}</RouterLink>
      <span>›</span>
      <strong>Checkout</strong>
    </nav>

    <div v-if="success" class="checkout-success ui-card">
      <div class="checkout-success__icon"><AppIcon name="shield-check" /></div>
      <div class="checkout-success__content">
        <p class="checkout-kicker">ORDER RECEIVED</p>
        <h1 class="ui-display">{{ success.order_number }}</h1>
        <p>We will contact you to confirm the details. Keep your order number for reference.</p>
        <div class="checkout-success__actions">
          <RouterLink class="btn btn-primary" to="/">Back home</RouterLink>
        </div>
      </div>
    </div>

    <div v-else class="checkout-grid">
      <form class="checkout-form" @submit.prevent="submit">
        <p v-if="!inStock" class="admin-alert" role="alert">Requested quantity is not in stock. Please reduce the quantity.</p>
        <header class="checkout-heading">
          <p class="checkout-kicker">CHECKOUT</p>
          <h1 class="ui-display">Order details</h1>
          <p>Enter your contact details and choose a shipping and payment method.</p>
        </header>

        <section class="checkout-section ui-card">
          <div class="checkout-section__head">
            <span>01</span>
            <div>
              <h2>Contact details</h2>
              <p>We only use these details to confirm and process your order.</p>
            </div>
          </div>
          <div class="form-grid form-grid--2">
            <label class="field">
              <span>Full name</span>
              <input v-model="form.customer_name" maxlength="160" required autocomplete="name">
            </label>
            <label class="field">
              <span>Phone</span>
              <input v-model="form.customer_phone" maxlength="32" required autocomplete="tel">
            </label>
            <label class="field checkout-field--wide">
              <span>Email <em>optional</em></span>
              <input v-model="form.customer_email" type="email" maxlength="320" autocomplete="email">
            </label>
          </div>
          <input v-model="form.website" class="checkout-honeypot" tabindex="-1" autocomplete="off" aria-hidden="true">
        </section>

        <section class="checkout-section ui-card">
          <div class="checkout-section__head">
            <span>02</span>
            <div>
              <h2>Shipping</h2>
              <p>Choose an available method. Required fields will appear automatically.</p>
            </div>
          </div>
          <div v-if="store.shippingMethods.length" class="checkout-option-grid" role="radiogroup" aria-label="Shipping method">
            <button
              v-for="method in store.shippingMethods"
              :key="method.code"
              class="checkout-option"
              :class="{ active: form.shipping_method === method.code }"
              type="button"
              role="radio"
              :aria-checked="form.shipping_method === method.code"
              @click="form.shipping_method = method.code"
            >
              <span class="checkout-option__marker"></span>
              <span class="checkout-option__content">
                <strong>{{ method.name }}</strong>
                <span>{{ method.description }}</span>
                <small v-if="method.price_minor">{{ formatMoney(method.price_minor, product.currency) }}</small>
                <small v-else>Carrier rates / free</small>
              </span>
            </button>
          </div>
          <p v-else class="checkout-method-note">No shipping method is currently active. Contact the store to place an order.</p>
          <div v-if="selectedShipping" class="form-grid checkout-method-fields" :class="{ 'checkout-method-fields--single': shippingFieldCount === 1, 'checkout-method-fields--stacked': shippingFieldsStacked }">
            <label v-if="selectedShipping.requires_city" class="field">
              <span>City</span>
              <input v-model="form.shipping_city" maxlength="160" required autocomplete="address-level2">
            </label>
            <label v-if="selectedShipping.requires_branch" class="field">
              <span>Branch / parcel locker</span>
              <input v-model="form.shipping_branch" maxlength="160" required>
            </label>
            <label v-if="selectedShipping.requires_address" class="field checkout-field--wide">
              <span>Address</span>
              <input v-model="form.shipping_address" maxlength="300" required autocomplete="street-address">
            </label>
          </div>
        </section>

        <section class="checkout-section ui-card">
          <div class="checkout-section__head">
            <span>03</span>
            <div>
              <h2>Payment</h2>
              <p>Choose a payment method and leave a note if needed.</p>
            </div>
          </div>
          <div v-if="store.paymentMethods.length" class="checkout-option-grid" role="radiogroup" aria-label="Payment method">
            <button
              v-for="method in store.paymentMethods"
              :key="method.code"
              class="checkout-option"
              :class="{ active: form.payment_method === method.code }"
              type="button"
              role="radio"
              :aria-checked="form.payment_method === method.code"
              @click="form.payment_method = method.code"
            >
              <span class="checkout-option__marker"></span>
              <span class="checkout-option__content">
                <strong>{{ method.name }}</strong>
                <span>{{ method.description }}</span>
              </span>
            </button>
          </div>
          <p v-else class="checkout-method-note">No payment method is currently active. Contact the store to place an order.</p>
          <p v-if="selectedPayment?.instructions" class="checkout-method-note">{{ selectedPayment.instructions }}</p>
          <label class="field checkout-comment-field">
            <span>Order note</span>
            <textarea v-model="form.customer_note" maxlength="2000" rows="4" placeholder="For example, a convenient time to call"></textarea>
          </label>
        </section>

        <div v-if="!store.ordersEnabled" class="form-error">Orders are temporarily paused. For details, contact us at {{ store.phoneDisplay }}.</div>
        <div v-else-if="!fulfillmentAvailable" class="form-error">Checkout is temporarily unavailable. Contact the store to arrange shipping and payment at {{ store.phoneDisplay }}.</div>
        <div v-if="error" class="form-error" role="alert">{{ error }}</div>

        <button class="btn btn-primary checkout-submit" type="submit" :disabled="submitting || !state.apiOnline || !store.ordersEnabled || !fulfillmentAvailable || !inStock">
          <AppIcon name="cart" />
          {{ submitting ? 'Creating order…' : 'Place order' }}
        </button>
        <p class="checkout-legal">By placing the order, you agree that the entered data may be used to process the order and contact you about it.</p>
      </form>

      <aside class="checkout-summary ui-card">
        <p class="checkout-kicker">YOUR ORDER</p>
        <div class="checkout-summary__image">
          <img :src="normalizeImage(product.primary_image)" :alt="product.title">
        </div>
        <h2 class="ui-display">{{ product.title }}</h2>
        <p>{{ product.subtitle }}</p>
        <div class="checkout-summary__quantity">
          <span>Quantity</span>
          <div>
            <button type="button" aria-label="Decrease quantity" @click="quantity = Math.max(1, quantity - 1)">−</button>
            <strong>{{ quantity }}</strong>
            <button type="button" aria-label="Increase quantity" @click="quantity = Math.min(99, quantity + 1)">+</button>
          </div>
        </div>
        <dl>
          <div><dt>Items</dt><dd>{{ formatMoney(product.price_minor * quantity, product.currency) }}</dd></div>
          <div v-if="shippingPrice"><dt>Shipping</dt><dd>{{ formatMoney(shippingPrice, product.currency) }}</dd></div>
          <div class="checkout-summary__total"><dt>Total</dt><dd>{{ formatMoney(total, product.currency) }}</dd></div>
        </dl>
        <div class="checkout-summary__trust">
          <AppIcon name="shield-check" />
          <span>
            <strong>{{ storeInfo.warranty }}</strong>
            <small>{{ storeInfo.warrantyNote }}</small>
          </span>
        </div>
      </aside>
    </div>
  </section>

  <section v-else class="store-empty">
    <p>{{ productNotFound ? '404 / CHECKOUT' : 'CHECKOUT' }}</p>
    <h1 class="ui-display">{{ productNotFound ? 'Product not found' : 'Product unavailable' }}</h1>
    <p v-if="productError" role="alert">{{ productError }}</p>
    <button v-if="productError" class="btn btn-secondary" type="button" @click="loadCheckoutProduct(route.params.slug)">Try again</button>
    <RouterLink class="btn btn-primary" to="/">Back to catalog</RouterLink>
  </section>
</template>
