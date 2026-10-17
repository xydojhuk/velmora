<script setup>
import { computed } from 'vue'
import { useHead } from '@unhead/vue'
import { useAppState } from '../composables/useAppState.js'
import { useStoreInfo } from '../composables/useStoreInfo.js'
import { validGoogleAnalyticsId, validGoogleTagManagerId, validVerificationToken } from '../utils/seo.js'

const state = useAppState()
const store = useStoreInfo()
const runtime = computed(() => state.runtimeConfig || {})
const googleVerification = computed(() => validVerificationToken(runtime.value.googleSiteVerification))
const bingVerification = computed(() => validVerificationToken(runtime.value.bingSiteVerification))
const yandexVerification = computed(() => validVerificationToken(runtime.value.yandexSiteVerification))
const gaId = computed(() => validGoogleAnalyticsId(runtime.value.googleAnalyticsId))
const gtmId = computed(() => validGoogleTagManagerId(runtime.value.googleTagManagerId))

useHead(() => {
  const meta = [
    { name: 'application-name', content: store.value.name },
    { name: 'apple-mobile-web-app-title', content: store.value.name },
    { name: 'format-detection', content: 'telephone=no' },
    { name: 'theme-color', content: store.value.storefront.theme.background }
  ]
  if (googleVerification.value) meta.push({ name: 'google-site-verification', content: googleVerification.value })
  if (bingVerification.value) meta.push({ name: 'msvalidate.01', content: bingVerification.value })
  if (yandexVerification.value) meta.push({ name: 'yandex-verification', content: yandexVerification.value })

  const script = []
  if (gtmId.value) {
    script.push({
      nonce: state.cspNonce || undefined,
      innerHTML: `(function(w,d,s,l,i){w[l]=w[l]||[];w[l].push({'gtm.start':new Date().getTime(),event:'gtm.js'});var f=d.getElementsByTagName(s)[0],j=d.createElement(s),dl=l!='dataLayer'?'&l='+l:'';j.async=true;j.src='https://www.googletagmanager.com/gtm.js?id='+i+dl;f.parentNode.insertBefore(j,f);})(window,document,'script','dataLayer','${gtmId.value}');`
    })
  } else if (gaId.value) {
    script.push({ src: `https://www.googletagmanager.com/gtag/js?id=${gaId.value}`, async: true, nonce: state.cspNonce || undefined })
    script.push({
      nonce: state.cspNonce || undefined,
      innerHTML: `window.dataLayer=window.dataLayer||[];window.gtag=function(){window.dataLayer.push(arguments)};window.gtag('js',new Date());window.gtag('config','${gaId.value}',{send_page_view:false});`
    })
  }

  return {
    htmlAttrs: { lang: 'en' },
    link: [
      { rel: 'manifest', href: '/site.webmanifest' },
      { rel: 'icon', href: store.value.logoUrl }
    ],
    meta,
    script
  }
})
</script>

<template></template>
