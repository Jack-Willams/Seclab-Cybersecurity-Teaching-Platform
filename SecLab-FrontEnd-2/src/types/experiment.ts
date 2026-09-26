export interface Experiment {
  id: number
  name: string
  description: string
  difficulty: 1 | 2 | 3 | 4 | 5
  courseId?: number
  courseIds?: number[]
  courseName?: string
  status: 'draft' | 'published' | 'archived'
  taskPoints: Array<{
    id: number
    name: string
    score: number
    description: string
  }>
  environment: {
    targetMachine?: {
      image: string
      port: number
      memory: string
    }
    operationMachine?: {
      image: string
      port: number
      memory: string
    }
  }
  studentCount: number
  completionRate: number
  averageScore: number
  createTime: string
  updateTime?: string
}
