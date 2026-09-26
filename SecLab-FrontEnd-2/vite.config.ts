import { defineConfig } from 'vite'
import type { ProxyOptions } from 'vite'
import vue from '@vitejs/plugin-vue'

// 各后端（user-service / experiment-module / image-service / ai-agent）的 CORS 白名单里
// 只有 http://localhost:5173 这类地址。走 cpolar 等隧道访问时，浏览器带的是隧道域名的
// Origin，后端会直接回 403 "Invalid CORS request"。
//
// 代理是服务端到服务端转发，浏览器侧的同源要求已经由 5173 满足了，后端这一跳的 CORS 检查
// 并没有实际意义，所以在转发时把 Origin/Referer 改写成后端认识的值。
// 这样换任何隧道域名都不用再去改后端白名单。
const LOCAL_ORIGIN = 'http://localhost:5173'

function backend(target: string, stripPrefix?: RegExp, ws = false): ProxyOptions {
  return {
    target,
    changeOrigin: true,
    ...(ws ? { ws: true } : {}),
    ...(stripPrefix ? { rewrite: (path: string) => path.replace(stripPrefix, '') } : {}),
    configure: proxy => {
      proxy.on('proxyReq', proxyReq => {
        proxyReq.setHeader('origin', LOCAL_ORIGIN)
        if (proxyReq.getHeader('referer')) {
          proxyReq.setHeader('referer', `${LOCAL_ORIGIN}/`)
        }
      })
    },
  }
}

// https://vite.dev/config/
export default defineConfig({
  plugins: [vue()],
  build: { target: 'esnext' },
  optimizeDeps: { esbuildOptions: { target: 'esnext' } },
  server: {
    host: '0.0.0.0',
    allowedHosts: true,
    proxy: {
      // 将 /api/agent 开头的请求代理到 FastAPI Agent 服务（开发环境）
      '/api/agent': backend('http://localhost:8010', /^\/api\/agent/),
      // 保留旧的 Docker API 代理（兼容）
      '/api/docker': backend('http://localhost:8010', undefined, true),
      // 以下几条配合 .env.local 里的相对路径使用：前端只访问 5173，
      // 由 Vite 转发到各后端，这样 cpolar 只需要转发 5173 一个端口。
      '/user-service': backend('http://localhost:8083', /^\/user-service/),
      '/experiment-module': backend('http://localhost:8084', /^\/experiment-module/),
      '/image-service': backend('http://localhost:8086', /^\/image-service/),
      '/docker-api': backend('http://localhost:3000', /^\/docker-api/, true),
      // 漏洞靶场容器：iframe 里的靶机地址已由前端 cleanUrl() 改写成 /lab-<端口>，
      // 这里把它们转发到对应容器，一条隧道即可覆盖所有靶场。
      '/lab-8090': backend('http://localhost:8090', /^\/lab-8090/),   // 命令注入
      '/lab-8091': backend('http://localhost:8091', /^\/lab-8091/),   // SQL 注入
      '/lab-8092': backend('http://localhost:8092', /^\/lab-8092/),   // XSS
      '/lab-8093': backend('http://localhost:8093', /^\/lab-8093/),   // CSRF
      '/lab-8094': backend('http://localhost:8094', /^\/lab-8094/),   // 文件上传
      '/lab-8095': backend('http://localhost:8095', /^\/lab-8095/),   // 目录遍历
      '/lab-8896': backend('http://localhost:8896', /^\/lab-8896/),   // 协议分析
    }
  }
})
