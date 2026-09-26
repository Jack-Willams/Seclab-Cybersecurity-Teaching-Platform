export interface ModuleOverViewType {
  id: number;
  name: string;
  description: string;
  difficulty: number;
  type: string;
  status: 'available' | 'locked' | 'completed';
  estimatedTime: string;
  score: number;
  courseId?: number | null;
  courseIds?: number[];
  prerequisites?: number[];
  image?: string;
}