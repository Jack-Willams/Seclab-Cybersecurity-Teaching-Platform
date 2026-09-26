export type AuthRole = "admin" | "teacher" | "student";

const TOKEN_KEY = "token";
const COOKIE_TOKEN_BACKUP_KEY = "cookie_token";
const AUTH_ROLE_KEY = "auth_role";
const AUTH_STUDENT_NUMBER_KEY = "auth_student_number";
const CURRENT_USER_KEY = "auth_current_user";
const COOKIE_MAX_AGE_SECONDS = 60 * 60 * 24 * 7;

// Kept only for compatibility with pages that have not yet been migrated.
export const DEMO_PROFILE_STORAGE_KEY = "seclab_demo_profile_user";
export const LIN_ZONGHENG_DEMO_STUDENT_NUMBER = "2023210405029";

type UnknownRecord = Record<string, unknown>;

export type CurrentUserSnapshot = {
    userId: number;
    username: string;
    realName: string;
    role: AuthRole;
    studentNumber: string;
    classId: number | null;
    className: string;
    email: string;
    phone: string;
    userImage: string;
    status: string;
};

const ROLE_FIELDS = [
    "role",
    "userRole",
    "identity",
    "userType",
    "accountType",
    "type",
    "statusRole",
    "user_role",
    "isAdmin",
    "is_admin",
] as const;

function readCookieValue(key: string): string | null {
    if (typeof document === "undefined") {
        return null;
    }

    const prefix = `${key}=`;
    const cookie = document.cookie
        .split("; ")
        .find((row) => row.startsWith(prefix));

    if (!cookie) {
        return null;
    }

    return decodeURIComponent(cookie.slice(prefix.length));
}

function writeCookieValue(key: string, value: string) {
    if (typeof document === "undefined") {
        return;
    }

    document.cookie = `${key}=${encodeURIComponent(value)}; path=/; max-age=${COOKIE_MAX_AGE_SECONDS}`;
}

function removeCookieValue(key: string) {
    if (typeof document === "undefined") {
        return;
    }

    document.cookie = `${key}=; path=/; expires=Thu, 01 Jan 1970 00:00:00 GMT`;
}

function readLocalStorage(key: string): string | null {
    if (typeof window === "undefined") {
        return null;
    }

    try {
        return window.localStorage.getItem(key);
    } catch {
        return null;
    }
}

function writeLocalStorage(key: string, value: string) {
    if (typeof window === "undefined") {
        return;
    }

    try {
        window.localStorage.setItem(key, value);
    } catch {
        // Ignore storage write failures and keep auth flow usable with cookies.
    }
}

function removeLocalStorage(key: string) {
    if (typeof window === "undefined") {
        return;
    }

    try {
        window.localStorage.removeItem(key);
    } catch {
        // Ignore storage cleanup failures.
    }
}

function asRecord(value: unknown): UnknownRecord | null {
    return value !== null && typeof value === "object" ? (value as UnknownRecord) : null;
}

function readFirstString(record: UnknownRecord | null, keys: string[]): string | null {
    if (!record) {
        return null;
    }

    for (const key of keys) {
        const value = record[key];
        if (typeof value === "string" && value.trim()) {
            return value.trim();
        }
    }

    return null;
}

function readFirstNumber(record: UnknownRecord | null, keys: string[]): number | null {
    if (!record) {
        return null;
    }

    for (const key of keys) {
        const value = record[key];
        if (typeof value === "number" && Number.isFinite(value)) {
            return value;
        }
        if (typeof value === "string" && value.trim()) {
            const parsed = Number(value);
            if (Number.isFinite(parsed)) {
                return parsed;
            }
        }
    }

    return null;
}

export function normalizeRoleValue(value: unknown): AuthRole | null {
    if (typeof value === "boolean") {
        return value ? "admin" : "student";
    }

    if (typeof value === "number") {
        if (value === 1) {
            return "admin";
        }
        if (value === 0) {
            return "student";
        }
        return null;
    }

    if (typeof value !== "string") {
        return null;
    }

    const normalized = value.trim().toLowerCase();
    if (!normalized) {
        return null;
    }

    if (normalized.includes("admin") || normalized.includes("administrator") || normalized.includes("manager")) {
        return "admin";
    }

    if (normalized.includes("teacher") || normalized.includes("instructor")) {
        return "teacher";
    }

    if (normalized.includes("student") || normalized.includes("user")) {
        return "student";
    }

    if (normalized === "active" || normalized === "enabled") {
        return null;
    }

    return null;
}

function extractRole(record: UnknownRecord | null): AuthRole | null {
    if (!record) {
        return null;
    }

    for (const field of ROLE_FIELDS) {
        const role = normalizeRoleValue(record[field]);
        if (role) {
            return role;
        }
    }

    return null;
}

export function normalizeCurrentUser(source: unknown): CurrentUserSnapshot | null {
    const root = asRecord(source);
    const data = asRecord(root?.data);
    const loginData = asRecord(data?.loginData ?? root?.loginData);

    const candidates = [loginData, data, root].filter(Boolean) as UnknownRecord[];
    let resolvedRole: AuthRole | null = null;

    for (const candidate of candidates) {
        resolvedRole = extractRole(candidate);
        if (resolvedRole) {
            break;
        }
    }

    const primary = loginData ?? data ?? root;
    const userId = readFirstNumber(primary, ["userId", "id"]);
    const username = readFirstString(primary, ["username", "userName", "realName", "name"]) ?? "";
    const studentNumber = readFirstString(primary, ["userStudentNumber", "studentNumber", "studentNo", "account"]) ?? "";

    if (!resolvedRole || userId === null || !studentNumber) {
        return null;
    }

    return {
        userId,
        username,
        realName: readFirstString(primary, ["realName", "name", "userName", "username"]) ?? username,
        role: resolvedRole,
        studentNumber,
        classId: readFirstNumber(primary, ["classId"]),
        className: readFirstString(primary, ["className", "userClass"]) ?? "",
        email: readFirstString(primary, ["email", "userEmail"]) ?? "",
        phone: readFirstString(primary, ["phone", "userTel"]) ?? "",
        userImage: readFirstString(primary, ["userImage", "avatar"]) ?? "",
        status: readFirstString(primary, ["status"]) ?? "active",
    };
}

export function clearStoredAuthSession() {
    removeCookieValue(TOKEN_KEY);
    removeLocalStorage(TOKEN_KEY);
    removeLocalStorage(COOKIE_TOKEN_BACKUP_KEY);
    removeLocalStorage(AUTH_ROLE_KEY);
    removeLocalStorage(AUTH_STUDENT_NUMBER_KEY);
    removeLocalStorage(CURRENT_USER_KEY);
}

export function storeAuthSession(token: string, currentUser: CurrentUserSnapshot) {
    writeCookieValue(TOKEN_KEY, token);
    writeLocalStorage(TOKEN_KEY, token);
    writeLocalStorage(COOKIE_TOKEN_BACKUP_KEY, token);
    writeLocalStorage(AUTH_ROLE_KEY, currentUser.role);
    writeLocalStorage(AUTH_STUDENT_NUMBER_KEY, currentUser.studentNumber);
    writeLocalStorage(CURRENT_USER_KEY, JSON.stringify(currentUser));
}

export function getStoredToken(): string | null {
    return readCookieValue(TOKEN_KEY) ?? readLocalStorage(TOKEN_KEY) ?? readLocalStorage(COOKIE_TOKEN_BACKUP_KEY);
}

export function getStoredCurrentUser(): CurrentUserSnapshot | null {
    const raw = readLocalStorage(CURRENT_USER_KEY);
    if (!raw) {
        return null;
    }

    try {
        return normalizeCurrentUser(JSON.parse(raw));
    } catch {
        return null;
    }
}

export function getStoredAuthRole(): AuthRole | null {
    return getStoredCurrentUser()?.role ?? normalizeRoleValue(readLocalStorage(AUTH_ROLE_KEY));
}

export function getStoredStudentNumber(): string | null {
    return getStoredCurrentUser()?.studentNumber ?? readLocalStorage(AUTH_STUDENT_NUMBER_KEY)?.trim() ?? null;
}

export function isPrivilegedRole(role: AuthRole | null): boolean {
    return role === "admin" || role === "teacher";
}

export function getHomeRouteForRole(role: AuthRole | null): string {
    // 合并后同时保留 /admin(我方) 与 /teacher(队友)：教师登录进教师端，管理员进管理后台
    if (role === "teacher") return "/teacher/overview";
    if (isPrivilegedRole(role)) return "/admin/dashboard";
    return "/user/welcome";
}
