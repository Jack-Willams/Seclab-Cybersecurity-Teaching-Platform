export interface CourseOverViewType {
  id: number;
  name: string;
  image: string;
  description: string;
  status: 'in-progress' | 'completed' | 'available';
  category: string;
  difficulty: 1 | 2 | 3 | 4 | 5;
  estimatedHours: number;
  tags: string[];
  totalStudents?: number;
  videoUrl?: string;
}