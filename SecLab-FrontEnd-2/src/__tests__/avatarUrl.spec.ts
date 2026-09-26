import { describe, expect, it } from 'vitest'
import { avatarUrl } from '../api'

// 库里存的是 image-service 返回的文件名，显示时才拼出完整地址，
// 这样换机器 / 换端口 / 走外网都不会把已有头像变成裂图。
describe('avatarUrl', () => {
  it('把文件名拼成图片服务地址', () => {
    expect(avatarUrl('avatar_125902ec.png')).toBe(
      'http://localhost:8086/api/images/files/avatar_125902ec.png',
    )
  })

  it('文件名里的特殊字符会被转义', () => {
    expect(avatarUrl('avatar 头像.png')).toBe(
      'http://localhost:8086/api/images/files/avatar%20%E5%A4%B4%E5%83%8F.png',
    )
  })

  it('老数据里的绝对 URL 原样返回，不二次拼接', () => {
    const stored = 'http://127.0.0.1:8086/api/images/files/avatar_old.png'
    expect(avatarUrl(stored)).toBe(stored)
    expect(avatarUrl('https://cdn.example.com/a.png')).toBe('https://cdn.example.com/a.png')
    expect(avatarUrl('//cdn.example.com/a.png')).toBe('//cdn.example.com/a.png')
  })

  it('站内相对路径和本地预览地址原样返回', () => {
    expect(avatarUrl('/example.png')).toBe('/example.png')
    expect(avatarUrl('blob:http://localhost:5173/abc')).toBe('blob:http://localhost:5173/abc')
    expect(avatarUrl('data:image/png;base64,AAAA')).toBe('data:image/png;base64,AAAA')
  })

  it('空值返回空串，让调用方走占位图标分支', () => {
    expect(avatarUrl('')).toBe('')
    expect(avatarUrl('   ')).toBe('')
    expect(avatarUrl(null)).toBe('')
    expect(avatarUrl(undefined)).toBe('')
  })
})
