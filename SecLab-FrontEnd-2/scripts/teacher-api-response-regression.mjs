import fs from 'node:fs'
import vm from 'node:vm'
import ts from 'typescript'

const apiSource = fs.readFileSync(new URL('../src/api.ts', import.meta.url), 'utf8')
const match = apiSource.match(/function unwrapTeacherResult<[\s\S]*?\r?\n}\r?\n/)

if (!match) {
  throw new Error('unwrapTeacherResult implementation was not found')
}

const executable = ts.transpileModule(
  `${match[0]}\n;globalThis.unwrapTeacherResult = unwrapTeacherResult;`,
  { compilerOptions: { target: ts.ScriptTarget.ES2022 } },
).outputText
const context = vm.createContext({ globalThis: {} })
vm.runInContext(executable, context)

const payload = [{ teachingClassId: 1, className: '网络安全232班' }]
const result = context.globalThis.unwrapTeacherResult(
  { status: 200, message: '教学班列表加载成功', data: payload },
  '教学班列表加载失败',
)

if (result !== payload) {
  throw new Error('successful status/data response was not unwrapped')
}

console.log('teacher API status/data response is accepted')
