import { createRouter, createWebHashHistory } from "vue-router";
// 路由组件统一改为动态 import：首屏只加载当前路由 chunk，避免把 Admin/Teacher/Module 全量打进主包
const UserLayout = () => import("../layout/User/index.vue");
const AdminLayout = () => import("../layout/Admin/index.vue");
const Courses = () => import("../pages/User/Courses/index.vue");
const Welcome = () => import("../pages/WelCome/index.vue");
const Course = () => import("../pages/User/Course/index.vue");
const Module = () => import("../pages/User/Module/index.vue");
const ScoreBoard = () => import("../pages/User/Scoreboard/index.vue");
const Modules = () => import("../pages/User/Modules/index.vue");
const Profile = () => import("../pages/User/Profile/index.vue");
const Community = () => import("../pages/User/Community/index.vue");
const Access = () => import("../pages/Access/index.vue");
const UserManage = () => import("../pages/Admin/Users/index.vue");
const CourseManage = () => import("../pages/Admin/Courses/index.vue");
const LabManage = () => import("../pages/Admin/Labs/index.vue");
const MockTarget = () => import("../mock/MockTarget.vue");
const DashBoard = () => import("../pages/Admin/DashBoard/index.vue");
const ClassProfile = () => import("../pages/Admin/ClassProfile/index.vue");
const GeneratedQuestions = () => import("../pages/Admin/GeneratedQuestions/index.vue");
const Chat = () => import("../pages/User/Chat/index.vue");
const FloatingChatDemo = () => import("../pages/User/Chat/FloatingChatDemo.vue");
const CourseCreate = () => import("../pages/Admin/Courses/create/create.vue");
const AdminStudentProfile = () => import("../pages/Admin/StudentProfile/index.vue");
const ModuleTest = () => import("../pages/User/Module/test.vue");
const XssTest = () => import("../pages/User/Module/xss-test.vue");
const CommandTest = () => import("../pages/User/Module/command-test.vue");
const XSSDirect = () => import("../pages/User/Module/xss-direct.vue");
const Training = () => import("../pages/User/Training/index.vue");
// 队友教师端(Teacher)布局与页面
const TeacherLayout = () => import("../layout/Teacher/index.vue");
const TeacherOverview = () => import("../pages/Teacher/Overview/index.vue");
const TeachingClasses = () => import("../pages/Teacher/TeachingClasses/index.vue");
const TeacherTeachingAnalysis = () => import("../pages/Teacher/TeachingAnalysis/index.vue");
const TeacherCourseLibrary = () => import("../pages/Teacher/CourseLibrary/index.vue");
const TeacherGeneratedQuestions = () => import("../pages/Teacher/GeneratedQuestions/index.vue");
import { getUserInfo } from "../api";
import { clearStoredAuthSession, getStoredToken, isPrivilegedRole, normalizeCurrentUser, storeAuthSession } from "../auth";
import { isLabRunning } from "../composables/useLabState";

export const router = createRouter({
    history: createWebHashHistory(import.meta.env.BASE_URL),
    routes: [
        {
            path: "/container/550e8400-e29b-41d4-a716-446655440000",
            component: MockTarget
        },
        {
            path: "/user",
            component: UserLayout,
            children: [
                {
                    path: "training/cmd-inject-bypass",
                    component: Training
                },
                {
                    path: "",
                    redirect: "/user/welcome"
                },
                {
                    path: "welcome",
                    component: Welcome
                },
                {
                    path: "courses",
                    component: Courses
                },
                {
                    path: "course/:id",
                    component: Course
                },
                {
                    path: "module/:id",
                    component: Module
                },
                {
                    path: "module",
                    component: Module
                },
                {
                    path: "community",
                    component: Community
                },
                {
                    path: "scoreboard",
                    component: ScoreBoard
                },
                {
                    path: "modules",
                    component: Modules
                },
                {
                    path: "profile",
                    component: Profile
                },
                {
                    path: "chat",
                    component: Chat
                },
                {
                    path: "floating-chat-demo",
                    component: FloatingChatDemo
                },
                {
                    path: "module-test",
                    component: ModuleTest
                },
                {
                    path: "xss-test",
                    component: XssTest
                },
                {
                    path: "command-test",
                    component: CommandTest
                },
                {
                    path: "xss-direct",
                    component: XSSDirect
                }
            ]
        },
        {
            path: "/admin",
            component: AdminLayout,
            children: [
                {
                    path: "",
                    redirect: "/admin/dashboard"
                },
                // 在admin路径下
                {
                    path: "course/create",
                    component: CourseCreate
                },
                {
                    path: "course/:id/edit",
                    component: CourseCreate
                },
                {
                    path: "welcome",
                    component: Welcome
                },
                {
                    path: "user",
                    component: UserManage
                },
                {
                    path: "course",
                    component: CourseManage
                },
                {
                    path: "lab",
                    component: LabManage
                },
                {
                    path: "class-profile",
                    component: ClassProfile
                },
                {
                    path: "generated-questions",
                    component: GeneratedQuestions
                },
                {
                    path: "student-profile/:id",
                    component: AdminStudentProfile
                },
                {
                    path: "dashboard",
                    component: DashBoard
                }
            ]
        },
        {
            // 队友新增：教师端（教学班/教学分析/课程库/生成题目），与 /admin 并存
            path: "/teacher",
            component: TeacherLayout,
            children: [
                { path: "", redirect: "/teacher/overview" },
                { path: "overview", component: TeacherOverview },
                { path: "classes", component: TeachingClasses },
                { path: "analysis", component: TeacherTeachingAnalysis },
                { path: "courses", component: TeacherCourseLibrary },
                { path: "generated-questions", component: TeacherGeneratedQuestions }
            ]
        },
        {
            path: "",
            component: Access
        },
        {
            path: "/test",
            component: ModuleTest
        },
        {
            path: "/xss",
            component: XssTest
        },
        {
            path: "/command",
            component: CommandTest
        },
        {
            path: "/xss-direct",
            component: XSSDirect
        }
    ]
});

router.beforeEach((to) => {
    if (isLabRunning.value && !to.path.startsWith("/user/module")) {
        const confirmed = window.confirm("实验正在进行中，离开页面前建议先结束实验。确定要继续离开吗？");
        if (!confirmed) {
            return false;
        }
    }

    const isProtectedRoute = to.path.startsWith("/teacher") || to.path.startsWith("/admin") || to.path.startsWith("/user");
    if (!isProtectedRoute) {
        return true;
    }

    const token = getStoredToken();
    if (!token) {
        return {
            path: "/",
            query: { redirect: to.fullPath },
        };
    }

    return getUserInfo(token)
        .then((response) => {
            if (!response?.data) {
                throw new Error(response?.message || "未获取到当前用户信息");
            }

            const currentUser = normalizeCurrentUser(response.data);
            if (!currentUser) {
                throw new Error("当前用户信息缺少角色字段");
            }

            storeAuthSession(token, currentUser);

            if (!to.path.startsWith("/teacher") && !to.path.startsWith("/admin")) {
                return true;
            }

            if (isPrivilegedRole(currentUser.role)) {
                return true;
            }

            return { path: "/user/profile" };
        })
        .catch((error) => {
            console.error("路由鉴权失败:", error);
            clearStoredAuthSession();
            return {
                path: "/",
                query: { redirect: to.fullPath },
            };
        });
});
