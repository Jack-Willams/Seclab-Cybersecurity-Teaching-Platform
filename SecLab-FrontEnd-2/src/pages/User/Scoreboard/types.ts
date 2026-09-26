export interface UserScore {
  id: number
  username: string
  studentNumber?: string
  avatar?: string
  totalScore: number
  completedTasks: number
  class?: string
  rank: number
  recentActivity?: {
    date: string
    experimentName: string
    score: number
  }
}

export type TimeRange = 'week' | 'month' | 'all'

export interface ScoreboardFilters {
  timeRange: TimeRange
  experimentType?: string
  className?: string
} 
