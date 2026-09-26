import axios from "axios";
import type { RegisterForm } from "./types/auth";
import { getStoredToken } from "./auth";
import type { User } from "./types/user";
import type { Course as AdminCourse } from "./types/course";
import type { Experiment as AdminExperiment } from "./types/experiment";
import type { ModuleOverViewType } from "./pages/User/Modules/components/ModuleOverView";
import type { Course } from "./pages/User/Course/index.ts";
import { CourseStatus } from "./pages/User/Course/index.ts";
import type { Module } from "./pages/User/Module/index.ts";
import { findExperimentById } from './data';

// 可配置的API基础URL
// 优先使用环境变量，如果没有则使用默认值
const API_BASE_URL =
    import.meta.env.VITE_API_BASE_URL ||
    (import.meta.env.DEV ? "http://localhost:8083" : "/user-service");
const EXPERIMENT_MODULE_BASE_URL = import.meta.env.VITE_EXPERIMENT_MODULE_BASE_URL || "http://localhost:8084";
const IMAGE_SERVICE_BASE_URL = import.meta.env.VITE_IMAGE_SERVICE_BASE_URL || "http://localhost:8086/api/images";
// Docker API服务器的URL
const DOCKER_API_URL = import.meta.env.VITE_DOCKER_API_URL || "http://localhost:3000";
// AI Agent / learning-event API server
const AGENT_BASE_URL = import.meta.env.VITE_AGENT_BASE_URL || "http://localhost:8010";

const BASE_URL: string = API_BASE_URL;
const IMAGE_URL = `${BASE_URL}/images/view/`;

type Result<T> = {
    isSuccess?:number,
    status:number,
    message:string,
    data:T
}

const getBackendErrorResponse = <T>(error: unknown): Result<T> | null => {
    if (axios.isAxiosError(error) && error.response?.data) {
        return error.response.data as Result<T>;
    }
    return null;
};

export function getApiErrorMessage(error: unknown, fallback: string): string {
    if (!axios.isAxiosError(error)) {
        return fallback;
    }

    if (!error.response) {
        if (error.code === "ECONNABORTED" || /timeout/i.test(error.message || "")) {
            return "请求超时，请稍后重试。";
        }
        return "当前服务暂不可用，请稍后重试。";
    }

    const status = error.response.status;
    const responseData = error.response.data as { detail?: unknown } | undefined;
    const responseDetail = typeof responseData?.detail === "string"
        ? responseData.detail.trim()
        : "";
    if (status === 401) {
        return "登录状态已失效，请重新登录。";
    }
    if (status === 403) {
        return "当前账号无权查看该数据。";
    }
    if (status === 404) {
        return "请求的数据已不存在或无权访问。";
    }
    if (status === 400 || status === 422) {
        return "请求内容有误，请检查后重试。";
    }
    if (status === 408 || status === 504) {
        return "请求超时，请稍后重试。";
    }
    if (status === 429) {
        return "请求过于频繁，请稍后重试。";
    }
    if (status >= 500) {
        if (responseDetail) {
            return responseDetail;
        }
        return "数据加载失败，请重新加载。";
    }
    return fallback;
}

export interface QuestionSubmitRequest {
    user_id?: number | null;
    class_id?: number | null;
    course_id?: number | null;
    module_id?: number | null;
    task_id?: number | null;
    question_id: number | string;
    question_uid?: string;
    question_type: string;
    answer: unknown;
    cost_time?: number | null;
    request_id?: string;
    lab_session_id?: string | null;
    question_score?: number;
    standard_answer?: unknown;
    question_snapshot?: Record<string, unknown>;
    training_session_id?: string | null;
    question_source?: "course_question" | "personalized_training";
    knowledge_point_id?: number | null;
}

export interface QuestionSubmitResponse {
    submission_id: string;
    is_correct: boolean | null;
    score: number;
    correct_answer: unknown;
    message: string;
}

export interface LabSessionStartRequest {
    user_id?: number | null;
    class_id?: number | null;
    course_id?: number | null;
    module_id?: number | null;
    task_id?: number | null;
    container_name?: string | null;
    container_id?: string | null;
    target_url?: string | null;
    request_id?: string;
}

export interface LabSessionStartResponse {
    session_id: string;
    status: string;
    start_time: string;
}

export interface LabSessionStopResponse {
    session_id: string;
    status: string;
    end_time: string;
}

export interface FlagSubmitRequest {
    user_id?: number | null;
    class_id?: number | null;
    course_id?: number | null;
    module_id?: number | null;
    task_id?: number | null;
    lab_session_id?: string | null;
    container_name?: string | null;
    flag_text: string;
    request_id?: string;
    score?: number;
}

export interface FlagSubmitResponse {
    submission_id: string;
    is_correct: boolean;
    score: number;
    completed: boolean;
    completion_id?: number | null;
    message: string;
}

export interface EventsIngestPayload {
    batch_id: string;
    source_system: string;
    generated_at: string;
    user_context: {
        user_id: number | null;
        class_id: number | null;
        course_id: number | null;
        module_id: number | null;
        task_id: number | null;
        question_id: number | null;
        lab_session_id: string;
    };
    events: Array<{
        event_id: string;
        request_id?: string;
        event_type: string;
        event_time: string;
        user_id?: number | null;
        class_id?: number | null;
        course_id?: number | null;
        module_id?: number | null;
        task_id?: number | null;
        question_id?: number | null;
        lab_session_id?: string;
        source?: string;
        question_type?: string | null;
        answer?: string | string[] | null;
        standard_answer?: string | null;
        question_score?: number | null;
        cost_time?: number | null;
        is_correct?: boolean | null;
        container_name?: string | null;
        flag_text?: string | null;
        score?: number | null;
        command_id?: string | null;
        command?: string | null;
        cwd?: string | null;
        exit_code?: number | null;
        duration_ms?: number | null;
        output_digest?: string | null;
        file_path?: string | null;
        file_ext?: string | null;
        action?: string | null;
        size_before?: number | null;
        size_after?: number | null;
        is_key_file?: boolean | null;
        error_signature?: string | null;
        error_category?: string | null;
        raw_excerpt?: string | null;
        severity?: string | null;
        extra?: Record<string, any>;
    }>;
    ai_generated_questions?: Array<unknown>;
    profile_rebuild?: {
        user_id: number | null;
        class_id: number | null;
        rebuild_after_ingest: boolean;
    };
}

export interface LearningEventPayload {
    event_id?: string;
    request_id?: string;
    event_type: string;
    event_time?: string;
    user_id?: number | null;
    class_id?: number | null;
    course_id?: number | null;
    module_id?: number | null;
    task_id?: number | null;
    question_id?: number | null;
    lab_session_id?: string | null;
    source?: string | null;
    question_type?: string | null;
    answer?: unknown;
    standard_answer?: unknown;
    question_score?: number | null;
    cost_time?: number | null;
    is_correct?: boolean | null;
    session_id?: string | null;
    target_url?: string | null;
    container_id?: string | null;
    container_name?: string | null;
    flag_text?: string | null;
    score?: number | null;
    prompt?: string | null;
    assistant_reply?: string | null;
    message_role?: string | null;
    context?: Record<string, unknown> | null;
    tool_calls?: Array<Record<string, unknown>> | null;
    used_context_injection?: boolean | null;
}

export interface ProfileDashboardSkill {
    name: string;
    score: number;
    color: string;
}

export interface ProfileDashboardTag {
    text: string;
    type: string;
}

export interface ProfileDashboardSolveRecord {
    id: string;
    sourceType: string;
    questionId: string;
    trainingSessionId?: string;
    title: string;
    experiment: string;
    stem: string;
    questionType: string;
    module: string;
    time: string;
    result: string;
    isCorrect: boolean | null;
    score: number;
    costTime: number | null;
    studentAnswer: unknown;
    standardAnswer: unknown;
    options: string[];
    explanation: string;
    contentAvailable: boolean;
}

export interface ProfileDashboardResponse {
    userStats: {
        completedCourses: number;
        totalScore: number;
        ranking: number;
        activeStreak: number;
    };
    learningProfile: {
        skills: ProfileDashboardSkill[];
        tags: ProfileDashboardTag[];
        recentFocus: string;
        comprehensiveScore: number;
        evaluation: string;
    };
    solveRecords: ProfileDashboardSolveRecord[];
}

export interface ProfileLatestResponse {
    snapshot_id?: string;
    user_id?: number;
    class_id?: number | null;
    course_id?: number | null;
    computed_at?: string;
    knowledge_mastery_score?: number;
    troubleshooting_score?: number;
    autonomy_score?: number;
    ai_collaboration_score?: number;
    engagement_score?: number;
    overall_score?: number;
    profile_summary_json?: Record<string, unknown>;
    source_range_start?: string | null;
    source_range_end?: string | null;
    created_at?: string;
    profile?: null;
    message?: string;
}

export interface ProfileRecommendationItem {
    id: string;
    dimension: string;
    dimension_name?: string;
    score: number;
    type: "COURSE" | "MODULE" | "LAB" | "QUESTION" | "GENERAL";
    title: string;
    reason: string;
    courseId: number | null;
    moduleId: number | null;
    labId: number | null;
    questionId: number | null;
    difficulty: number | null;
    actionText: string;
    source: string;
    knowledgeTags?: string[];
    threshold?: number;
    priority?: string;
    action?: string;
    tags?: string[];
}

export interface WeakKnowledgePoint {
    knowledge_point_id: number | null;
    name: string;
    category?: string | null;
    description?: string | null;
    difficulty_level?: string | null;
    module_id?: number | null;
    task_id?: number | null;
    confidence?: number;
    evidence_level?: string;
    reason: string;
}

export interface TrainingDiagnoseRequest {
    user_id: number;
    class_id?: number | null;
    course_id?: number | null;
    top_k?: number;
    question_count?: number;
}

export interface TrainingDiagnoseResponse {
    profile_snapshot_id?: string | null;
    user_id?: number;
    class_id?: number | null;
    course_id?: number | null;
    dimension_scores: {
        knowledge_mastery_score?: number;
        troubleshooting_score?: number;
        autonomy_score?: number;
        ai_collaboration_score?: number;
        engagement_score?: number;
        overall_score?: number;
    };
    weak_dimensions: string[];
    tags: string[];
    recent_focus?: string;
    weak_knowledge_points: WeakKnowledgePoint[];
    generation_constraints: {
        difficulty: string;
        question_types: string[];
        question_count: number;
    };
    recent_evidence: {
        recent_errors: string[];
        recent_failed_tasks: number[];
        recent_ai_topics: string[];
    };
}

export interface GeneratedTrainingQuestion {
    generated_question_id: string;
    question_id: string;
    question_numeric_id?: number;
    training_session_id: string;
    question_type: "single_choice" | "fill_blank" | "short_answer" | string;
    knowledge_point_id?: number | null;
    module_id?: number | null;
    task_id?: number | null;
    difficulty?: string | null;
    title: string;
    stem: string;
    options: string[];
    standard_answer?: string | null;
    reference_answer?: string | null;
    explanation?: string | null;
    scoring_rubric: string[];
    source_model?: string | null;
    created_at?: string;
    raw_ai?: Record<string, unknown>;
}

export interface TrainingGenerationRequest {
    user_id: number;
    class_id?: number | null;
    course_id?: number | null;
    profile_snapshot_id?: string | null;
    dimension_scores?: TrainingDiagnoseResponse["dimension_scores"];
    weak_dimensions: string[];
    weak_knowledge_points: WeakKnowledgePoint[];
    recent_focus?: string;
    tags?: string[];
    recent_evidence?: TrainingDiagnoseResponse["recent_evidence"];
    question_types: Array<"single_choice" | "fill_blank" | "short_answer">;
    difficulty: string;
    question_count: number;
    course_context?: Array<{
        module_id?: number | null;
        module_name?: string | null;
        knowledge_snippets?: Array<string | null | undefined>;
    }>;
}

export interface TrainingGenerationResponse {
    training_session_id: string;
    profile_snapshot_id?: string | null;
    source_model?: string | null;
    generation_status?: string;
    generation_error?: string | null;
    training_context?: Record<string, unknown>;
    questions: GeneratedTrainingQuestion[];
}

export interface TrainingSingleQuestionRequest {
    userId: number;
    dimension: string;
    recommendationId?: string;
    moduleId?: number | null;
    courseId?: number | null;
    knowledgeTags?: string[];
    difficulty: number;
    questionType: "SHORT_ANSWER";
    count: 1;
    source: "student_profile_snapshot";
}

export interface TrainingQuestionSetRequest {
    userId: number;
    dimension: string;
    recommendationId?: string;
    moduleId?: number | null;
    courseId?: number | null;
    knowledgeTags?: string[];
    difficulty: number;
    questionType: "SHORT_ANSWER";
    count?: number;
    source: "student_profile_snapshot" | "teacher_assignment";
}

export interface TrainingQuestionGradingRubricItem {
    point: string;
    score: number;
}

export interface TrainingSingleQuestion {
    title: string;
    stem: string;
    questionType: "SHORT_ANSWER" | "MCQ" | "CASE" | string;
    difficulty: number;
    dimension: string;
    knowledgeTags: string[];
    standardAnswer: string;
    explanation: string;
    sourceKnowledgeUnitIds: string[];
    validationHints: Record<string, unknown>;
    options?: string[] | null;
    correctOption?: string | null;
    teachingObjective?: string;
    expectedSkill?: string;
    difficultyReason?: string;
    commonMistakes?: string[];
    gradingRubric?: TrainingQuestionGradingRubricItem[];
    qualityScore?: number;
    qualitySummary?: string;
    qualityFlags?: string[];
}

export interface TrainingSingleQuestionResponse {
    success: boolean;
    generatedQuestionId: string;
    question: TrainingSingleQuestion;
    metadata: {
        userId: number;
        moduleId?: number | null;
        recommendationId?: string | null;
        generator: string;
        knowledgeUnitCount: number;
        trainingSessionId: string;
        sourceSnapshotId?: string | null;
    };
}

export interface TrainingQuestionSetItem {
    generatedQuestionId: string;
    title: string;
    stem: string;
    questionType: "SHORT_ANSWER" | string;
    difficulty?: number | null;
    knowledgeTags: string[];
}

export interface TrainingQuestionSetResponse {
    success: boolean;
    trainingSessionId: string;
    count: number;
    targetCount: number;
    actualCount: number;
    partial: boolean;
    questions: TrainingQuestionSetItem[];
    metadata: {
        generator: string;
        mode: "question_set_batch" | string;
        targetCount: number;
        actualCount: number;
        partial: boolean;
    };
}

export interface GeneratedQuestionAnswerSubmitRequest {
    userId: number;
    answer: string;
    source?: string;
}

export interface GeneratedQuestionFeedbackItem {
    point: string;
    score: number;
    matched: boolean;
}

export interface GeneratedQuestionAnswerSubmitResponse {
    success: boolean;
    generatedQuestionId: string;
    trainingSessionId?: string;
    attemptId: string;
    correctnessScore: number;
    level: "EXCELLENT" | "GOOD" | "PARTIAL" | "NEEDS_REVIEW" | string;
    feedback: string;
    hitRubricItems: GeneratedQuestionFeedbackItem[];
    missedRubricItems: GeneratedQuestionFeedbackItem[];
    keywordHits: string[];
    keywordMisses: string[];
    suggestion: string;
    submittedAt: string;
    learningEventId?: string;
    profileRebuildTriggered?: boolean;
    latestSnapshotId?: string | null;
}

export interface TrainingSessionSummaryQuestion {
    generatedQuestionId: string;
    title: string;
    stem: string;
    submitted: boolean;
    studentAnswer?: string;
    correctnessScore?: number | null;
    level?: string | null;
    feedback?: string | null;
    hitRubricItems: GeneratedQuestionFeedbackItem[];
    missedRubricItems: GeneratedQuestionFeedbackItem[];
    keywordHits: string[];
    keywordMisses: string[];
    suggestion?: string | null;
    standardAnswer?: string | null;
    explanation?: string | null;
    teachingObjective?: string | null;
    expectedSkill?: string | null;
    difficultyReason?: string | null;
    commonMistakes?: string[];
    gradingRubric?: TrainingQuestionGradingRubricItem[];
}

export interface TrainingSessionSummaryResponse {
    success: boolean;
    trainingSessionId: string;
    userId: number;
    totalQuestions: number;
    submittedCount: number;
    completed: boolean;
    averageScore: number;
    level: string;
    dimension?: string | null;
    knowledgeTags: string[];
    summaryFeedback?: string;
    questions: TrainingSessionSummaryQuestion[];
    nextActions?: string[];
}

export interface TrainingSubmitRequest {
    user_id: number;
    class_id?: number | null;
    course_id?: number | null;
    module_id?: number | null;
    task_id?: number | null;
    training_session_id: string;
    question_id: string;
    question_uid?: string;
    question_type: "single_choice" | "fill_blank" | "short_answer" | string;
    answer: unknown;
    knowledge_point_id?: number | null;
    question_score?: number;
    cost_time?: number | null;
    request_id: string;
    auto_rebuild?: boolean;
}

export interface TrainingSubmitResponse {
    submission_id: string;
    question_id: string;
    question_numeric_id?: number;
    question_source?: "course_question" | "personalized_training" | string;
    training_session_id?: string | null;
    knowledge_point_id?: number | null;
    is_correct: boolean | null;
    score: number;
    correct_answer?: unknown;
    message: string;
    attempt?: {
        attempt_id: string;
        training_session_id: string;
        generated_question_id: string;
        user_id: number;
        answer: unknown;
        is_correct: boolean | null;
        score: number;
        cost_time?: number | null;
        submission_id?: string | null;
        profile_rebuild_snapshot_id?: string | null;
        submitted_at: string;
    };
    profile_rebuild_triggered?: boolean;
    latest_snapshot_id?: string | null;
    profile_rebuild?: Record<string, unknown> | null;
}

export interface TrainingSessionData {
    training_session_id: string;
    user_id: number;
    class_id?: number | null;
    course_id?: number | null;
    profile_snapshot_id?: string | null;
    source_type?: string;
    diagnose_result?: Record<string, unknown>;
    training_context?: Record<string, unknown>;
    created_at?: string;
    question_count?: number;
    attempt_count?: number;
}

export interface TrainingSessionResponse {
    session: TrainingSessionData;
    questions: GeneratedTrainingQuestion[];
}

export interface TrainingQuestionListResponse {
    training_session_id: string;
    questions: GeneratedTrainingQuestion[];
}

export interface UserTrainingSessionsResponse {
    user_id: number;
    sessions: TrainingSessionData[];
}

// 定义后端返回的课程数据类型
export interface CourseSummaryDto {
    id: number;
    name: string;
    description: string;
    difficulty: number;
    imageUrl: string;
    type: string;
    tags: string[];
    status: string;
    createdBy?: number | null;
    creatorEditable?: boolean;
}

export interface TeachingClassDto {
    teachingClassId: number;
    className: string;
    academicYear: string;
    semester: 1 | 2;
    teacherId: number;
    teacherName?: string | null;
    startDate?: string | null;
    endDate?: string | null;
    status: "ACTIVE" | "ARCHIVED" | string;
    studentCount: number;
    courseCount: number;
    currentCourse?: string | null;
    lastActiveAt?: string | null;
    canManage: boolean;
    createdAt: string;
    updatedAt: string;
}

export interface TeachingClassSavePayload {
    className: string;
    academicYear: string;
    semester: 1 | 2;
    startDate?: string | null;
    endDate?: string | null;
}

export interface TeachingClassStudentDto {
    studentId: number;
    studentNumber: string;
    studentName?: string | null;
    administrativeClass?: string | null;
    joinedAt: string;
    recentActivityAt?: string | null;
}

export interface TeachingClassCourseDto {
    courseId: number;
    courseName: string;
    courseDescription: string;
    teachingContent?: string | null;
    teachingOrder: number;
    plannedStartDate?: string | null;
    plannedEndDate?: string | null;
    createdBy?: number | null;
    creatorName?: string | null;
    updatedAt: string;
}

export interface TeachingClassImportRowDto {
    rowNumber: number;
    studentNumber: string;
    studentName: string;
    administrativeClass: string;
}

export interface TeachingClassImportPreviewDto {
    batchId: string;
    newAccounts: TeachingClassImportRowDto[];
    existingAccounts: TeachingClassImportRowDto[];
    duplicateRows: Array<{ rowNumber: number; studentNumber: string; firstRowNumber: number }>;
    errorRows: Array<{ rowNumber: number; message: string }>;
    expiresAt: string;
}

export interface TeachingClassImportResultDto {
    createdAccountCount: number;
    addedMemberCount: number;
    skippedMemberCount: number;
}

export interface TeacherGeneratedQuestionRecord {
    generatedQuestionId: string;
    trainingSessionId?: string | null;
    student: { studentId: number; studentNumber?: string | null; studentName: string };
    teachingClassId: number;
    teachingClassName: string;
    courseId?: number | null;
    courseName?: string | null;
    knowledgePointId?: number | null;
    knowledgePointName?: string | null;
    questionType?: string | null;
    difficulty?: string | null;
    title: string;
    stem: string;
    options: string[];
    generationReason?: string | null;
    standardAnswer?: string | null;
    referenceAnswer?: string | null;
    explanation?: string | null;
    latestAttempt?: {
        attemptId: string;
        answer: unknown;
        isCorrect?: boolean | null;
        score: number;
        costTime?: number | null;
        submittedAt?: string | null;
    } | null;
    attemptCount: number;
    generatedAt?: string | null;
    isTypical: boolean;
    attemptHistory?: TeacherQuestionAttemptDto[];
}

export interface TeacherQuestionAttemptDto {
    attemptId: string;
    answer: unknown;
    isCorrect?: boolean | null;
    score: number;
    costTime?: number | null;
    submittedAt?: string | null;
}

export interface TeacherCourseQuestionSummaryDto {
    studentCount: number;
    questionCount: number;
    attemptedQuestionCount: number;
    attemptCount: number;
    correctQuestionCount: number;
    incorrectQuestionCount: number;
    accuracyRate: number;
    averageScore: number;
    students: Array<{
        studentId: number;
        studentName: string;
        studentNumber?: string | null;
        questionCount: number;
        attemptCount: number;
        correctQuestionCount: number;
        incorrectQuestionCount: number;
        accuracyRate: number;
    }>;
    knowledgePoints: Array<{
        knowledgePointName: string;
        questionCount: number;
        attemptCount: number;
        correctQuestionCount: number;
        incorrectQuestionCount: number;
        affectedStudentCount: number;
        accuracyRate: number;
    }>;
}

export interface TeacherCourseQuestionsDto {
    success: boolean;
    teachingClassId: number;
    course: { courseId: number; courseName: string };
    studentId?: number | null;
    items: TeacherGeneratedQuestionRecord[];
    summary: TeacherCourseQuestionSummaryDto;
}

export interface TeacherCourseAnalysisDto {
    teacherId: number;
    teachingClassId: number;
    courseId: number;
    scope: "CLASS" | "STUDENT" | string;
    studentId?: number | null;
    analysisStatus: "IDLE" | "RUNNING" | "READY" | "FAILED" | string;
    analysis?: {
        scope: "class_course" | "student_course" | string;
        courseId: number;
        courseName: string;
        generatedBy: string;
        fallbackUsed: boolean;
        providerMessage?: string | null;
        generatedAt?: string | null;
        overallComment: string;
        summary?: TeacherCourseQuestionSummaryDto;
        knowledgeFindings?: Array<{
            knowledgePointName: string;
            evidence?: string;
            teacherAction?: string;
            affectedStudents?: string[];
            representativeQuestionId?: string | null;
            representativeQuestionTitle?: string | null;
            observedAnswer?: string | null;
            standardAnswer?: string | null;
            diagnosis?: string | null;
            instruction?: string | null;
            check?: string | null;
            incorrectQuestionCount?: number;
            affectedStudentCount?: number;
            accuracyRate?: number;
        }>;
        representativeMistakes?: Array<{
            generatedQuestionId: string;
            title: string;
            studentName?: string | null;
            knowledgePointName?: string | null;
            latestAnswer?: unknown;
            standardAnswer?: unknown;
            score?: number | null;
        }>;
        teachingSuggestions?: string[];
        [key: string]: unknown;
    } | null;
    sourceStats?: TeacherCourseQuestionSummaryDto | null;
    lastErrorMessage?: string | null;
    generatedAt?: string | null;
}

export interface TeacherGeneratedQuestionPage {
    success: boolean;
    teacherId: number;
    items: TeacherGeneratedQuestionRecord[];
    total: number;
    page: number;
    size: number;
}

export interface TeacherGeneratedQuestionSummary {
    teachingClassId: number;
    items: Array<{
        knowledgePointId?: number | null;
        knowledgePointName: string;
        studentCount: number;
        generatedQuestionCount: number;
        attemptedCount: number;
        incorrectCount: number;
        incorrectRate: number;
        representativeQuestionIds: string[];
    }>;
}

export interface TeachingClassAnalysisDto {
    teachingClassId: number;
    analysisStatus: "IDLE" | "RUNNING" | "READY" | string;
    analysis?: {
        overallComment?: string;
        commonProblems?: Array<{
            title: string;
            evidence: string;
            studentCount: number;
            questionIds: string[];
            teacherAction: string;
        }>;
        teachingSuggestions?: Array<{ title?: string; action?: string; evidenceQuestionIds?: string[] }>;
        representativeQuestions?: Array<{ generatedQuestionId?: string; reason?: string }>;
        [key: string]: unknown;
    } | null;
    sourceStats?: Record<string, unknown> | null;
    generatedAt?: string | null;
    dataCutoffAt?: string | null;
    lastErrorMessage?: string | null;
}

export interface TeachingStudentAnalysisDto {
    teacherId: number;
    teachingClassId: number;
    studentId: number;
    analysisStatus: "IDLE" | "RUNNING" | "READY" | string;
    analysis?: TeacherStudentAiAnalysisDto | null;
    sourceStats?: Record<string, unknown> | null;
    generatedAt?: string | null;
    dataCutoffAt?: string | null;
    lastErrorMessage?: string | null;
}

export interface AiAnalysisHealthDto {
    configured: boolean;
    providerReachable: boolean;
    message: string;
}

export interface CapabilityEvidenceItemDto {
    kind: "LAB_START" | "COMMAND" | "ERROR" | "HINT" | "AI" | "ATTEMPT" | "SUCCESS" | string;
    occurredAt?: string | null;
    sourceId: string;
    title: string;
    detail?: string;
    status?: string;
    labSessionId?: string | null;
    moduleId?: number | null;
    taskId?: number | null;
    command?: string;
    commandCategory?: string | null;
    exitCode?: number | null;
    retryOutcome?: "success" | "recovered" | "unresolved" | "pending" | string;
    errorCategory?: string | null;
    severity?: string | null;
    score?: number;
    isCorrect?: boolean;
    aiAskCount?: number;
}

export interface CapabilityDimensionDto {
    key: "knowledge_mastery" | "troubleshooting" | "autonomy" | "ai_collaboration" | "engagement" | string;
    label: string;
    score?: number | null;
    summary: string;
    evidence: CapabilityEvidenceItemDto[];
}

export interface CapabilityEvidenceResponseDto {
    teachingClassId: number;
    studentId: number;
    profileSnapshotId?: string | null;
    computedAt?: string | null;
    overallScore?: number | null;
    dimensions: CapabilityDimensionDto[];
}

export interface LearningReplayResponseDto {
    teachingClassId: number;
    studentId: number;
    items: CapabilityEvidenceItemDto[];
}

export type CapabilityGrowthDimensionKey =
    | "knowledge_mastery"
    | "troubleshooting"
    | "autonomy"
    | "ai_collaboration"
    | "engagement";

export interface CapabilityGrowthMetricDto {
    key: string;
    label: string;
    baselineValue?: number | null;
    currentValue?: number | null;
    unit: "percent" | "seconds" | "score" | string;
    changeRate?: number | null;
    direction: "improved" | "stable" | "declined" | "insufficient" | string;
    baselineSampleCount: number;
    currentSampleCount: number;
    confidence: "high" | "moderate" | "emerging" | "insufficient" | string;
    explanation: string;
    sourceTypes: string[];
    sourceRecordIds: string[];
}

export interface CapabilityGrowthEvidenceDto {
    kind: string;
    title: string;
    detail?: string;
    occurredAt?: string | null;
    sourceId: string;
    sourceType: string;
    labSessionId?: string | null;
    conversationId?: string | null;
    courseId?: number | null;
    moduleId?: number | null;
    taskId?: number | null;
    moduleName?: string | null;
    status?: string | null;
    startedAt?: string | null;
    endedAt?: string | null;
    durationSeconds?: number | null;
    targetUrl?: string | null;
    containerName?: string | null;
    eventCount?: number;
    eventTypes?: string[];
    messageContent?: string | null;
    knowledgePointId?: number | null;
    knowledgePointName?: string | null;
    questionType?: string | null;
    difficulty?: string | null;
    costTime?: number | null;
    isCorrect?: boolean | null;
    commandCategory?: string | null;
    recoverySeconds?: number | null;
    failedCommand?: string | null;
    recoveredCommand?: string | null;
    aiAskCount?: number | null;
    activeSeconds?: number | null;
}

export interface CapabilityGrowthDimensionDto {
    key: CapabilityGrowthDimensionKey;
    label: string;
    baselineScore?: number | null;
    currentScore?: number | null;
    delta?: number | null;
    confidence: string;
    summary: string;
    metrics: CapabilityGrowthMetricDto[];
    evidence: CapabilityGrowthEvidenceDto[];
}

export interface CapabilityGrowthHistoryDto {
    snapshotId: string;
    computedAt?: string | null;
    overallScore?: number | null;
    knowledge_masteryScore?: number | null;
    troubleshootingScore?: number | null;
    autonomyScore?: number | null;
    ai_collaborationScore?: number | null;
    engagementScore?: number | null;
}

export interface CapabilityGrowthResponseDto {
    studentId: number;
    teachingClassId?: number | null;
    baselineComputedAt?: string | null;
    currentComputedAt?: string | null;
    calculationVersion: string;
    dataProvenance: {
        mode: string;
        calculationVersion?: string;
        eligibleRecordCount?: number;
        excludedRecordCount?: number;
        unverifiableRecordCount?: number;
        sourceTypes?: string[];
        snapshotIds?: string[];
    };
    overall: {
        baselineScore?: number | null;
        currentScore?: number | null;
        delta?: number | null;
    };
    dimensions: CapabilityGrowthDimensionDto[];
    history: CapabilityGrowthHistoryDto[];
    message?: string | null;
}

export interface KnowledgeRiskItemDto {
    courseId?: number | null;
    courseName: string;
    teachingOrder?: number | null;
    knowledgePointId?: number | null;
    knowledgePointName: string;
    knowledgeCategory: string;
    studentCount: number;
    attemptedStudentCount: number;
    incorrectStudentCount: number;
    attemptedCount: number;
    incorrectCount: number;
    incorrectRate: number;
    errorShare?: number;
    unansweredStudentCount?: number;
    riskLevel: "high" | "medium" | "attention" | "good" | string;
    affectedStudents: Array<{ studentId: number; studentName: string }>;
    representativeQuestions: Array<{ generatedQuestionId: string; title: string }>;
}

export interface KnowledgeRiskMapResponseDto {
    teachingClassId: number;
    courseId?: number | null;
    items: KnowledgeRiskItemDto[];
}

export interface KnowledgeRiskDetailDto extends KnowledgeRiskItemDto {
    commonMistakes: Array<{ answer: string; count: number; studentCount: number }>;
    representativeAttempts: Array<{
        studentId: number;
        studentName: string;
        generatedQuestionId: string;
        title: string;
        answer: string;
        standardAnswer: string;
        score?: number | null;
        submittedAt?: string | null;
    }>;
    pagination: { page: number; size: number; total: number };
}

export type KnowledgeExerciseRole = "FOUNDATION" | "CONSOLIDATION" | "TRANSFER";
export type KnowledgeExerciseReviewStatus = "PENDING_REVIEW" | "APPROVED" | "NEEDS_REVISION" | "REJECTED";

export interface KnowledgeExerciseDto {
    exerciseId: number;
    analysisId: number;
    role: KnowledgeExerciseRole;
    questionType: string;
    stem: string;
    options: string[];
    standardAnswer: string;
    explanation: string;
    difficulty: number;
    generationRationale: string;
    reviewStatus: KnowledgeExerciseReviewStatus | string;
    reviewComment: string;
    sourceVersion: number;
    reviewedBy?: number | null;
    reviewedAt?: string | null;
    updatedAt?: string | null;
}

export interface KnowledgeAiAnalysisDto {
    teacherId: number;
    teachingClassId: number;
    courseId: number;
    knowledgePointId: number;
    analysisStatus: "IDLE" | "RUNNING" | "READY" | "FAILED" | string;
    analysis?: {
        overallConclusion: string;
        commonMistakes: Array<{ title: string; reason: string }>;
        teachingAdvice: Array<{ title: string; action: string }>;
    } | null;
    evidence?: Record<string, unknown> | null;
    lastErrorMessage?: string | null;
    generatedAt?: string | null;
    exercises: KnowledgeExerciseDto[];
}

export type TeacherInterventionActionType = "FOCUS_GROUP" | "TARGETED_PRACTICE" | "LESSON_EXAMPLE";

export interface TeacherInterventionStudentDto {
    studentId: number;
    studentNumber?: string | null;
    studentName?: string | null;
    assignmentStatus: "PENDING" | "STARTED" | "COMPLETED" | string;
    trainingSessionId?: string | null;
    startedAt?: string | null;
    completedAt?: string | null;
    baseline?: Record<string, unknown> | null;
    latest?: Record<string, unknown> | null;
    comparison?: {
        delta: Record<string, number>;
        improvedDimensions: string[];
        status: string;
    };
    resultSummary?: { attemptCount: number; correctCount: number; averageScore: number } | null;
}

export interface TeacherInterventionDto {
    interventionId: number;
    teacherId: number;
    teachingClassId: number;
    courseId?: number | null;
    title: string;
    actionType: TeacherInterventionActionType;
    knowledgePointId?: number | null;
    description: string;
    status: "ACTIVE" | "COMPLETED" | "CANCELLED" | string;
    baselineAt: string;
    dueAt: string;
    createdAt: string;
    updatedAt: string;
    students: TeacherInterventionStudentDto[];
    questions: Array<{ generatedQuestionId: string; title: string; usageType: string }>;
    progress: {
        studentCount: number;
        completedCount: number;
        completionRate: number;
        evaluationDue: boolean;
    };
}

export interface StudentTeacherAssignmentDto extends TeacherInterventionDto {
    className?: string | null;
    teacherName?: string | null;
    courseName?: string | null;
    knowledgePointName?: string | null;
    assignmentStatus: "PENDING" | "STARTED" | "COMPLETED" | string;
    trainingSessionId?: string | null;
    startedAt?: string | null;
    completedAt?: string | null;
    questionCount: number;
    estimatedMinutes: number;
    isOverdue: boolean;
    resultSummary?: { attemptCount: number; correctCount: number; averageScore: number } | null;
}

export interface TeacherUserListItemDto {
    userId: number;
    userStudentNumber: string;
    userName: string;
    userEmail?: string | null;
    userTel?: string | null;
    userAcademy?: string | null;
    userClass?: string | null;
    userGender?: number | null;
    classId?: number | null;
    createTime?: string | null;
    status?: string | null;
}

export interface TeacherUserListPageDto {
    list: TeacherUserListItemDto[];
    total: number;
    page: number;
    pageSize: number;
}

export type TeacherUserListResponse = Result<TeacherUserListPageDto>;

export interface ClassProfileLatestDto {
    snapshot_id?: string;
    class_id: number;
    course_id?: number | null;
    computed_at?: string | null;
    student_count?: number;
    class_avg_knowledge_mastery?: number;
    class_avg_troubleshooting?: number;
    class_avg_autonomy?: number;
    class_avg_ai_collaboration?: number;
    class_avg_engagement?: number;
    class_overall_score?: number;
    weak_dimensions_json?: Array<{
        dimension?: string;
        dimension_name?: string;
        average_score?: number;
        description?: string;
    }>;
    strengths_json?: Array<{
        dimension?: string;
        dimension_name?: string;
        average_score?: number;
        description?: string;
    }>;
    risk_students_json?: Array<{
        user_id: number;
        overall_score?: number;
        knowledge_mastery_score?: number;
        troubleshooting_score?: number;
        autonomy_score?: number;
        ai_collaboration_score?: number;
        engagement_score?: number;
        risk_level?: string;
        risk_reasons?: string[];
        weak_dimensions?: string[];
    }>;
    summary_json?: Record<string, unknown>;
    source_range_start?: string | null;
    source_range_end?: string | null;
    created_at?: string | null;
}

export interface ClassProfileStudentMetricDto {
    user_id: number;
    overall_score?: number;
    knowledge_mastery_score?: number;
    troubleshooting_score?: number;
    autonomy_score?: number;
    ai_collaboration_score?: number;
    engagement_score?: number;
    risk_level?: string;
    risk_reasons?: string[];
    weak_dimensions?: string[];
    created_at?: string | null;
}

export interface ClassProfileStudentsResponse {
    class_id: number;
    snapshot_id?: string | null;
    student_count?: number;
    source?: string;
    students: ClassProfileStudentMetricDto[];
}

export interface ScoreboardItemDto {
    rank: number;
    userId: number;
    studentNumber?: string;
    username: string;
    nickname?: string;
    classId?: number | null;
    className?: string;
    avatarUrl?: string | null;
    /** 还没做过实验的学生没有画像数据，这里为 null，前端渲染成 -- */
    overallScore: number | null;
    trainingCount: number;
    generatedQuestionAttemptCount: number;
    averageTrainingScore?: number | null;
    lastActiveAt?: string | null;
    /** false 表示该学生还没有任何训练记录，只是名单里有这个人 */
    hasActivity?: boolean;
    trend?: "up" | "down" | "stable" | string;
    weakDimension?: string | null;
    bestDimension?: string | null;
}

export interface ScoreboardResponseDto {
    success: boolean;
    updatedAt: string;
    source: string;
    items: ScoreboardItemDto[];
}

export interface TeacherDashboardSummaryDto {
    classCount: number;
    studentCount: number;
    activeStudentCount: number;
    generatedQuestionCount: number;
    attemptCount: number;
    averageProfileScore: number;
    averageTrainingScore: number;
}

export interface TeacherWeakDimensionDto {
    dimension: string;
    label: string;
    averageScore: number;
    studentCount: number;
}

export interface TeacherActivityDto {
    userId: number;
    username: string;
    eventType: string;
    createdAt?: string | null;
    summary: string;
}

export interface TeacherTopStudentDto {
    userId: number;
    username: string;
    overallScore: number;
    attemptCount: number;
}

export interface TeacherDashboardResponseDto {
    success: boolean;
    teacherId?: number | null;
    updatedAt: string;
    summary: TeacherDashboardSummaryDto;
    weakDimensions: TeacherWeakDimensionDto[];
    recentActivities: TeacherActivityDto[];
    topStudents: TeacherTopStudentDto[];
}

export interface TeacherClassDto {
    classId: number;
    className: string;
    studentCount: number;
    activeStudentCount: number;
    averageProfileScore: number;
    averageTrainingScore: number;
    lastActiveAt?: string | null;
}

export interface TeacherClassesResponseDto {
    success: boolean;
    teacherId?: number | null;
    items: TeacherClassDto[];
}

export interface TeacherClassStudentDto {
    userId: number;
    username: string;
    nickname?: string | null;
    avatarUrl?: string | null;
    classId?: number | null;
    className?: string | null;
    overallScore: number;
    knowledgeMasteryScore: number;
    troubleshootingScore: number;
    autonomyScore: number;
    aiCollaborationScore: number;
    engagementScore: number;
    trainingQuestionSubmitCount: number;
    generatedQuestionAttemptCount: number;
    averageTrainingScore: number;
    lastActiveAt?: string | null;
}

export interface TeacherClassStudentsResponseDto {
    success: boolean;
    classId: number;
    items: TeacherClassStudentDto[];
}

export interface TeacherClassAiSuggestionDto {
    dimension: string;
    label: string;
    averageScore: number;
    affectedStudentCount: number;
    evidence: string;
    inClassAction: string;
    afterClassFollowUp: string;
    priority: "high" | "medium" | "low" | string;
}

export interface TeacherClassAiAnalysisDto {
    scope: "class" | string;
    generatedBy: "llm" | "rule_fallback" | string;
    fallbackUsed: boolean;
    generatedAt?: string | null;
    overallComment: string;
    suggestions: TeacherClassAiSuggestionDto[];
}

export interface TeacherStudentProfileResponseDto {
    success: boolean;
    userId: number;
    latestProfile: ProfileLatestResponse | null;
    dashboard: ProfileDashboardResponse;
    recentAttempts: Array<{
        attemptId: string;
        generatedQuestionId?: string | null;
        title: string;
        questionType?: string | null;
        difficulty?: string | null;
        score: number;
        isCorrect?: boolean | null;
        submittedAt?: string | null;
    }>;
    personalSignals?: Array<{
        eventType: string;
        eventTime?: string | null;
        moduleId?: number | null;
        taskId?: number | null;
        questionId?: number | null;
        summary: string;
        severity?: string | null;
        errorCategory?: string | null;
    }>;
    recommendations: Array<{
        dimension: string;
        label: string;
        score?: number;
        summary: string;
        evidence?: string;
        teacherAction?: string;
        priority?: "high" | "medium" | "low" | string;
        scope?: "student" | "class" | string;
    }>;
}

export interface TeacherStudentAiFocusAreaDto {
    dimension: string;
    label: string;
    score?: number;
    evidence: string;
    teacherAction: string;
    priority: "high" | "medium" | "low" | string;
}

export interface TeacherStudentAiAnalysisDto {
    scope: "student" | string;
    generatedBy: "llm" | "rule_fallback" | string;
    fallbackUsed: boolean;
    generatedAt?: string | null;
    overallComment: string;
    focusAreas: TeacherStudentAiFocusAreaDto[];
}

export interface TeacherGeneratedQuestionDto {
    generatedQuestionId: string;
    userId: number;
    username: string;
    title: string;
    stem: string;
    questionType?: string | null;
    difficulty?: string | null;
    knowledgeTags: string[];
    qualityScore: number;
    reviewStatus: string;
    standardAnswer?: string | null;
    referenceAnswer?: string | null;
    explanation?: string | null;
    teachingObjective?: string | null;
    expectedSkill?: string | null;
    gradingRubric?: unknown;
    attemptCount: number;
    averageScore: number;
    createdAt?: string | null;
}

export interface TeacherGeneratedQuestionsResponseDto {
    success: boolean;
    teacherId?: number | null;
    items: TeacherGeneratedQuestionDto[];
    total: number;
    page: number;
    size: number;
}

export interface LabEventListItem {
    type?: string;
    event_type?: string;
    received_at?: string;
    timestamp?: string;
    levelTitle?: string;
    prompt?: string;
    container?: string;
    message?: string;
    [key: string]: unknown;
}

export interface LabEventsResponse {
    total: number;
    events: LabEventListItem[];
}

export interface TeacherCourseMutationPayload {
    name: string;
    description: string;
    difficulty: number;
    cover?: string;
    teacherName?: string;
    category: string;
    tags: string[];
    status: AdminCourse["status"];
}

export interface TeacherLabMutationPayload {
    name: string;
    description: string;
    difficulty: number;
    type?: string;
    image?: string;
}

export interface TeacherUserMutationPayload {
    userStudentNumber?: string;
    userName: string;
    userAcademy?: string;
    userClass?: string;
    userEmail?: string;
    userTel?: string;
    userGender?: number;
    classId?: number;
}

export interface ImageUploadResponse {
    id?: number;
    filename?: string;
    originalFilename?: string;
    url?: string;
    size?: number;
    contentType?: string;
    uploadTime?: string;
}

/** 上传失败是不是因为图片服务压根没起来（连接被拒 / 超时），而不是文件本身的问题。 */
export function isImageServiceUnreachable(error: unknown): boolean {
    if (!axios.isAxiosError(error)) {
        return false;
    }
    return !error.response;
}

export async function uploadImageFile(file: File): Promise<ImageUploadResponse> {
    const formData = new FormData();
    formData.append("file", file);
    const response = await axios.post<ImageUploadResponse>(`${IMAGE_SERVICE_BASE_URL}/upload`, formData, {
        headers: { "Content-Type": "multipart/form-data" },
        timeout: 15000,
    });
    const data = response.data;
    if (data.url && !data.url.startsWith("http://") && !data.url.startsWith("https://")) {
        data.url = new URL(data.url, IMAGE_SERVICE_BASE_URL).toString();
    } else if (!data.url && data.filename) {
        data.url = `${IMAGE_SERVICE_BASE_URL}/files/${encodeURIComponent(data.filename)}`;
    }
    return data;
}

/**
 * 头像地址。库里只存 image-service 返回的文件名（avatar_xxx.png），
 * 显示时才按当前 VITE_IMAGE_SERVICE_BASE_URL 拼出完整地址——
 * 存绝对地址的话换机器 / 换端口 / 走外网时，已有头像会全部变裂图。
 *
 * 老数据里可能已经存了绝对 URL 或站内相对路径，这两种原样返回。
 */
export function avatarUrl(value?: string | null): string {
    const name = (value || "").trim();
    if (!name) {
        return "";
    }
    if (/^(https?:)?\/\//i.test(name) || name.startsWith("data:") || name.startsWith("blob:") || name.startsWith("/")) {
        return name;
    }
    return `${IMAGE_SERVICE_BASE_URL}/files/${encodeURIComponent(name)}`;
}

export let image = (imageName: string | null | undefined) => {
    // 添加空值检查
    if (!imageName) {
        return '/default-course-image.png'; // 默认图片路径
    }
    
    // 如果已经是完整URL，直接返回
    if (imageName.startsWith('http://') || imageName.startsWith('https://')) {
        return imageName;
    }
    
    // 如果是本地文件路径，直接从public目录加载
    if (imageName.startsWith('/') || imageName.includes('.png') || imageName.includes('.jpg') || imageName.includes('.jpeg') || imageName.includes('.svg')) {
        // 尝试从public目录加载
        try {
            // 仅移除标准 UUID 前缀 (类似 "a9fe8e50-ba21-45ef-abd5-50b717857502-1.SQL注入攻防实战.png")，
            // 不能按任意 "-" 拆分，否则会误伤 cover-ids-ips.png、default-course-image.png 等合法文件名
            const uuidPrefix = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}-/i;
            const fileName = imageName.replace(uuidPrefix, '');
            // 如果文件名包含路径分隔符，只取最后一部分
            const cleanFileName = fileName.includes('/') ? fileName.split('/').pop() : fileName;
            
            if (cleanFileName) {
                return `/${cleanFileName}`;
            }
        } catch (e) {
            console.warn('处理图片路径出错:', e);
        }
    }
    
    // 拼接后端图片URL
    return IMAGE_URL + imageName;
};

export async function login(loginRequest: { userStudentNumber: string; userPassword: string; }): Promise<Result<{ 
    loginData: {
        userId: number; 
        userStudentNumber: string; 
        userImage: string; 
        userName: string; 
        classId: number; 
        className?: string | null;
        role?: string | null;
        status?: string | null;
        token: string; 
    }
}>> {
    try {
        const response = await axios.post(`${BASE_URL}/stu/login`, loginRequest);
        return response.data;
    } catch (error) {
        const backendError = getBackendErrorResponse<{
            loginData: {
                userId: number;
                userStudentNumber: string;
                userImage: string;
                userName: string;
                classId: number;
                className?: string | null;
                role?: string | null;
                status?: string | null;
                token: string;
            }
        }>(error);
        if (backendError) {
            return backendError;
        }
        throw error;
    }
}

export interface RegisterClassOption {
    teachingClassId: number;
    className: string;
    academicYear: string;
    semester: number;
    teacherName?: string | null;
}

/**
 * 注册页可选班级。数据源是教师端已创建且未归档的教学班，
 * 教师没建过的班级学生端选不到，后端 /stu/register 也会再校验一次。
 */
export async function getRegisterClassOptions(): Promise<RegisterClassOption[]> {
    const response = await axios.get<Result<{ classes: RegisterClassOption[] }>>(
        `${BASE_URL}/stu/register-options`,
    );
    return response.data?.data?.classes ?? [];
}

export async function register(registerRequest: RegisterForm): Promise<Result<undefined>> {
    try {
        const response = await axios.post(`${BASE_URL}/stu/register`, registerRequest);
        return response.data;
    } catch (error) {
        const backendError = getBackendErrorResponse<undefined>(error);
        if (backendError) {
            return backendError;
        }
        throw error;
    }
}

export async function getUserInfo(token: string): Promise<Result<User>> {
    try {
        const response = await axios.get(`${BASE_URL}/stu/profile`, {
            headers: {
                Authorization: `Bearer ${token}`,
            },
        });
        
        if (response.status === 200) {
            return response.data;
        } else {
            throw new Error(`Unexpected response status: ${response.status}`);
        }
    } catch (error) {
        const backendError = getBackendErrorResponse<User>(error);
        if (backendError) {
            return backendError;
        }
        throw error;
    }
}

export async function updateUserInfoByToken(user: User, token: string): Promise<Result<User>> {
    try {
        const response = await axios.post(`${BASE_URL}/stu/updateProfile`, user, {
            headers: {
                Authorization: `Bearer ${token}`,
            },
        });
        return response.data;
    } catch (error) {
        const backendError = getBackendErrorResponse<User>(error);
        if (backendError) {
            return backendError;
        }
        throw error;
    }
}

export async function submitQuestionAnswer(
    payload: QuestionSubmitRequest
): Promise<QuestionSubmitResponse> {
    const response = await axios.post(`${AGENT_BASE_URL}/api/questions/submit`, payload);
    return response.data;
}

export async function startLabSession(
    payload: LabSessionStartRequest
): Promise<LabSessionStartResponse> {
    const response = await axios.post(`${AGENT_BASE_URL}/api/lab-sessions/start`, payload);
    return response.data;
}

export async function stopLabSession(sessionId: string): Promise<LabSessionStopResponse> {
    const response = await axios.post(`${AGENT_BASE_URL}/api/lab-sessions/${sessionId}/stop`);
    return response.data;
}

export async function submitFlagAnswer(payload: FlagSubmitRequest): Promise<FlagSubmitResponse> {
    const response = await axios.post(`${AGENT_BASE_URL}/api/flags/submit`, payload);
    return response.data;
}

export async function ingestEvents(payload: EventsIngestPayload): Promise<Result<unknown>> {
    try {
        const response = await axios.post(`${AGENT_BASE_URL}/api/external/events/ingest`, payload, {
            headers: { "Content-Type": "application/json" },
        });
        return response.data;
    } catch (error) {
        const backendError = getBackendErrorResponse<unknown>(error);
        if (backendError) {
            return backendError;
        }

        console.error("[EventsIngest] 事件上报失败:", error);
        return {
            isSuccess: 0,
            status: 500,
            message: "事件上报失败",
            data: null as unknown,
        };
    }
}

export async function getProfileDashboard(userId: number): Promise<ProfileDashboardResponse> {
    const response = await axios.get(`${AGENT_BASE_URL}/api/profile/${userId}/dashboard`);
    return response.data;
}

export async function getProfileLatest(userId: number): Promise<ProfileLatestResponse> {
    const response = await axios.get(`${AGENT_BASE_URL}/api/profile/${userId}/latest`);
    return response.data;
}

export async function diagnoseTraining(
    payload: TrainingDiagnoseRequest
): Promise<TrainingDiagnoseResponse> {
    const response = await axios.post(`${AGENT_BASE_URL}/api/training/diagnose`, payload);
    return response.data;
}

export async function generateTrainingQuestions(
    payload: TrainingGenerationRequest
): Promise<TrainingGenerationResponse> {
    const response = await axios.post(`${AGENT_BASE_URL}/api/training/generate`, payload);
    return response.data;
}

export async function generateTrainingQuestion(
    payload: TrainingSingleQuestionRequest
): Promise<TrainingSingleQuestionResponse> {
    const response = await axios.post(`${AGENT_BASE_URL}/api/training/generate-question`, payload);
    return response.data;
}

export async function generateTrainingQuestionSet(
    payload: TrainingQuestionSetRequest
): Promise<TrainingQuestionSetResponse> {
    const response = await axios.post(
        `${AGENT_BASE_URL}/api/training/generate-question-set`,
        payload,
        { timeout: 50_000 }
    );
    return response.data;
}

export async function submitTrainingAnswer(
    payload: TrainingSubmitRequest
): Promise<TrainingSubmitResponse> {
    const response = await axios.post(`${AGENT_BASE_URL}/api/training/submit`, payload);
    return response.data;
}

export async function submitGeneratedQuestionAnswer(
    generatedQuestionId: string,
    payload: GeneratedQuestionAnswerSubmitRequest
): Promise<GeneratedQuestionAnswerSubmitResponse> {
    const response = await axios.post(`${AGENT_BASE_URL}/api/training/generated-question/${generatedQuestionId}/submit`, payload);
    return response.data;
}

export async function getTrainingSession(
    trainingSessionId: string
): Promise<TrainingSessionResponse> {
    const response = await axios.get(`${AGENT_BASE_URL}/api/training/session/${trainingSessionId}`);
    return response.data;
}

export async function getTrainingSessionSummary(
    trainingSessionId: string,
    userId: number
): Promise<TrainingSessionSummaryResponse> {
    const response = await axios.get(`${AGENT_BASE_URL}/api/training/session/${trainingSessionId}/summary`, {
        params: { userId }
    });
    return response.data;
}

export async function getTrainingQuestions(
    trainingSessionId: string
): Promise<TrainingQuestionListResponse> {
    const response = await axios.get(`${AGENT_BASE_URL}/api/training/questions/${trainingSessionId}`);
    return response.data;
}

export async function getUserTrainingSessions(
    userId: number
): Promise<UserTrainingSessionsResponse> {
    const response = await axios.get(`${AGENT_BASE_URL}/api/training/users/${userId}/sessions`);
    return response.data;
}

export async function getModuleList(): Promise<Result<ModuleOverViewType[]>> {
    const response = await axios.get(`${EXPERIMENT_MODULE_BASE_URL}/stu/module/modules`);
    if (response.status === 200) {
        // Return the response data (e.g., updated user info)
        return response.data;
    } else {
        // Handle unexpected response status
        throw new Error(`Unexpected response status: ${response.status}`);
    }
}

export async function getCourseList(): Promise<Result<CourseSummaryDto[]>> {
    const response = await axios.get(`${EXPERIMENT_MODULE_BASE_URL}/course/overview-list`);
    if (response.status === 200) {
        return response.data;
    } else {
        throw new Error(`Unexpected response status: ${response.status}`);
    }
}

const LEARNING_EVENT_ENDPOINT_MAP: Record<string, string> = {
    AI_ASK: "/api/events/ai-interaction",
    AI_INTERACTION: "/api/events/ai-interaction",
    FLAG_SUBMIT: "/api/events/flag-submit",
    LAB_START: "/api/events/lab-start",
    LAB_STOP: "/api/events/lab-stop",
    QUESTION_SUBMIT: "/api/events/question-submit",
};

export async function reportLearningEvent(payload: LearningEventPayload): Promise<any> {
    const normalizedType = String(payload.event_type || "").trim().toUpperCase();
    const endpoint = LEARNING_EVENT_ENDPOINT_MAP[normalizedType];

    if (!endpoint) {
        throw new Error(`Unsupported learning event type: ${payload.event_type}`);
    }

    const response = await axios.post(`${AGENT_BASE_URL}${endpoint}`, {
        ...payload,
        event_type: normalizedType,
        source: payload.source || "frontend",
    });
    return response.data;
}

export async function getMyStudentProfile(): Promise<any> {
    const token = getStoredToken();
    const response = await axios.get(`${BASE_URL}/api/profile/student/me`, {
        headers: {
            Authorization: `Bearer ${token}`
        }
    });
    return response.data;
}


function clampDifficulty(value: number | null | undefined): 1 | 2 | 3 | 4 | 5 {
    const difficulty = Number(value ?? 3);
    return Math.min(Math.max(difficulty, 1), 5) as 1 | 2 | 3 | 4 | 5;
}

function mapTeacherCourseStatus(status: string | null | undefined): AdminCourse["status"] {
    const normalized = String(status ?? "").trim().toLowerCase();

    if (normalized === "draft" || normalized === "locked") {
        return "draft";
    }

    if (normalized === "archived") {
        return "archived";
    }

    return "published";
}

function mapTeacherLabStatus(status: string | null | undefined): AdminExperiment["status"] {
    const normalized = String(status ?? "").trim().toLowerCase();

    if (normalized === "draft" || normalized === "locked") {
        return "draft";
    }

    if (normalized === "archived") {
        return "archived";
    }

    return "published";
}

export function mapCourseSummaryDtoToAdminCourse(course: CourseSummaryDto): AdminCourse {
    return {
        id: course.id,
        name: course.name,
        description: course.description || "",
        cover: image(course.imageUrl),
        difficulty: clampDifficulty(course.difficulty),
        category: course.type || "未分类",
        tags: course.tags || [],
        status: mapTeacherCourseStatus(course.status),
        studentCount: 0,
        experimentCount: 0,
        createTime: "",
        createdBy: course.createdBy ?? null,
        creatorEditable: course.creatorEditable ?? course.createdBy != null,
    };
}

export function mapModuleOverviewToAdminExperiment(module: ModuleOverViewType): AdminExperiment {
    return {
        id: module.id,
        name: module.name,
        description: module.description || "",
        difficulty: clampDifficulty(module.difficulty),
        courseId: module.courseId ?? undefined,
        courseIds: module.courseIds || [],
        courseName: module.type || "未分类模块",
        status: mapTeacherLabStatus(module.status),
        taskPoints: [],
        environment: {},
        studentCount: 0,
        completionRate: 0,
        averageScore: 0,
        createTime: "",
    };
}

function mapTeacherUserDtoToUser(user: TeacherUserListItemDto): User {
    return {
        userId: user.userId,
        userStudentNumber: user.userStudentNumber,
        userName: user.userName || "",
        userEmail: user.userEmail || undefined,
        userTel: user.userTel || undefined,
        userAcademy: user.userAcademy || undefined,
        userClass: user.userClass || undefined,
        userGender: user.userGender ?? undefined,
        classId: user.classId ?? undefined,
        createTime: user.createTime || undefined,
    };
}

export async function getTeacherUserList(): Promise<User[]> {
    const token = getStoredToken();
    if (!token) {
        throw new Error("当前没有登录态 token，无法请求教师端用户列表。");
    }

    const pageSize = 200;
    let page = 1;
    let total = Number.POSITIVE_INFINITY;
    const aggregatedUsers: User[] = [];

    while (aggregatedUsers.length < total) {
        const response = await axios.get<TeacherUserListResponse>(`${BASE_URL}/admin/users`, {
            params: {
                page,
                pageSize,
                status: "active",
            },
            headers: {
                Authorization: `Bearer ${token}`,
            },
        });

        const pageData = response.data.data;
        if (!pageData) {
            break;
        }

        aggregatedUsers.push(...(pageData.list || []).map(mapTeacherUserDtoToUser));
        total = Number(pageData.total ?? aggregatedUsers.length);

        const totalPages = Math.max(1, Math.ceil(total / pageSize));
        if (!pageData.list.length || page >= totalPages) {
            break;
        }

        page += 1;
    }

    return aggregatedUsers;
}

export interface AdminUserFilterOptions {
    academies: string[];
    classes: string[];
}

/** 管理后台的学院 / 班级筛选项，取自库里真实存在的学生数据。 */
export async function getTeacherUserFilterOptions(): Promise<AdminUserFilterOptions> {
    const response = await axios.get<Result<AdminUserFilterOptions>>(
        `${BASE_URL}/admin/user-filters`,
        getBearerAuthConfig("当前没有登录态 token，无法请求用户筛选项。"),
    );
    return {
        academies: response.data?.data?.academies ?? [],
        classes: response.data?.data?.classes ?? [],
    };
}

export async function getTeacherUserPage(
    page = 1,
    pageSize = 10,
    keyword?: string,
    academy?: string,
    className?: string,
    status?: string,
    gender?: string
): Promise<TeacherUserListPageDto> {
    const token = getStoredToken();
    if (!token) {
        throw new Error("当前没有登录态 token，无法请求教师端用户列表。");
    }

    const params: Record<string, any> = {
        page,
        pageSize,
    };
    if (keyword) params.keyword = keyword;
    if (academy) params.academy = academy;
    if (className) params.className = className;
    if (status) params.status = status;
    if (gender) params.gender = gender;

    const response = await axios.get<TeacherUserListResponse>(`${BASE_URL}/admin/users`, {
        params,
        headers: {
            Authorization: `Bearer ${token}`,
        },
    });

    if (!response.data.data) {
        throw new Error(response.data.message || "获取教师端用户分页数据失败");
    }

    return response.data.data;
}

export async function getCurrentUserProfile(token: string): Promise<User> {
    const response = await axios.get<Result<User>>(`${BASE_URL}/stu/profile`, {
        headers: {
            Authorization: `Bearer ${token}`,
        },
    });
    if (response.status !== 200) {
        throw new Error(`Unexpected response status: ${response.status}`);
    }

    const result = response.data;
    if (result.isSuccess !== 1 || !result.data) {
        throw new Error(result.message || "获取当前登录用户信息失败");
    }

    return result.data;
}

function getTeacherUserAuthConfig() {
    return getBearerAuthConfig("当前没有登录态 token，无法请求教师端用户管理接口。");
}

function getTeacherAgentAuthConfig() {
    return getBearerAuthConfig("当前没有登录态 token，无法请求教师端 AI 接口。");
}

function getTeacherCatalogAuthConfig() {
    return getBearerAuthConfig("当前没有登录态 token，无法请求课程实验管理接口。");
}

function getBearerAuthConfig(message: string) {
    const token = getStoredToken();
    if (!token) {
        throw new Error(message);
    }

    return {
        headers: {
            Authorization: `Bearer ${token}`,
        },
    };
}

function mapTeacherUserMutationPayload(payload: TeacherUserMutationPayload) {
    return {
        userStudentNumber: payload.userStudentNumber,
        userName: payload.userName,
        userAcademy: payload.userAcademy || null,
        userClass: payload.userClass || null,
        userEmail: payload.userEmail || null,
        userTel: payload.userTel || null,
        userGender: payload.userGender ?? null,
        classId: payload.classId ?? null,
    };
}

export async function createTeacherUser(payload: TeacherUserMutationPayload): Promise<User> {
    const response = await axios.post<Result<TeacherUserListItemDto>>(
        `${BASE_URL}/admin/users`,
        mapTeacherUserMutationPayload(payload),
        getTeacherUserAuthConfig(),
    );
    if (!response.data.data) {
        throw new Error(response.data.message || "创建用户失败");
    }
    return mapTeacherUserDtoToUser(response.data.data);
}

export async function updateTeacherUser(userId: number, payload: TeacherUserMutationPayload): Promise<User> {
    const response = await axios.put<Result<TeacherUserListItemDto>>(
        `${BASE_URL}/admin/users/${userId}`,
        mapTeacherUserMutationPayload(payload),
        getTeacherUserAuthConfig(),
    );
    if (!response.data.data) {
        throw new Error(response.data.message || "更新用户失败");
    }
    return mapTeacherUserDtoToUser(response.data.data);
}

export async function deleteTeacherUser(userId: number): Promise<void> {
    await axios.delete(`${BASE_URL}/admin/users/${userId}`, getTeacherUserAuthConfig());
}

export async function resetTeacherUserPassword(userId: number): Promise<void> {
    await axios.post(`${BASE_URL}/admin/users/${userId}/reset-password`, null, getTeacherUserAuthConfig());
}

export async function getTeacherCourseList(): Promise<AdminCourse[]> {
    const response = await getCourseList();
    return (response.data || []).map(mapCourseSummaryDtoToAdminCourse);
}

export async function getTeacherLabList(): Promise<AdminExperiment[]> {
    const response = await getModuleList();
    return (response.data || []).map(mapModuleOverviewToAdminExperiment);
}

function mapAdminCourseToMutationPayload(course: TeacherCourseMutationPayload) {
    return {
        courseName: course.name,
        courseDescription: course.description,
        difficulty: course.difficulty,
        imageUrl: course.cover || null,
        teacherName: course.teacherName || null,
        category: course.category,
        tags: course.tags,
        status: course.status,
    };
}

function mapAdminLabToMutationPayload(experiment: TeacherLabMutationPayload) {
    return {
        moduleName: experiment.name,
        moduleDescription: experiment.description,
        difficulty: experiment.difficulty,
        type: experiment.type || null,
        image: experiment.image || null,
    };
}

export async function getTeacherCourseDetail(id: number): Promise<AdminCourse> {
    const response = await axios.get<Result<CourseSummaryDto>>(`${EXPERIMENT_MODULE_BASE_URL}/course/${id}`);
    if (!response.data.data) {
        throw new Error(response.data.message || '课程详情不存在');
    }
    return mapCourseSummaryDtoToAdminCourse(response.data.data);
}

export async function createTeacherCourse(payload: TeacherCourseMutationPayload): Promise<AdminCourse> {
    const response = await axios.post<Result<CourseSummaryDto>>(
        `${EXPERIMENT_MODULE_BASE_URL}/course`,
        mapAdminCourseToMutationPayload(payload),
        getTeacherCatalogAuthConfig(),
    );
    if (!response.data.data) {
        throw new Error(response.data.message || '课程创建失败');
    }
    return mapCourseSummaryDtoToAdminCourse(response.data.data);
}

export async function updateTeacherCourse(id: number, payload: TeacherCourseMutationPayload): Promise<AdminCourse> {
    const response = await axios.put<Result<CourseSummaryDto>>(
        `${EXPERIMENT_MODULE_BASE_URL}/course/${id}`,
        mapAdminCourseToMutationPayload(payload),
        getTeacherCatalogAuthConfig(),
    );
    if (!response.data.data) {
        throw new Error(response.data.message || '课程更新失败');
    }
    return mapCourseSummaryDtoToAdminCourse(response.data.data);
}

export async function deleteTeacherCourse(id: number): Promise<void> {
    await axios.delete(`${EXPERIMENT_MODULE_BASE_URL}/course/${id}`, getTeacherCatalogAuthConfig());
}

export async function createTeacherLab(payload: TeacherLabMutationPayload): Promise<AdminExperiment> {
    const response = await axios.post<Result<ModuleOverViewType>>(
        `${EXPERIMENT_MODULE_BASE_URL}/stu/module`,
        mapAdminLabToMutationPayload(payload),
        getTeacherCatalogAuthConfig(),
    );
    if (!response.data.data) {
        throw new Error(response.data.message || '实验创建失败');
    }
    return mapModuleOverviewToAdminExperiment(response.data.data);
}

export async function updateTeacherLab(id: number, payload: TeacherLabMutationPayload): Promise<AdminExperiment> {
    const response = await axios.put<Result<ModuleOverViewType>>(
        `${EXPERIMENT_MODULE_BASE_URL}/stu/module/${id}`,
        mapAdminLabToMutationPayload(payload),
        getTeacherCatalogAuthConfig(),
    );
    if (!response.data.data) {
        throw new Error(response.data.message || '实验更新失败');
    }
    return mapModuleOverviewToAdminExperiment(response.data.data);
}

export async function deleteTeacherLab(id: number): Promise<void> {
    await axios.delete(`${EXPERIMENT_MODULE_BASE_URL}/stu/module/${id}`, getTeacherCatalogAuthConfig());
}

export async function getCourseModules(courseId: number): Promise<AdminExperiment[]> {
    const response = await axios.get<Result<ModuleOverViewType[]>>(
        `${EXPERIMENT_MODULE_BASE_URL}/course/${courseId}/modules`,
    );
    return (response.data.data || []).map(mapModuleOverviewToAdminExperiment);
}

export async function addCourseModule(courseId: number, moduleId: number): Promise<AdminExperiment[]> {
    const response = await axios.post<Result<ModuleOverViewType[]>>(
        `${EXPERIMENT_MODULE_BASE_URL}/course/${courseId}/modules/${moduleId}`,
        null,
        getTeacherCatalogAuthConfig(),
    );
    return (response.data.data || []).map(mapModuleOverviewToAdminExperiment);
}

export async function removeCourseModule(courseId: number, moduleId: number): Promise<AdminExperiment[]> {
    const response = await axios.delete<Result<ModuleOverViewType[]>>(
        `${EXPERIMENT_MODULE_BASE_URL}/course/${courseId}/modules/${moduleId}`,
        getTeacherCatalogAuthConfig(),
    );
    return (response.data.data || []).map(mapModuleOverviewToAdminExperiment);
}

export async function getClassProfileLatest(classId: number): Promise<ClassProfileLatestDto> {
    const response = await axios.get(`${AGENT_BASE_URL}/api/class-profile/${classId}/latest`);
    return response.data;
}

export async function getClassProfileStudents(classId: number): Promise<ClassProfileStudentsResponse> {
    const response = await axios.get(`${AGENT_BASE_URL}/api/class-profile/${classId}/students`);
    return response.data;
}

export async function getScoreboard(limit = 50): Promise<ScoreboardResponseDto> {
    const response = await axios.get(`${AGENT_BASE_URL}/api/scoreboard`, {
        params: { limit },
    });
    return response.data;
}

export async function getTeacherDashboard(_teacherId?: number | null): Promise<TeacherDashboardResponseDto> {
    const response = await axios.get(`${AGENT_BASE_URL}/api/teacher/dashboard`, {
        ...getTeacherAgentAuthConfig(),
    });
    return response.data;
}

export async function getTeacherClasses(_teacherId?: number | null): Promise<TeacherClassesResponseDto> {
    const response = await axios.get(`${AGENT_BASE_URL}/api/teacher/classes`, {
        ...getTeacherAgentAuthConfig(),
    });
    return response.data;
}

export async function getTeacherClassStudents(classId: number): Promise<TeacherClassStudentsResponseDto> {
    const response = await axios.get(
        `${AGENT_BASE_URL}/api/teacher/classes/${classId}/students`,
        getTeacherAgentAuthConfig(),
    );
    return response.data;
}

export async function getTeacherClassAiAnalysis(classId: number): Promise<TeacherClassAiAnalysisDto> {
    const response = await axios.post(
        `${AGENT_BASE_URL}/api/teacher/classes/${classId}/ai-analysis`,
        null,
        getTeacherAgentAuthConfig(),
    );
    return response.data;
}

export async function getTeacherStudentProfile(userId: number): Promise<TeacherStudentProfileResponseDto> {
    const response = await axios.get(
        `${AGENT_BASE_URL}/api/teacher/students/${userId}/profile`,
        getTeacherAgentAuthConfig(),
    );
    return response.data;
}

export async function getTeacherStudentAiAnalysis(userId: number): Promise<TeacherStudentAiAnalysisDto> {
    const response = await axios.post(
        `${AGENT_BASE_URL}/api/teacher/students/${userId}/profile/ai-analysis`,
        null,
        getTeacherAgentAuthConfig(),
    );
    return response.data;
}

export async function getTeacherGeneratedQuestions(
    params: { teacherId?: number | null; status?: string; page?: number; size?: number } = {},
): Promise<TeacherGeneratedQuestionsResponseDto> {
    const { teacherId: _ignoredTeacherId, ...trustedParams } = params;
    const response = await axios.get(`${AGENT_BASE_URL}/api/teacher/generated-questions`, {
        params: trustedParams,
        ...getTeacherAgentAuthConfig(),
    });
    return response.data;
}

function unwrapTeacherResult<T>(result: Result<T>, fallback: string): T {
    const succeeded = result.isSuccess === 1
        || (result.isSuccess === undefined && result.status >= 200 && result.status < 300);
    if (!succeeded || result.data === undefined || result.data === null) {
        throw new Error(result.message || fallback);
    }
    return result.data;
}

export async function getTeachingClasses(): Promise<TeachingClassDto[]> {
    const response = await axios.get<Result<TeachingClassDto[]>>(
        `${BASE_URL}/api/teacher/teaching-classes`,
        getTeacherUserAuthConfig(),
    );
    return unwrapTeacherResult(response.data, "教学班列表加载失败");
}

export async function getTeachingClass(teachingClassId: number): Promise<TeachingClassDto> {
    const response = await axios.get<Result<TeachingClassDto>>(
        `${BASE_URL}/api/teacher/teaching-classes/${teachingClassId}`,
        getTeacherUserAuthConfig(),
    );
    return unwrapTeacherResult(response.data, "教学班信息加载失败");
}

export async function createTeachingClass(payload: TeachingClassSavePayload): Promise<TeachingClassDto> {
    const response = await axios.post<Result<TeachingClassDto>>(
        `${BASE_URL}/api/teacher/teaching-classes`, payload, getTeacherUserAuthConfig(),
    );
    return unwrapTeacherResult(response.data, "教学班创建失败");
}

export async function updateTeachingClass(
    teachingClassId: number,
    payload: TeachingClassSavePayload,
): Promise<TeachingClassDto> {
    const response = await axios.put<Result<TeachingClassDto>>(
        `${BASE_URL}/api/teacher/teaching-classes/${teachingClassId}`, payload, getTeacherUserAuthConfig(),
    );
    return unwrapTeacherResult(response.data, "教学班保存失败");
}

export interface TeachingClassDeleteResultDto {
    deletedStudentCount: number;
    keptStudentCount: number;
}

/** 删除教学班：名单、课程安排、教师分析记录，以及只属于本班的学生账号都会被清除，不可恢复。 */
export async function deleteTeachingClass(teachingClassId: number): Promise<TeachingClassDeleteResultDto> {
    const response = await axios.delete<Result<TeachingClassDeleteResultDto>>(
        `${BASE_URL}/api/teacher/teaching-classes/${teachingClassId}`,
        getTeacherUserAuthConfig(),
    );
    return unwrapTeacherResult(response.data, "教学班删除失败");
}

export async function getTeachingClassStudents(teachingClassId: number): Promise<TeachingClassStudentDto[]> {
    const response = await axios.get<Result<TeachingClassStudentDto[]>>(
        `${BASE_URL}/api/teacher/teaching-classes/${teachingClassId}/students`,
        getTeacherUserAuthConfig(),
    );
    return unwrapTeacherResult(response.data, "学生名单加载失败");
}

export async function previewTeachingClassImport(
    teachingClassId: number,
    file: File,
): Promise<TeachingClassImportPreviewDto> {
    const form = new FormData();
    form.append("file", file);
    const response = await axios.post<Result<TeachingClassImportPreviewDto>>(
        `${BASE_URL}/api/teacher/teaching-classes/${teachingClassId}/students/import/preview`,
        form,
        getTeacherUserAuthConfig(),
    );
    return unwrapTeacherResult(response.data, "名单校验失败");
}

export async function confirmTeachingClassImport(
    teachingClassId: number,
    batchId: string,
): Promise<TeachingClassImportResultDto> {
    const response = await axios.post<Result<TeachingClassImportResultDto>>(
        `${BASE_URL}/api/teacher/teaching-classes/${teachingClassId}/students/import/${batchId}/confirm`,
        null,
        getTeacherUserAuthConfig(),
    );
    return unwrapTeacherResult(response.data, "名单导入失败");
}

export async function removeTeachingClassStudent(teachingClassId: number, studentId: number): Promise<void> {
    await axios.delete(
        `${BASE_URL}/api/teacher/teaching-classes/${teachingClassId}/students/${studentId}`,
        getTeacherUserAuthConfig(),
    );
}

export async function getTeachingClassCourses(teachingClassId: number): Promise<TeachingClassCourseDto[]> {
    const response = await axios.get<Result<TeachingClassCourseDto[]>>(
        `${BASE_URL}/api/teacher/teaching-classes/${teachingClassId}/courses`,
        getTeacherUserAuthConfig(),
    );
    return unwrapTeacherResult(response.data, "教学安排加载失败");
}

export async function replaceTeachingClassCourses(
    teachingClassId: number,
    items: Array<{ courseId: number; teachingOrder: number; plannedStartDate?: string | null; plannedEndDate?: string | null }>,
): Promise<TeachingClassCourseDto[]> {
    const response = await axios.put<Result<TeachingClassCourseDto[]>>(
        `${BASE_URL}/api/teacher/teaching-classes/${teachingClassId}/courses`,
        { items },
        getTeacherUserAuthConfig(),
    );
    return unwrapTeacherResult(response.data, "教学安排保存失败");
}

export async function updateTeachingClassCourseContent(
    teachingClassId: number,
    courseId: number,
    teachingContent: string | null,
): Promise<TeachingClassCourseDto> {
    const response = await axios.patch<Result<TeachingClassCourseDto>>(
        `${BASE_URL}/api/teacher/teaching-classes/${teachingClassId}/courses/${courseId}/content`,
        { teachingContent },
        getTeacherUserAuthConfig(),
    );
    return unwrapTeacherResult(response.data, "教学内容保存失败");
}

export async function getTeacherGeneratedQuestionRecords(params: {
    teachingClassId?: number;
    courseId?: number;
    knowledgePointId?: number;
    studentId?: number;
    answerResult?: "correct" | "incorrect" | "attempted" | "unanswered" | "";
    typicalOnly?: boolean;
    dateFrom?: string;
    dateTo?: string;
    page?: number;
    size?: number;
} = {}): Promise<TeacherGeneratedQuestionPage> {
    const response = await axios.get<TeacherGeneratedQuestionPage>(`${AGENT_BASE_URL}/api/teacher/generated-questions`, {
        params,
        ...getTeacherAgentAuthConfig(),
    });
    return response.data;
}

export async function setGeneratedQuestionTypical(generatedQuestionId: string, typical: boolean): Promise<void> {
    const url = `${AGENT_BASE_URL}/api/teacher/generated-questions/${encodeURIComponent(generatedQuestionId)}/typical`;
    if (typical) await axios.put(url, null, getTeacherAgentAuthConfig());
    else await axios.delete(url, getTeacherAgentAuthConfig());
}

export async function getGeneratedQuestionSummary(teachingClassId: number): Promise<TeacherGeneratedQuestionSummary> {
    const response = await axios.get<TeacherGeneratedQuestionSummary>(
        `${AGENT_BASE_URL}/api/teacher/teaching-classes/${teachingClassId}/generated-question-summary`,
        getTeacherAgentAuthConfig(),
    );
    return response.data;
}

export async function getTeacherClassCourseQuestions(
    teachingClassId: number,
    courseId: number,
): Promise<TeacherCourseQuestionsDto> {
    const response = await axios.get<TeacherCourseQuestionsDto>(
        `${AGENT_BASE_URL}/api/teacher/teaching-classes/${teachingClassId}/courses/${courseId}/questions`,
        getTeacherAgentAuthConfig(),
    );
    return response.data;
}

export async function getTeacherStudentCourseQuestions(
    teachingClassId: number,
    courseId: number,
    studentId: number,
): Promise<TeacherCourseQuestionsDto> {
    const response = await axios.get<TeacherCourseQuestionsDto>(
        `${AGENT_BASE_URL}/api/teacher/teaching-classes/${teachingClassId}/courses/${courseId}/students/${studentId}/questions`,
        getTeacherAgentAuthConfig(),
    );
    return response.data;
}

export async function getTeacherCourseAnalysis(
    teachingClassId: number,
    courseId: number,
    studentId?: number | null,
): Promise<TeacherCourseAnalysisDto> {
    const suffix = studentId ? `/students/${studentId}` : '';
    const response = await axios.get<TeacherCourseAnalysisDto>(
        `${AGENT_BASE_URL}/api/teacher/teaching-classes/${teachingClassId}/courses/${courseId}${suffix}/ai-analysis`,
        getTeacherAgentAuthConfig(),
    );
    return response.data;
}

export async function startTeacherCourseAnalysis(
    teachingClassId: number,
    courseId: number,
    studentId?: number | null,
): Promise<TeacherCourseAnalysisDto> {
    const suffix = studentId ? `/students/${studentId}` : '';
    const response = await axios.post<TeacherCourseAnalysisDto>(
        `${AGENT_BASE_URL}/api/teacher/teaching-classes/${teachingClassId}/courses/${courseId}${suffix}/ai-analysis`,
        null,
        getTeacherAgentAuthConfig(),
    );
    return response.data;
}

export async function getTeachingClassAnalysis(teachingClassId: number): Promise<TeachingClassAnalysisDto> {
    const response = await axios.get<TeachingClassAnalysisDto>(
        `${AGENT_BASE_URL}/api/teacher/teaching-classes/${teachingClassId}/ai-analysis`,
        getTeacherAgentAuthConfig(),
    );
    return response.data;
}

export async function startTeachingClassAnalysis(teachingClassId: number): Promise<TeachingClassAnalysisDto> {
    const response = await axios.post<TeachingClassAnalysisDto>(
        `${AGENT_BASE_URL}/api/teacher/teaching-classes/${teachingClassId}/ai-analysis`,
        null,
        getTeacherAgentAuthConfig(),
    );
    return response.data;
}

export async function getTeachingClassStudentProfile(
    teachingClassId: number,
    studentId: number,
): Promise<TeacherStudentProfileResponseDto> {
    const response = await axios.get<TeacherStudentProfileResponseDto>(
        `${AGENT_BASE_URL}/api/teacher/teaching-classes/${teachingClassId}/students/${studentId}/profile`,
        getTeacherAgentAuthConfig(),
    );
    return response.data;
}

export async function getTeachingClassStudentAnalysis(
    teachingClassId: number,
    studentId: number,
): Promise<TeachingStudentAnalysisDto> {
    const response = await axios.get<TeachingStudentAnalysisDto>(
        `${AGENT_BASE_URL}/api/teacher/teaching-classes/${teachingClassId}/students/${studentId}/ai-analysis`,
        getTeacherAgentAuthConfig(),
    );
    return response.data;
}

export async function startTeachingClassStudentAnalysis(
    teachingClassId: number,
    studentId: number,
): Promise<TeachingStudentAnalysisDto> {
    const response = await axios.post<TeachingStudentAnalysisDto>(
        `${AGENT_BASE_URL}/api/teacher/teaching-classes/${teachingClassId}/students/${studentId}/ai-analysis`,
        null,
        getTeacherAgentAuthConfig(),
    );
    return response.data;
}

export async function getAiAnalysisHealth(): Promise<AiAnalysisHealthDto> {
    const response = await axios.get<AiAnalysisHealthDto>(`${AGENT_BASE_URL}/health/ai-analysis`);
    return response.data;
}

export async function rebuildTeachingClassProfiles(teachingClassId: number): Promise<{
    teachingClassId: number;
    studentCount: number;
    rebuiltCount: number;
    failedCount: number;
    failures: Array<{ studentId: number; message: string }>;
}> {
    const response = await axios.post(
        `${AGENT_BASE_URL}/api/teacher/teaching-classes/${teachingClassId}/profiles/rebuild`,
        null,
        getTeacherAgentAuthConfig(),
    );
    return response.data;
}

export async function getTeachingClassStudentCapabilityEvidence(
    teachingClassId: number,
    studentId: number,
): Promise<CapabilityEvidenceResponseDto> {
    const response = await axios.get<CapabilityEvidenceResponseDto>(
        `${AGENT_BASE_URL}/api/teacher/teaching-classes/${teachingClassId}/students/${studentId}/capability-evidence`,
        getTeacherAgentAuthConfig(),
    );
    return response.data;
}

export async function getTeachingClassStudentCapabilityGrowth(
    teachingClassId: number,
    studentId: number,
): Promise<CapabilityGrowthResponseDto> {
    const response = await axios.get<CapabilityGrowthResponseDto>(
        `${AGENT_BASE_URL}/api/teacher/teaching-classes/${teachingClassId}/students/${studentId}/capability-growth`,
        getTeacherAgentAuthConfig(),
    );
    return response.data;
}

export async function getTeachingClassStudentLearningReplay(
    teachingClassId: number,
    studentId: number,
    limit = 100,
): Promise<LearningReplayResponseDto> {
    const response = await axios.get<LearningReplayResponseDto>(
        `${AGENT_BASE_URL}/api/teacher/teaching-classes/${teachingClassId}/students/${studentId}/learning-replay`,
        { params: { limit }, ...getTeacherAgentAuthConfig() },
    );
    return response.data;
}

export async function getTeachingClassRiskMap(
    teachingClassId: number,
): Promise<KnowledgeRiskMapResponseDto> {
    const response = await axios.get<KnowledgeRiskMapResponseDto>(
        `${AGENT_BASE_URL}/api/teacher/teaching-classes/${teachingClassId}/risk-map`,
        getTeacherAgentAuthConfig(),
    );
    return response.data;
}

export async function getTeachingClassExperimentRiskMap(
    teachingClassId: number,
    courseId: number,
): Promise<KnowledgeRiskMapResponseDto> {
    const response = await axios.get<KnowledgeRiskMapResponseDto>(
        `${AGENT_BASE_URL}/api/teacher/teaching-classes/${teachingClassId}/experiments/${courseId}/knowledge-risks`,
        getTeacherAgentAuthConfig(),
    );
    return response.data;
}

export async function getTeachingClassKnowledgeRiskDetail(
    teachingClassId: number,
    courseId: number,
    knowledgePointId: number,
    page = 1,
    size = 20,
): Promise<KnowledgeRiskDetailDto> {
    const response = await axios.get<KnowledgeRiskDetailDto>(
        `${AGENT_BASE_URL}/api/teacher/teaching-classes/${teachingClassId}/experiments/${courseId}/knowledge-risks/${knowledgePointId}`,
        { params: { page, size }, ...getTeacherAgentAuthConfig() },
    );
    return response.data;
}

export async function getKnowledgePointAiAnalysis(
    teachingClassId: number,
    courseId: number,
    knowledgePointId: number,
): Promise<KnowledgeAiAnalysisDto> {
    const response = await axios.get<KnowledgeAiAnalysisDto>(
        `${AGENT_BASE_URL}/api/teacher/teaching-classes/${teachingClassId}/experiments/${courseId}/knowledge-points/${knowledgePointId}/ai-analysis`,
        getTeacherAgentAuthConfig(),
    );
    return response.data;
}

export async function startKnowledgePointAiAnalysis(
    teachingClassId: number,
    courseId: number,
    knowledgePointId: number,
): Promise<KnowledgeAiAnalysisDto> {
    const response = await axios.post<KnowledgeAiAnalysisDto>(
        `${AGENT_BASE_URL}/api/teacher/teaching-classes/${teachingClassId}/experiments/${courseId}/knowledge-points/${knowledgePointId}/ai-analysis`,
        null,
        getTeacherAgentAuthConfig(),
    );
    return response.data;
}

export async function updateKnowledgeExercise(
    teachingClassId: number,
    exerciseId: number,
    payload: Partial<Pick<KnowledgeExerciseDto, "questionType" | "stem" | "options" | "standardAnswer" | "explanation" | "difficulty" | "generationRationale">>,
): Promise<KnowledgeExerciseDto> {
    const response = await axios.patch<KnowledgeExerciseDto>(
        `${AGENT_BASE_URL}/api/teacher/teaching-classes/${teachingClassId}/knowledge-exercises/${exerciseId}`,
        payload,
        getTeacherAgentAuthConfig(),
    );
    return response.data;
}

export async function reviewKnowledgeExercise(
    teachingClassId: number,
    exerciseId: number,
    status: Exclude<KnowledgeExerciseReviewStatus, "PENDING_REVIEW">,
    comment = "",
): Promise<KnowledgeExerciseDto> {
    const response = await axios.post<KnowledgeExerciseDto>(
        `${AGENT_BASE_URL}/api/teacher/teaching-classes/${teachingClassId}/knowledge-exercises/${exerciseId}/review`,
        { status, comment },
        getTeacherAgentAuthConfig(),
    );
    return response.data;
}

export async function regenerateKnowledgeExercise(
    teachingClassId: number,
    exerciseId: number,
): Promise<KnowledgeExerciseDto> {
    const response = await axios.post<KnowledgeExerciseDto>(
        `${AGENT_BASE_URL}/api/teacher/teaching-classes/${teachingClassId}/knowledge-exercises/${exerciseId}/regenerate`,
        null,
        getTeacherAgentAuthConfig(),
    );
    return response.data;
}

export async function getTeachingClassInterventions(
    teachingClassId: number,
): Promise<{ teachingClassId: number; items: TeacherInterventionDto[] }> {
    const response = await axios.get(
        `${AGENT_BASE_URL}/api/teacher/teaching-classes/${teachingClassId}/interventions`,
        getTeacherAgentAuthConfig(),
    );
    return response.data;
}

export async function createTeachingClassIntervention(
    teachingClassId: number,
    payload: {
        title: string;
        actionType: TeacherInterventionActionType;
        studentIds: number[];
        courseId?: number | null;
        knowledgePointId?: number | null;
        description?: string;
        questionIds?: string[];
        approvedExerciseIds?: number[];
        dueAt?: string | null;
    },
): Promise<TeacherInterventionDto> {
    const response = await axios.post<TeacherInterventionDto>(
        `${AGENT_BASE_URL}/api/teacher/teaching-classes/${teachingClassId}/interventions`,
        payload,
        getTeacherAgentAuthConfig(),
    );
    return response.data;
}

export async function refreshTeachingClassIntervention(
    teachingClassId: number,
    interventionId: number,
): Promise<TeacherInterventionDto> {
    const response = await axios.post<TeacherInterventionDto>(
        `${AGENT_BASE_URL}/api/teacher/teaching-classes/${teachingClassId}/interventions/${interventionId}/refresh`,
        null,
        getTeacherAgentAuthConfig(),
    );
    return response.data;
}

export async function updateTeachingClassInterventionStatus(
    teachingClassId: number,
    interventionId: number,
    status: "ACTIVE" | "COMPLETED" | "CANCELLED",
): Promise<TeacherInterventionDto> {
    const response = await axios.patch<TeacherInterventionDto>(
        `${AGENT_BASE_URL}/api/teacher/teaching-classes/${teachingClassId}/interventions/${interventionId}`,
        { status },
        getTeacherAgentAuthConfig(),
    );
    return response.data;
}

export async function getStudentTeacherAssignments(
    studentId: number,
): Promise<{ studentId: number; items: StudentTeacherAssignmentDto[] }> {
    const response = await axios.get(
        `${AGENT_BASE_URL}/api/students/${studentId}/teacher-assignments`,
        getBearerAuthConfig("当前没有登录态 token，无法读取教师布置任务。"),
    );
    return response.data;
}

export async function getStudentCapabilityGrowth(
    studentId: number,
    teachingClassId?: number,
): Promise<CapabilityGrowthResponseDto> {
    const response = await axios.get<CapabilityGrowthResponseDto>(
        `${AGENT_BASE_URL}/api/students/${studentId}/capability-growth`,
        {
            params: teachingClassId == null ? undefined : { teachingClassId },
            ...getBearerAuthConfig("当前没有登录态 token，无法读取能力成长数据。"),
        },
    );
    return response.data;
}

export async function startStudentTeacherAssignment(
    studentId: number,
    interventionId: number,
): Promise<StudentTeacherAssignmentDto & { startedNow: boolean; generation?: TrainingQuestionSetResponse | null }> {
    const response = await axios.post(
        `${AGENT_BASE_URL}/api/students/${studentId}/teacher-assignments/${interventionId}/start`,
        null,
        getBearerAuthConfig("当前没有登录态 token，无法开始教师布置任务。"),
    );
    return response.data;
}

export async function getRecentLabEvents(limit = 20): Promise<LabEventsResponse> {
    const response = await axios.get(`${AGENT_BASE_URL}/api/lab/events`, {
        params: { limit },
    });
    return response.data;
}

export async function getCourseDetail(id:number): Promise<Result<Course>> {
    try {
        const response = await axios.get(`${BASE_URL}/course/detail?id=${id}`);
        if (response.status === 200) {
            return response.data;
        } else {
            console.error(`Unexpected response status: ${response.status}`);
            return getFallbackCourseDetail(id);
        }
    } catch (error) {
        console.error('Error fetching course detail:', error);
        return getFallbackCourseDetail(id);
    }
}

// 提供硬编码的备用课程数据
function getFallbackCourseDetail(id: number): Result<Course> {
    // 使用SQL文件中的课程数据作为备用
    const fallbackCourses = [
        {
            id: 1,
            name: "SQL注入攻击",
            description: "本课程详细讲解SQL注入攻击的原理、分类和防御技术。通过实际案例讲解如何发现和利用SQL注入漏洞，以及如何通过参数化查询、输入验证和最小权限原则等方法防止SQL注入攻击，保障Web应用的数据安全。",
            difficulty: 3,
            imageUrl: "a9fe8e50-ba21-45ef-abd5-50b717857502-1.SQL注入攻防实战.png",
            instructor: "张教授",
            costTime: 8,
            schedule: "每周一",
            status: CourseStatus.ACTIVE,
            tags: ["SQL注入", "Web安全", "数据库安全"],
            type: "web",
            modules: []
        },
        {
            id: 2,
            name: "XSS与CSRF攻击",
            description: "本课程深入剖析跨站脚本(XSS)和跨站请求伪造(CSRF)攻击的原理和防御方法。通过实例讲解反射型XSS、存储型XSS和DOM型XSS攻击，以及CSRF攻击的实施过程，帮助学习者掌握Web前端安全防护的关键技术。",
            difficulty: 2,
            imageUrl: "eb678908-4878-4303-94ae-b3434d52612a-2.XSS漏洞深度解析.png",
            instructor: "李教授",
            costTime: 6,
            schedule: "每周二",
            status: CourseStatus.ACTIVE,
            tags: ["XSS", "CSRF", "Web安全"],
            type: "web",
            modules: []
        },
        {
            id: 3,
            name: "IDS和IPS系统",
            description: "本课程介绍入侵检测系统(IDS)和入侵防御系统(IPS)的工作原理和部署策略。通过分析网络流量和系统行为，识别和防御各类网络攻击，包括异常检测、特征匹配和行为分析等技术，帮助学习者构建有效的网络安全防护体系。",
            difficulty: 3,
            imageUrl: "5780e906-42a1-4a88-ad06-d054bbf92735-3.文件上传漏洞突破.png",
            instructor: "王教授",
            costTime: 7,
            schedule: "每周三",
            status: CourseStatus.ACTIVE,
            tags: ["IDS", "IPS", "网络安全"],
            type: "network",
            modules: []
        },
        {
            id: 4,
            name: "APT攻击分析",
            description: "本课程深入分析高级持续性威胁(APT)攻击的特点和防御策略。通过实际APT攻击案例分析，介绍攻击者的战术、技术和程序(TTP)，以及如何建立有效的威胁情报和安全防御体系，提升组织抵御高级威胁的能力。",
            difficulty: 4,
            imageUrl: "4.中间件漏洞利用.png",
            instructor: "赵教授",
            costTime: 10,
            schedule: "每周四",
            status: CourseStatus.ACTIVE,
            tags: ["APT", "高级威胁", "网络安全"],
            type: "advanced",
            modules: []
        },
        {
            id: 5,
            name: "防火墙技术",
            description: "本课程详细讲解网络防火墙的原理、类型和配置方法。包括包过滤防火墙、状态检测防火墙、应用层防火墙和下一代防火墙的特点与部署策略，以及访问控制列表(ACL)、NAT配置、VPN集成等实用技术，帮助学习者掌握网络边界防护的核心技能。",
            difficulty: 3,
            imageUrl: "5.组件漏洞挖掘.png",
            instructor: "钱教授",
            costTime: 8,
            schedule: "每周五",
            status: CourseStatus.ACTIVE,
            tags: ["防火墙", "网络安全", "边界防护"],
            type: "network",
            modules: []
        },
        {
            id: 6,
            name: "古典密码学",
            description: "本课程介绍密码学的历史发展和古典密码体系，包括替换密码、置换密码、维吉尼亚密码等经典加密方法的原理与分析。通过历史案例和实际操作，了解密码破译的基本方法和密码学的基本概念，为现代密码学学习奠定基础。",
            difficulty: 2,
            imageUrl: "6.框架漏洞利用.png",
            instructor: "孙教授",
            costTime: 6,
            schedule: "每周一",
            status: CourseStatus.ACTIVE,
            tags: ["密码学", "古典密码", "信息安全"],
            type: "crypto",
            modules: []
        },
        {
            id: 7,
            name: "公钥密码简介",
            description: "本课程详细讲解公钥密码体系的基本原理和应用场景。介绍非对称加密的数学基础、密钥管理、数字证书和PKI体系，以及RSA、ECC等常用公钥算法的工作机制，帮助学习者理解现代密码学中最重要的概念和技术。",
            difficulty: 3,
            imageUrl: "7.业务逻辑漏洞实战.png",
            instructor: "周教授",
            costTime: 8,
            schedule: "每周二",
            status: CourseStatus.ACTIVE,
            tags: ["公钥密码", "非对称加密", "密码学"],
            type: "crypto",
            modules: []
        },
        {
            id: 8,
            name: "RSA公钥加密方案",
            description: "本课程深入剖析RSA公钥加密算法的数学原理、实现细节和安全性分析。包括素数生成、密钥生成、加密解密过程、数字签名应用，以及常见攻击方法和防御措施，帮助学习者全面掌握这一最广泛使用的公钥密码系统。",
            difficulty: 4,
            imageUrl: "8.内网渗透技术.png",
            instructor: "吴教授",
            costTime: 9,
            schedule: "每周三",
            status: CourseStatus.ACTIVE,
            tags: ["RSA", "公钥密码", "密码学"],
            type: "crypto",
            modules: []
        },
        {
            id: 9,
            name: "数字签名技术",
            description: "本课程详细介绍数字签名的原理、算法和应用。包括RSA签名、DSA、ECDSA等签名算法的工作机制，数字证书与PKI体系，以及时间戳、盲签名等高级签名技术，帮助学习者理解数字签名在信息安全中的重要作用和实现方法。",
            difficulty: 4,
            imageUrl: "9.代码审计进阶.png",
            instructor: "郑教授",
            costTime: 8,
            schedule: "每周四",
            status: CourseStatus.ACTIVE,
            tags: ["数字签名", "PKI", "密码学"],
            type: "crypto",
            modules: []
        },
        {
            id: 10,
            name: "操作系统安全概述",
            description: "本课程全面介绍操作系统安全的核心概念和防护技术。包括访问控制、权限管理、认证机制、内核安全、内存保护等基础安全机制，以及常见操作系统的安全配置和加固方法，帮助学习者建立系统安全的整体认识。",
            difficulty: 3,
            imageUrl: "10.CTF攻防实战.png",
            instructor: "王教授",
            costTime: 7,
            schedule: "每周五",
            status: CourseStatus.ACTIVE,
            tags: ["操作系统安全", "系统安全", "访问控制"],
            type: "system",
            modules: []
        },
        {
            id: 11,
            name: "可信计算技术",
            description: "本课程深入讲解可信计算的基本原理和关键技术。包括可信平台模块(TPM)、可信启动、远程证明、密封存储等可信计算机制，以及可信计算在云计算、物联网等领域的应用，帮助学习者理解构建可信系统的方法和挑战。",
            difficulty: 4,
            imageUrl: "11.红队武器库.png",
            instructor: "李教授",
            costTime: 9,
            schedule: "每周一",
            status: CourseStatus.ACTIVE,
            tags: ["可信计算", "系统安全", "TPM"],
            type: "system",
            modules: []
        },
        {
            id: 12,
            name: "网络安全概述",
            description: "本课程全面介绍网络安全的基本概念、威胁类型和防护策略。包括网络攻击分类、网络协议安全、边界防护、入侵检测与防御、安全运维等核心内容，帮助学习者建立网络安全的整体认识和防护思路。",
            difficulty: 3,
            imageUrl: "12.漏洞挖掘方法论.png",
            instructor: "张教授",
            costTime: 8,
            schedule: "每周二",
            status: CourseStatus.ACTIVE,
            tags: ["网络安全", "安全架构", "威胁防护"],
            type: "network",
            modules: []
        }
    ];
    
    // 查找请求的ID，如果找不到则返回第一个课程
    const course = fallbackCourses.find(c => c.id === id) || fallbackCourses[0];
    
    return {
        isSuccess: 1,
        status: 200,
        message: "success",
        data: course as Course
    };
}

export async function getModuleDetail(id:number): Promise<Result<Module>> {
    try {
        const response = await axios.get(`${BASE_URL}/course/module/detail?id=${id}`);
        if (response.status === 200) {
            return response.data;
        } else {
            console.error(`Unexpected response status: ${response.status}`);
            return getFallbackModuleDetail(id);
        }
    } catch (error) {
        console.error('Error fetching module detail:', error);
        return getFallbackModuleDetail(id);
    }
}   

// 提供硬编码的备用模块数据
function getFallbackModuleDetail(id: number): Result<Module> {
    // 尝试从我们的备用数据中查找对应ID的实验
    const experiment = findExperimentById(Number(id));
    
    if (experiment) {
        // 确保experiment的结构符合Module接口
        const moduleData = {
            id: experiment.id,
            name: experiment.name,
            introduction: experiment.introduction,
            difficulty: experiment.difficulty,
            taskPoints: experiment.taskPoints.map(task => ({
                ...task,
                questions: task.questions || []
            })),
            targetMachine: experiment.targetMachine
        };
        
        return {
            isSuccess: 1,
            status: 200,
            message: "success",
            data: moduleData as any
        };
    } else {
        // 如果找不到对应ID的实验，返回默认的SQL注入实验（ID为1）
        const defaultExperiment = findExperimentById(1);
        const moduleData = {
            id: id, // 使用请求的ID
            name: defaultExperiment?.name || "SQL注入基础实验",
            introduction: defaultExperiment?.introduction || "SQL注入基础实验介绍",
            difficulty: defaultExperiment?.difficulty || 3,
            taskPoints: (defaultExperiment?.taskPoints || []).map(task => ({
                ...task,
                questions: task.questions || []
            })),
            targetMachine: defaultExperiment?.targetMachine || { id: "default-machine" }
        };
        
        return {
            isSuccess: 1,
            status: 200,
            message: "success",
            data: moduleData as any
        };
    }
}
