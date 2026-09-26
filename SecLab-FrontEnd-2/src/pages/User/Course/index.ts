

export enum CourseStatus {
    ACTIVE = 'active',
    UPCOMING = 'upcoming',
    COMPLETED = 'completed'
  }



export interface ModuleOverView {
    moduleId: number | null;
    moduleName: string | null;
    introduction: string | null;
    type: string[] | null;
    difficulty: number | null;
  }
  
  /**
   * 课程接口定义
   */
  export interface Course {
    id: number | null;
    name: string;
    description: string | null;
    difficulty: number | null;     // 难度,1-5
    type: string | null;
    tags: string[] | null;
    imageUrl: string | null;
    costTime: number | null;
    schedule: string | null;
    status: CourseStatus | null;
    instructor: number | string | null;     // 使用number或string类型
    modules: ModuleOverView[];
  }