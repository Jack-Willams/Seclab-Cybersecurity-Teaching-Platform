<script setup lang="ts">
import MarkdownIt from "markdown-it";
import { computed } from 'vue'
import hljs from "highlight.js/lib/core";
import c from "highlight.js/lib/languages/c";
import cpp from "highlight.js/lib/languages/cpp";
import bash from "highlight.js/lib/languages/bash";
import python from "highlight.js/lib/languages/python";
import x86asm from "highlight.js/lib/languages/x86asm";
import plaintext from "highlight.js/lib/languages/plaintext";
// 语法高亮配色沿用全局 main.ts 引入的 github（浅色）主题，代码块统一浅底彩色 token，
// 浅色/深色应用主题下均清晰可见（见下方 <style> 固定的浅色代码块底色）。

// main.ts 只注册了 cpp/shell/python 等，这里补注册实验文档实际用到但缺失的 c/bash/text
hljs.registerLanguage("c", c);
hljs.registerLanguage("cpp", cpp);
hljs.registerLanguage("bash", bash);
hljs.registerLanguage("shell", bash);
hljs.registerLanguage("sh", bash);
hljs.registerLanguage("python", python);
hljs.registerLanguage("py", python);
hljs.registerLanguage("x86asm", x86asm);
hljs.registerLanguage("asm", x86asm);
hljs.registerLanguage("text", plaintext);
hljs.registerLanguage("plaintext", plaintext);

const props = defineProps<{
  content: string
}>()

const escapeHtml = (s: string) =>
  s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");

const md = new MarkdownIt({
  html: true,
  linkify: true,
  typographer: true,
  // 统一把代码块包进 <pre class="hljs">：已注册语言的做彩色高亮，未知语言退化为纯转义，
  // 但同样带 hljs 深色底 —— 修复此前浅色主题下代码几乎不可见的问题。
  highlight(str, lang) {
    if (lang && hljs.getLanguage(lang)) {
      try {
        const out = hljs.highlight(str, { language: lang, ignoreIllegals: true }).value;
        return `<pre class="hljs"><code class="hljs language-${lang}">${out}</code></pre>`;
      } catch (__) {}
    }
    return `<pre class="hljs"><code class="hljs">${escapeHtml(str)}</code></pre>`;
  },
})

const renderedContent = computed(() => {
  return md.render(props.content)
})
</script>

<template>
  <div class="markdown-body" v-html="renderedContent"></div>
</template>

<style scoped>
.markdown-body {
  @apply prose prose-slate max-w-none;
}

.markdown-body :deep(h1) {
  @apply text-2xl font-bold mb-3 mt-2;
}

.markdown-body :deep(h2) {
  @apply text-xl font-bold mb-2 mt-3;
}

.markdown-body :deep(h3) {
  @apply text-lg font-bold mb-2 mt-3;
}

.markdown-body :deep(p) {
  @apply mb-3 leading-relaxed;
}

.markdown-body :deep(ul), .markdown-body :deep(ol) {
  @apply mb-3 pl-5;
}

.markdown-body :deep(ul) {
  @apply list-disc;
}

.markdown-body :deep(ol) {
  @apply list-decimal;
}

.markdown-body :deep(li) {
  @apply mb-1;
}

/* 行内代码：跟随主题底色，浅/深色下都清晰 */
.markdown-body :deep(:not(pre) > code) {
  @apply bg-base-200 px-1 py-0.5 rounded text-sm;
  color: inherit;
}

/* 代码块：固定 github 浅色底 + 深色基础文字，配合全局 github 主题的彩色 token，
   在应用浅色/深色主题下都清晰可见（修复此前浅色模式下代码几乎不可见的问题） */
.markdown-body :deep(pre) {
  @apply p-3 rounded mb-3 overflow-x-auto text-sm;
  background: #f6f8fa;
  color: #24292e;
  border: 1px solid #d0d7de;
}

.markdown-body :deep(pre code) {
  @apply p-0;
  background: transparent;
  color: inherit;
}

.markdown-body :deep(blockquote) {
  @apply pl-4 border-l-4 border-base-300 italic my-3 text-base-content/80;
}

.markdown-body :deep(a) {
  @apply text-primary underline hover:text-primary/80 transition-colors;
}

.markdown-body :deep(table) {
  @apply w-full mb-3 text-sm;
}

.markdown-body :deep(th), .markdown-body :deep(td) {
  @apply p-2 border border-base-300;
}

.markdown-body :deep(th) {
  @apply bg-base-200;
}

/* 确保代码块内的文本不会换行 */
.markdown-body :deep(pre code) {
  white-space: pre;
}

/* 代码块最大高度，超出时显示滚动条 */
.markdown-body :deep(pre) {
  max-height: 400px;
}
</style> 