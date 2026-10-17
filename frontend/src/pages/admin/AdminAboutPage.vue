<script setup>
import { VELMORA_VERSION } from '../../utils/version.js'
import { useSeo } from '../../composables/useSeo.js'
useSeo({ title: 'About Velmora | Admin', description: 'Project and release information', path: '/admin/about', noindex: true })
const repo = 'https://github.com/xydojhuk/velmora'
</script>
<template>
  <section class="admin-page project-about-page">
    <header class="admin-page-head"><div><p>PLATFORM</p><h1 class="ui-display">About Velmora</h1><span>Information about the software behind this store.</span></div></header>
    <div class="project-about-grid">
      <article class="admin-panel project-about-hero">
        <div class="project-about-mark" aria-hidden="true">&lt;/&gt;</div>
        <p class="project-about-eyebrow">INDEPENDENT OPEN-SOURCE E-COMMERCE</p>
        <h2>Own your storefront.</h2>
        <p>Velmora is a self-hosted e-commerce platform. Your installation, content, catalog, and customer data stay under your control.</p>
        <a class="btn btn-primary" :href="repo" target="_blank" rel="noopener noreferrer">View project on GitHub ↗</a>
      </article>
      <article class="admin-panel project-release-card">
        <p class="project-about-eyebrow">INSTALLED VERSION</p>
        <strong class="project-release-number">v{{ VELMORA_VERSION }}</strong>
        <p>This version is read from the application's VERSION file when the build is created.</p>
        <p class="project-release-meta">Update management will appear here in a future release. Updates are currently performed by the server administrator.</p>
        <a class="project-repo-link" :href="repo" target="_blank" rel="noopener noreferrer">Source code and releases ↗</a>
      </article>
    </div>
  </section>
</template>
