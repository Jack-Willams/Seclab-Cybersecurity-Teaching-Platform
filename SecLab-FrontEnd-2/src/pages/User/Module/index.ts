import type { DisplayQuestionType } from '../../../types/Question';

export interface TaskPoint {
  id: number;
  name: string;
  description: string;
  score: number;
  document: string;
  questions: DisplayQuestionType[];
}

export interface Module {
  id: number;
  name: string;
  introduction: string;
  difficulty: number;
  taskPoints: TaskPoint[];
  targetMachine?: {
    id: string;
  };
}

// 添加类型转换辅助函数，将ExperimentType转换为Module
export function convertExperimentToModule(experiment: any): Module {
  // 确保taskPoints中的questions属性符合DisplayQuestionType[]类型
  const taskPoints = experiment.taskPoints.map((task: any) => {
    return {
      ...task,
      questions: task.questions || [] // 确保questions是数组
    };
  });

  return {
    ...experiment,
    taskPoints
  };
}