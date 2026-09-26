export interface Course {
  id: number
  name: string
  description: string
  cover?: string
  difficulty: 1 | 2 | 3 | 4 | 5
  category: string
  // 后端一直返回 tags，只是之前没映射进来：教师端卡片显示不了标签，
  // 编辑课程时也会把原有标签清空（表单初始值写死成空串）
  tags?: string[]
  status: 'draft' | 'published' | 'archived'
  studentCount: number
  experimentCount: number
  createTime: string
  updateTime?: string
  createdBy?: number | null
  creatorEditable?: boolean
}
 