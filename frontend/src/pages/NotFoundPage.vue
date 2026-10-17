<script setup>
import { useSeo } from '../composables/useSeo.js'
useSeo({ title: 'Page not found | VELMORA', description: 'Page not found.', path: '/404', noindex: true })
</script>

<template>
  <section class="store-empty not-found"><p>404 / NOT FOUND</p><h1 class="ui-display">This page does not exist</h1><span>The link may have changed or the page may have been removed.</span><RouterLink class="btn btn-primary" to="/">Back home</RouterLink></section>
</template>
