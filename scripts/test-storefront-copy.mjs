#!/usr/bin/env node
// Private, dependency-free regression for old placeholder content and project credit.
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
const readJson = name => JSON.parse(readFileSync(new URL(name, import.meta.url), 'utf8'))
const canonical = readJson('../frontend/src/state/storefrontDefaults.json')
const legacy = readJson('../frontend/src/state/legacyStorefrontCopy.json')
let source = readFileSync(new URL('../frontend/src/state/storefrontDefaults.js', import.meta.url), 'utf8')
source = source.replace(/^import .+\n/gm, '').replace(/\bexport /g, '')
const { mergeStorefrontConfig } = new Function('canonicalStorefront', 'legacyCopy', `${source}\nreturn { mergeStorefrontConfig }`)(canonical, legacy)
const old = JSON.parse(JSON.stringify(legacy))
assert.notEqual(mergeStorefrontConfig(old).modals.about.lead, old.modals.about.lead)
assert.notEqual(mergeStorefrontConfig(old).modals.shipping.note, old.modals.shipping.note)
assert.notEqual(mergeStorefrontConfig(old).platform.support_text, old.platform.support_text)
const customized = mergeStorefrontConfig({ modals: { about: { title: 'My original copy', stats: [{ value: 'PUPUPU', label: 'STAT' }] } }, platform: { enabled: false, repository_url: '' } })
assert.equal(customized.modals.about.title, 'My original copy')
assert.equal(customized.modals.about.stats[0].value, 'PUPUPU')
assert.equal(customized.platform.enabled, true)
assert.equal(customized.platform.repository_url, 'https://github.com/xydojhuk/velmora')
console.log('Storefront legacy copy and mandatory project attribution OK')
