import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { dirname, resolve } from 'node:path'

const root = resolve(dirname(fileURLToPath(import.meta.url)), '..')
const page = readFileSync(resolve(root, 'src/pages/Teacher/TeachingClasses/index.vue'), 'utf8')
const api = readFileSync(resolve(root, 'src/api.ts'), 'utf8')
const cors = readFileSync(
  resolve(root, '../seclab-backend/user-service/src/main/kotlin/me/myot233/seclab/userservice/config/CorsConfig.kt'),
  'utf8',
)
const gatewayCors = readFileSync(
  resolve(root, '../seclab-backend/gateway/src/main/resources/application.yml'),
  'utf8',
)

assert.match(api, /teachingContent\?: string \| null/)
assert.match(api, /export async function updateTeachingClassCourseContent/)
assert.match(api, /axios\.patch<Result<TeachingClassCourseDto>>/)
assert.match(api, /courses\/\$\{courseId\}\/content/)
assert.match(cors, /allowedMethods\([^)]*"PATCH"/)
assert.match(gatewayCors, /allowedMethods:[\s\S]*?- PATCH[\s\S]*?allowedHeaders:/)

assert.match(page, /updateTeachingClassCourseContent/)
assert.match(page, /const openTeachingContentEditor =/)
assert.match(page, /const saveTeachingContent = async/)
assert.match(page, /class="course-content-edit"/)
assert.match(page, /v-model="teachingContentForm"/)
assert.match(page, /course\.teachingContent \|\| course\.courseDescription/)

console.log('teacher arrangement content regression: PASS')
