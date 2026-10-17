<script setup>
import AppIcon from './AppIcon.vue'
import { useStoreInfo } from '../composables/useStoreInfo.js'

const store = useStoreInfo()
</script>

<template>
  <section class="maintenance-screen">
    <div class="maintenance-screen__card ui-card">
      <div class="maintenance-screen__icon"><AppIcon name="pulse" /></div>
      <p class="maintenance-screen__eyebrow">{{ store.name }} / SERVICE</p>
      <h1 class="ui-display">{{ store.maintenanceTitle }}</h1>
      <p>{{ store.maintenanceMessage }}</p>
      <div class="maintenance-screen__contacts">
        <a :href="`tel:${store.phoneHref}`">{{ store.phoneDisplay }}</a>
        <a :href="`mailto:${store.email}`">{{ store.email }}</a>
        <span>{{ store.hours }}</span>
      </div>
    </div>
  </section>
</template>
