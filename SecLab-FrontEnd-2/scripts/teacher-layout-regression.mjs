import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { dirname, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

const here = dirname(fileURLToPath(import.meta.url))
const source = readFileSync(resolve(here, '../src/layout/Teacher/index.vue'), 'utf8')

const escapeRegex = (value) => value.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')

const ruleBody = (selector) => {
  const match = source.match(new RegExp(`${escapeRegex(selector)}\\s*\\{([^}]*)\\}`))
  assert.ok(match, `${selector} CSS rule must exist`)
  return match[1]
}

const assertDeclaration = (body, property, value) => {
  const declaration = new RegExp(
    `(?:^|;)\\s*${escapeRegex(property)}\\s*:\\s*${escapeRegex(value)}\\s*(?=;|$)`,
  )
  assert.match(body, declaration, `${property}: ${value} must be declared`)
}

const shell = ruleBody('.teacher-shell')
assertDeclaration(shell, 'height', '100vh')
assertDeclaration(shell, 'height', '100dvh')
assertDeclaration(shell, 'overflow', 'hidden')

const main = ruleBody('.teacher-main')
assertDeclaration(main, 'height', '100vh')
assertDeclaration(main, 'height', '100dvh')
assertDeclaration(main, 'min-height', '0')
assertDeclaration(main, 'overflow-x', 'hidden')
assertDeclaration(main, 'overflow-y', 'auto')

console.log('teacher layout scroll regression: PASS')
