// 类型定义文件，为JavaScript模块提供类型

export interface ExperimentType {
  id: number;
  name: string;
  introduction: string;
  difficulty: number;
  taskPoints: Array<{
    id: number;
    name: string;
    description: string;
    score: number;
    document: string;
    questions?: any[];
  }>;
  targetMachine?: {
    id: string;
  };
}

// 声明模块导出
export const SQLInjectionExperiment: ExperimentType;
export const XSSExperiment: ExperimentType;
export const CSRFExperiment: ExperimentType;
export const CommandInjectionExperiment: ExperimentType;
export const FileUploadExperiment: ExperimentType;

export const AllExperiments: ExperimentType[];

// 辅助函数
export function findExperimentById(id: number): ExperimentType | undefined;
export const ExperimentTypes: {
  SQL_INJECTION: 1;
  XSS: 2;
  CSRF: 3;
  COMMAND_INJECTION: 4;
  FILE_UPLOAD: 5;
};

export function getExperimentsByDifficulty(difficulty: number): ExperimentType[];
export function getBeginnerExperiments(): ExperimentType[];
export function getAdvancedExperiments(): ExperimentType[]; 