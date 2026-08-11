// Pulls the live OpenAPI spec from the backend so `generate:api-types` has
// something fresh to generate from. Run this whenever backend routes change.
import { writeFile } from 'node:fs/promises'

const apiUrl = process.env.VITE_API_URL ?? 'http://localhost:8000'
const url = `${apiUrl.replace(/\/$/, '')}/openapi.json`

const res = await fetch(url)
if (!res.ok) {
  throw new Error(`Failed to fetch OpenAPI spec from ${url}: ${res.status} ${res.statusText}`)
}

const spec = await res.json()
await writeFile('./openapi.json', JSON.stringify(spec, null, 2) + '\n')

const pathCount = Object.keys(spec.paths ?? {}).length
console.log(`Wrote openapi.json from ${url} (${pathCount} path${pathCount === 1 ? '' : 's'})`)
