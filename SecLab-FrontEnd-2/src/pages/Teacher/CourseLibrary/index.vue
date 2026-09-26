<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { createTeacherCourse, deleteTeacherCourse, getApiErrorMessage, getTeacherCourseList, updateTeacherCourse } from '../../../api'
import { getStoredCurrentUser } from '../../../auth'
import type { Course } from '../../../types/course'
import '../teacher-page.css'

const courses = ref<Course[]>([])
const loading = ref(true)
const error = ref('')
const search = ref('')
const category = ref('')
const showModal = ref(false)
const editing = ref<Course | null>(null)
const saving = ref(false)
const form = ref({ name: '', description: '', difficulty: 2 as 1 | 2 | 3 | 4 | 5, category: 'Web安全', tags: '', status: 'published' as Course['status'] })
const currentUserId = getStoredCurrentUser()?.userId || 0
const brokenCovers = ref<number[]>([])

const categories = computed(() => {
  const set = new Set(courses.value.map((item) => item.category).filter(Boolean))
  const defaultCats = ['Web安全', '网络安全', '高级威胁', '密码学', '系统安全', '二进制安全']
  defaultCats.forEach((c) => set.add(c))
  return Array.from(set)
})

const filtered = computed(() => courses.value.filter((item) => {
  const keyword = search.value.trim().toLowerCase()
  return (!keyword || `${item.name} ${item.description}`.toLowerCase().includes(keyword)) && (!category.value || item.category === category.value)
}))

const canEdit = (course: Course) => course.createdBy != null && course.createdBy === currentUserId

const PLACEHOLDER_COVER = '/default-course-image.png'
const CATEGORY_TINT: Record<string, string> = {
  'Web安全': 'linear-gradient(135deg, #1e293b 0%, #0f172a 100%)',
  '系统安全': 'linear-gradient(135deg, #1e1b4b 0%, #0f172a 100%)',
  '网络安全': 'linear-gradient(135deg, #064e3b 0%, #0f172a 100%)',
  '密码学': 'linear-gradient(135deg, #4c1d95 0%, #0f172a 100%)',
  '高级威胁': 'linear-gradient(135deg, #701a75 0%, #0f172a 100%)',
  '二进制安全': 'linear-gradient(135deg, #831843 0%, #0f172a 100%)',
}
const FALLBACK_TINT = 'linear-gradient(135deg, #1e293b 0%, #0f172a 100%)'

const STATUS_META: Record<Course['status'], { label: string; className: string }> = {
  published: { label: '已发布', className: 'published' },
  draft: { label: '草稿', className: 'draft' },
  archived: { label: '已归档', className: 'archived' }
}

const categoryCounts = computed(() => {
  const counts: Record<string, number> = {}
  courses.value.forEach((item) => {
    if (item.category) {
      counts[item.category] = (counts[item.category] || 0) + 1
    }
  })
  return counts
})

const stats = computed(() => ({
  total: courses.value.length,
  mine: courses.value.filter((item) => canEdit(item)).length,
  published: courses.value.filter((item) => item.status === 'published').length,
  categories: categories.value.length,
}))

const COVER_MAP: Record<string, string> = {
  'SQL注入攻击': '/cover-sql-169.jpg',
  'XSS与CSRF攻击': '/cover-xss-169.jpg',
  '文件上传漏洞': '/cover-file-upload-169.jpg',
  '文件上传': '/cover-file-upload-169.jpg',
  'IDS和IPS系统': '/cover-ids-ips.png',
  'APT攻击分析': '/cover-apt.png',
  '防火墙技术': '/cover-firewall.png',
  '经典密码学': '/cover-classic-crypto.png',
  'RSA公钥加密': '/cover-rsa.png',
  '数字签名与HASH': '/cover-signature.png',
  '操作系统安全': '/cover-os-security.png',
  '格式化字符串漏洞': '/cover-format-string.png',
  '堆溢出漏洞': '/cover-heap-overflow.png',
  '可信计算与TPM': '/cover-trusted-computing.png',
}

const tintOf = (course: Course) => CATEGORY_TINT[course.category] || FALLBACK_TINT
const coverOf = (course: Course) => {
  if (COVER_MAP[course.name]) return COVER_MAP[course.name]
  if (brokenCovers.value.includes(course.id)) return ''
  const cover = (course.cover || '').trim()
  if (!cover || cover.endsWith(PLACEHOLDER_COVER)) return ''
  return cover
}
const markCoverBroken = (course: Course) => {
  if (!brokenCovers.value.includes(course.id)) brokenCovers.value = [...brokenCovers.value, course.id]
}

const load = async () => {
  loading.value = true; error.value = ''
  try { courses.value = await getTeacherCourseList() }
  catch (err) { error.value = getApiErrorMessage(err, '课程库加载失败，请稍后重试。') }
  finally { loading.value = false }
}
const openCreate = () => { editing.value = null; form.value = { name: '', description: '', difficulty: 2, category: 'Web安全', tags: '', status: 'published' }; showModal.value = true }
const openEdit = (course: Course) => { if (!canEdit(course)) return; editing.value = course; form.value = { name: course.name, description: course.description, difficulty: course.difficulty, category: course.category, tags: (course.tags || []).join('，'), status: course.status }; showModal.value = true }
const save = async () => {
  if (!form.value.name.trim() || !form.value.description.trim()) return
  saving.value = true
  const payload = { ...form.value, name: form.value.name.trim(), description: form.value.description.trim(), tags: form.value.tags.split(/[，,]/).map((item) => item.trim()).filter(Boolean) }
  try { if (editing.value) await updateTeacherCourse(editing.value.id, payload); else await createTeacherCourse(payload); showModal.value = false; await load() }
  catch (err) { error.value = getApiErrorMessage(err, '课程保存失败，请检查后重试。') }
  finally { saving.value = false }
}
const remove = async (course: Course) => {
  if (!canEdit(course) || !window.confirm(`确定删除课程“${course.name}”吗？`)) return
  try { await deleteTeacherCourse(course.id); await load() }
  catch (err) { error.value = getApiErrorMessage(err, '课程删除失败，可能仍被教学班使用。') }
}
onMounted(() => void load())
</script>

<template>
  <div class="teacher-page course-library-page">
    <header class="page-head"><div><h1>课程库</h1><p>课程跨学期共享复用。每位教师只能维护自己创建的课程。</p></div><button class="primary-button" @click="openCreate">＋ 创建课程</button></header>

    <!-- 1. 全新升级的 4 大高级质感看板卡片 -->
    <section class="stat-grid">
      <div class="stat-card stat-blue">
        <div class="stat-icon">
          <svg viewBox="0 0 24 24" class="stat-svg"><path d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" fill="none"/></svg>
        </div>
        <div class="stat-info">
          <span class="stat-title">课程总数</span>
          <div class="stat-value">{{ stats.total }} <small>门</small></div>
          <span class="stat-desc">全平台共享课程资源</span>
        </div>
      </div>
      <div class="stat-card stat-indigo">
        <div class="stat-icon">
          <svg viewBox="0 0 24 24" class="stat-svg"><path d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" fill="none"/></svg>
        </div>
        <div class="stat-info">
          <span class="stat-title">我创建的</span>
          <div class="stat-value">{{ stats.mine }} <small>门</small></div>
          <span class="stat-desc">仅本人可维护修改</span>
        </div>
      </div>
      <div class="stat-card stat-emerald">
        <div class="stat-icon">
          <svg viewBox="0 0 24 24" class="stat-svg"><path d="M15.59 14.37a6 6 0 01-5.84 7.38v-4.8m5.84-2.58a14.98 14.98 0 006.16-12.12A14.98 14.98 0 009.631 8.41m5.96 5.96a14.926 14.926 0 01-5.841 2.58m-.119-8.54a6 6 0 00-7.381 5.84h4.8m2.581-5.84a14.927 14.927 0 00-2.58 5.84m2.699 2.7c-.103.021-.207.041-.311.06a15.09 15.09 0 01-2.448-2.448 14.9 14.9 0 01.06-.312m-2.24 3.76a6 6 0 00-5.84 5.84h4.8v-4.8z" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" fill="none"/></svg>
        </div>
        <div class="stat-info">
          <span class="stat-title">已发布</span>
          <div class="stat-value">{{ stats.published }} <small>门</small></div>
          <span class="stat-desc">可安排进教学班授课</span>
        </div>
      </div>
      <div class="stat-card stat-purple">
        <div class="stat-icon">
          <svg viewBox="0 0 24 24" class="stat-svg"><path d="M4 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2V6zM14 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2V6zM4 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2v-2zM14 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2v-2z" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" fill="none"/></svg>
        </div>
        <div class="stat-info">
          <span class="stat-title">覆盖方向</span>
          <div class="stat-value">{{ stats.categories }} <small>个</small></div>
          <span class="stat-desc">涵盖多个学科方向</span>
        </div>
      </div>
    </section>

    <!-- 2. 分类 Pills 标签与搜索面板（使用系统标准矢量图标） -->
    <div class="panel filter-panel-v2">
      <div class="category-pills">
        <button 
          class="pill-btn" 
          :class="{ active: category === '' }" 
          @click="category = ''"
        >
          <svg viewBox="0 0 24 24" class="cat-svg"><path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>
          <span>全部课程</span>
          <span class="pill-badge">{{ courses.length }}</span>
        </button>
        <button 
          v-for="cat in categories" 
          :key="cat" 
          class="pill-btn" 
          :class="{ active: category === cat }" 
          @click="category = cat"
        >
          <template v-if="cat === 'Web安全'">
            <svg viewBox="0 0 24 24" class="cat-svg"><circle cx="12" cy="12" r="10" fill="none" stroke="currentColor" stroke-width="2"/><path d="M2 12h20M12 2a15.3 15.3 0 014 10 15.3 15.3 0 01-4 10 15.3 15.3 0 01-4-10 15.3 15.3 0 014-10z" fill="none" stroke="currentColor" stroke-width="2"/></svg>
          </template>
          <template v-else-if="cat === '系统安全'">
            <svg viewBox="0 0 24 24" class="cat-svg"><rect x="2" y="3" width="20" height="14" rx="2" fill="none" stroke="currentColor" stroke-width="2"/><path d="M8 21h8M12 17v4" stroke="currentColor" stroke-width="2" stroke-linecap="round"/></svg>
          </template>
          <template v-else-if="cat === '网络安全' || cat === '网络攻防'">
            <svg viewBox="0 0 24 24" class="cat-svg"><rect x="9" y="2" width="6" height="6" rx="1" fill="none" stroke="currentColor" stroke-width="2"/><rect x="2" y="16" width="6" height="6" rx="1" fill="none" stroke="currentColor" stroke-width="2"/><rect x="16" y="16" width="6" height="6" rx="1" fill="none" stroke="currentColor" stroke-width="2"/><path d="M12 8v4M5 16v-4h14v4" stroke="currentColor" stroke-width="2" fill="none"/></svg>
          </template>
          <template v-else-if="cat === '密码学'">
            <svg viewBox="0 0 24 24" class="cat-svg"><circle cx="8" cy="15" r="4" fill="none" stroke="currentColor" stroke-width="2"/><path d="M11 12l8-8M16 7l2 2M13 10l2 2" stroke="currentColor" stroke-width="2" stroke-linecap="round"/></svg>
          </template>
          <template v-else-if="cat === '高级威胁'">
            <svg viewBox="0 0 24 24" class="cat-svg"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>
          </template>
          <template v-else-if="cat === '二进制安全'">
            <svg viewBox="0 0 24 24" class="cat-svg"><rect x="6" y="6" width="12" height="12" rx="2" fill="none" stroke="currentColor" stroke-width="2"/><path d="M9 2v4M15 2v4M9 18v4M15 18v4M2 9h4M2 15h4M18 9h4M18 15h4" stroke="currentColor" stroke-width="2" stroke-linecap="round"/></svg>
          </template>
          <template v-else>
            <svg viewBox="0 0 24 24" class="cat-svg"><path d="M4 6h16M4 12h16M4 18h16" stroke="currentColor" stroke-width="2" stroke-linecap="round"/></svg>
          </template>

          <span>{{ cat }}</span>
          <span class="pill-badge">{{ categoryCounts[cat] || 0 }}</span>
        </button>
      </div>

      <div class="filter-search-wrap">
        <div class="search-input-box">
          <svg viewBox="0 0 24 24" class="search-icon"><path d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" stroke="currentColor" stroke-width="2" fill="none"/></svg>
          <input v-model="search" class="filter-search-input" placeholder="搜索课程名称或说明内容…" />
          <button v-if="search" @click="search = ''" class="clear-search-btn" title="清空搜索">✕</button>
        </div>
        <span class="count-label">共 <strong>{{ filtered.length }}</strong> 门课程</span>
      </div>
    </div>

    <div v-if="error" class="notice error" style="margin: 16px 0">{{ error }}</div>
    <div v-if="loading" class="panel loading-state" style="margin-top: 16px">正在加载课程库…</div>
    <div v-else-if="!filtered.length" class="panel empty-state" style="margin-top: 16px"><strong>没有符合条件的课程</strong>可以创建一门新课程，供所有教师安排到教学班。</div>
    <div v-else class="course-grid">
      <article v-for="course in filtered" :key="course.id" class="panel course-card">
        <div class="course-accent"></div>
        <div class="course-cover" :style="{ background: tintOf(course) }">
          <img v-if="coverOf(course)" :src="coverOf(course)" :alt="`${course.name} 封面`" class="cover-img-fill" @error="markCoverBroken(course)" />
          <svg v-else viewBox="0 0 24 24" aria-hidden="true"><path d="M4 5.5A2.5 2.5 0 0 1 6.5 3H20v16H6.5a2.5 2.5 0 1 1 0-5H20M7 7h9"/></svg>
          <span class="status-chip" :class="STATUS_META[course.status].className">{{ STATUS_META[course.status].label }}</span>
        </div>
        <div class="course-body">
          <div class="course-card-head"><span class="tag">{{ course.category || '未分类' }}</span><span class="owner-label" :class="{ mine: canEdit(course) }">{{ canEdit(course) ? '我创建' : '共享课程' }}</span></div>
          <h2>{{ course.name }}</h2><p>{{ course.description || '暂无课程说明' }}</p>
          <div v-if="course.tags?.length" class="course-tags"><span v-for="tag in (course.tags || []).slice(0, 3)" :key="tag" class="tag gray">{{ tag }}</span></div>
          <div class="course-meta"><span>难度 {{ course.difficulty }}/5</span></div>
          <div class="course-actions" v-if="canEdit(course)"><button class="secondary-button" @click="openEdit(course)">编辑</button><button class="danger-button" @click="remove(course)">删除</button></div>
          <div v-else class="shared-note">可用于教学班安排，不可修改</div>
        </div>
      </article>
    </div>

    <div v-if="showModal" class="modal-layer" @click.self="showModal = false"><div class="modal-card"><div class="modal-head"><h2>{{ editing ? '编辑课程' : '创建课程' }}</h2><button @click="showModal = false">×</button></div>
      <form @submit.prevent="save"><div class="modal-body"><div class="field"><label>课程名称</label><input v-model="form.name" required maxlength="120" placeholder="例如：SQL 注入基础" /></div><div class="field"><label>课程说明</label><textarea v-model="form.description" required rows="4" placeholder="说明本课程讲什么、适合什么阶段"></textarea></div><div class="form-grid"><div class="field"><label>分类</label><input v-model="form.category" required placeholder="Web安全" /></div><div class="field"><label>难度</label><select v-model="form.difficulty"><option v-for="level in 5" :key="level" :value="level">{{ level }} 级</option></select></div></div><div class="field"><label>标签（逗号分隔）</label><input v-model="form.tags" placeholder="SQL注入, Web安全" /></div><div class="field"><label>状态</label><select v-model="form.status"><option value="published">已发布</option><option value="draft">草稿</option><option value="archived">已归档</option></select></div></div><div class="modal-actions"><button type="button" class="secondary-button" @click="showModal = false">取消</button><button class="primary-button" :disabled="saving">{{ saving ? '保存中…' : '保存课程' }}</button></div></form>
    </div></div>
  </div>
</template>

<style scoped>
/* 1. 顶部统计看板 */
.stat-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
  margin-bottom: 20px;
}

.stat-card {
  position: relative;
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 18px 20px;
  background: oklch(var(--b1));
  border-radius: 16px;
  border: 1px solid oklch(var(--bc) / 0.1);
  box-shadow: 0 4px 20px -4px rgba(0, 0, 0, 0.04);
  transition: all 0.3s cubic-bezier(0.16, 1, 0.3, 1);
  overflow: hidden;
}

.stat-card:hover {
  transform: translateY(-3px);
  box-shadow: 0 12px 28px -6px rgba(0, 0, 0, 0.08);
  border-color: oklch(var(--p) / 0.3);
}

.stat-icon {
  width: 48px;
  height: 48px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 22px;
  flex-shrink: 0;
  background: oklch(var(--b2));
}

.stat-svg {
  width: 22px;
  height: 22px;
}
.stat-blue .stat-svg { stroke: oklch(var(--p)); color: oklch(var(--p)); }
.stat-indigo .stat-svg { stroke: oklch(var(--in)); color: oklch(var(--in)); }
.stat-emerald .stat-svg { stroke: oklch(var(--su)); color: oklch(var(--su)); }
.stat-purple .stat-svg { stroke: oklch(var(--a)); color: oklch(var(--a)); }

.stat-blue .stat-icon { background: oklch(var(--p) / 0.12); }
.stat-indigo .stat-icon { background: oklch(var(--in) / 0.12); }
.stat-emerald .stat-icon { background: oklch(var(--su) / 0.12); }
.stat-purple .stat-icon { background: oklch(var(--a) / 0.12); }

.stat-info { display: flex; flex-direction: column; gap: 2px; }
.stat-title { font-size: 12px; font-weight: 600; color: oklch(var(--bc) / 0.6); }
.stat-value { font-size: 24px; font-weight: 800; color: oklch(var(--bc)); font-family: var(--font-display, sans-serif); line-height: 1.2; }
.stat-value small { font-size: 13px; font-weight: 500; color: oklch(var(--bc) / 0.5); }
.stat-desc { font-size: 11px; color: oklch(var(--bc) / 0.45); }

/* 2. 分类 Pills 标签与搜索框控制面板 */
.filter-panel-v2 {
  display: flex;
  flex-direction: column;
  gap: 16px;
  padding: 18px 20px;
  background: oklch(var(--b1));
  border-radius: 16px;
  border: 1px solid oklch(var(--bc) / 0.1);
  box-shadow: 0 4px 20px -4px rgba(0, 0, 0, 0.04);
  transition: border-color 0.3s ease;
}

.category-pills {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  align-items: center;
}

.pill-btn {
  position: relative;
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 6px 16px 6px 10px;
  border-radius: 999px;
  font-size: 13px;
  font-weight: 600;
  border: 1px solid oklch(var(--bc) / 0.12);
  background: oklch(var(--b2) / 0.4);
  color: oklch(var(--bc) / 0.75);
  cursor: pointer;
  transition: all 0.3s cubic-bezier(0.16, 1, 0.3, 1);
  user-select: none;
}

.cat-svg {
  width: 15px;
  height: 15px;
  flex-shrink: 0;
  transition: transform 0.3s ease;
}

.pill-btn:hover .cat-svg {
  transform: scale(1.2) rotate(6deg);
}

.pill-btn.active .cat-svg {
  transform: scale(1.1);
}

.pill-icon {
  font-size: 14px;
  transition: transform 0.3s ease;
}

.pill-btn:hover {
  transform: translateY(-2px);
  background: oklch(var(--p) / 0.12);
  color: oklch(var(--p));
  border-color: oklch(var(--p) / 0.35);
  box-shadow: 0 4px 12px -2px oklch(var(--p) / 0.15);
}

.pill-btn:hover .pill-icon {
  transform: scale(1.2) rotate(6deg);
}

.pill-btn:active {
  transform: scale(0.96);
}

.pill-btn.active {
  background: linear-gradient(135deg, oklch(var(--p)) 0%, oklch(var(--in)) 100%);
  color: #ffffff;
  border-color: transparent;
  box-shadow: 0 6px 18px -2px oklch(var(--p) / 0.45);
  transform: translateY(-2px) scale(1.02);
}

.pill-btn.active .pill-icon {
  transform: scale(1.15);
}

.pill-badge {
  font-size: 11px;
  font-weight: 700;
  padding: 2px 8px;
  border-radius: 999px;
  background: oklch(var(--bc) / 0.08);
  color: oklch(var(--bc) / 0.6);
  transition: all 0.3s ease;
}

.pill-btn:hover .pill-badge {
  background: oklch(var(--p) / 0.2);
  color: oklch(var(--p));
}

.pill-btn.active .pill-badge {
  background: rgba(255, 255, 255, 0.25);
  color: #ffffff;
}

/* 搜索框与动效 */
.filter-search-wrap {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding-top: 14px;
  border-top: 1px solid oklch(var(--bc) / 0.08);
}

.search-input-box {
  position: relative;
  flex: 1;
  max-width: 440px;
}

.search-icon {
  position: absolute;
  left: 14px;
  top: 50%;
  transform: translateY(-50%);
  width: 16px;
  height: 16px;
  color: oklch(var(--bc) / 0.4);
  transition: color 0.2s ease;
}

.search-input-box:focus-within .search-icon {
  color: oklch(var(--p));
}

.filter-search-input {
  width: 100%;
  padding: 9px 36px 9px 38px;
  border-radius: 12px;
  border: 1px solid oklch(var(--bc) / 0.12);
  background: oklch(var(--b2) / 0.35);
  font-size: 13px;
  color: oklch(var(--bc));
  transition: all 0.25s cubic-bezier(0.16, 1, 0.3, 1);
}

.filter-search-input:focus {
  outline: none;
  border-color: oklch(var(--p));
  background: oklch(var(--b1));
  box-shadow: 0 0 0 3px oklch(var(--p) / 0.18), 0 4px 12px -2px oklch(var(--p) / 0.1);
}

.clear-search-btn {
  position: absolute;
  right: 12px;
  top: 50%;
  transform: translateY(-50%);
  width: 18px;
  height: 18px;
  border-radius: 50%;
  background: oklch(var(--bc) / 0.15);
  color: oklch(var(--bc) / 0.7);
  border: none;
  font-size: 12px;
  line-height: 1;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s ease;
}

.clear-search-btn:hover {
  background: oklch(var(--er));
  color: #fff;
}

/* 3. 卡片与封面 */
.course-grid { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 16px; margin-top: 16px; animation: fadeInUp 0.4s ease-out; }

@keyframes fadeInUp {
  from {
    opacity: 0;
    transform: translateY(10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.course-card { position: relative; overflow: hidden; padding: 0; border-radius: 14px; border: 1px solid oklch(var(--bc) / 0.1); background: oklch(var(--b1)); transition: all 0.25s ease; }.course-card:hover { transform: translateY(-3px); box-shadow: 0 12px 24px -4px rgba(0, 0, 0, 0.08); }.course-accent { position: absolute; inset: 0 auto 0 0; z-index: 2; width: 3px; background: oklch(var(--p)); }
.course-cover { position: relative; display: block; height: 160px; overflow: hidden; border-bottom: 1px solid oklch(var(--bc) / .08); background: oklch(var(--b2)); }
.cover-img-fill { display: block; width: 100%; height: 100%; object-fit: cover; object-position: center; transition: transform 0.4s ease; }
.course-card:hover .cover-img-fill { transform: scale(1.05); }
.status-chip { position: absolute; right: 10px; top: 10px; z-index: 2; padding: 3px 8px; border-radius: 999px; font-size: 10px; font-weight: 700; letter-spacing: .02em; }.status-chip.published { background: oklch(var(--su) / .92); color: oklch(var(--suc)); }.status-chip.draft { background: oklch(var(--wa) / .92); color: oklch(var(--wac)); }.status-chip.archived { background: oklch(var(--n) / .82); color: oklch(var(--nc)); }
.course-body { padding: 18px 20px 20px; }.course-card-head { display: flex; align-items: center; justify-content: space-between; }.owner-label { color: oklch(var(--bc) / .55); font-size: 10px; }.owner-label.mine { color: oklch(var(--p)); }.course-card h2 { margin: 14px 0 8px; font-size: 17px; }.course-body > p { height: 61px; margin: 0; overflow: hidden; color: oklch(var(--bc) / .65); font-size: 12px; line-height: 1.7; }
.course-tags { display: flex; flex-wrap: wrap; gap: 6px; margin-top: 12px; }
.course-meta { display: flex; gap: 18px; margin-top: 14px; padding-top: 13px; border-top: 1px solid oklch(var(--bc) / .1); color: oklch(var(--bc) / .6); font-size: 11px; }.course-actions { display: flex; gap: 8px; margin-top: 15px; }.course-actions button { min-height: 32px; }.shared-note { margin-top: 15px; color: oklch(var(--bc) / .55); font-size: 11px; }.form-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 14px; }
@media (max-width: 1240px) { .stat-grid { grid-template-columns: repeat(2, 1fr); } }
@media (max-width: 1100px) { .course-grid { grid-template-columns: repeat(2, 1fr); } } @media (max-width: 660px) { .filter-panel-v2, .course-grid, .form-grid, .stat-grid { grid-template-columns: 1fr; } }
</style>
