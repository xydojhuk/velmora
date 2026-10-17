import fs from 'node:fs/promises'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { compileScript, compileTemplate, parse } from '@vue/compiler-sfc'

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..')

async function walk(dir) {
  const entries = await fs.readdir(dir, { withFileTypes: true })
  const files = []
  for (const entry of entries) {
    const full = path.join(dir, entry.name)
    if (entry.isDirectory()) files.push(...await walk(full))
    else files.push(full)
  }
  return files
}

const files = await walk(path.join(root, 'src'))
const vueFiles = files.filter(file => file.endsWith('.vue'))
let failed = false

for (const file of vueFiles) {
  const source = await fs.readFile(file, 'utf8')
  const id = path.relative(root, file)
  const parsed = parse(source, { filename: id })
  if (parsed.errors.length) {
    failed = true
    console.error(id, parsed.errors)
    continue
  }
  const descriptor = parsed.descriptor
  if (descriptor.scriptSetup) {
    try {
      compileScript(descriptor, { id })
    } catch (error) {
      failed = true
      console.error(id, error.message)
    }
  }
  if (descriptor.template) {
    const result = compileTemplate({ source: descriptor.template.content, filename: id, id })
    if (result.errors.length) {
      failed = true
      console.error(id, result.errors)
    }
  }
}

if (failed) process.exit(1)
console.log(`Checked ${vueFiles.length} Vue components successfully.`)
