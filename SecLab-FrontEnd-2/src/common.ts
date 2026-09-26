import { inject, ref } from "vue";
import type { VueCookies } from "vue-cookies";

export type MergeId<A> = Omit<A, 'id'> &  { id:number }

export function useCookie() {
    return {
        set(key: string, value: string) {
            document.cookie = `${key}=${value}; path=/; max-age=${60 * 60 * 24 * 7}`; // 7天过期
            // 同时存储到localStorage作为备份
            localStorage.setItem(`cookie_${key}`, value);
        },
        get(key: string) {
            const cookieValue = document.cookie
                .split('; ')
                .find(row => row.startsWith(`${key}=`))
                ?.split('=')[1];
            
            // 如果cookie中没有，尝试从localStorage获取
            if (!cookieValue) {
                const localValue = localStorage.getItem(`cookie_${key}`);
                return localValue;
            }
            
            return cookieValue;
        },
        remove(key: string) {
            document.cookie = `${key}=; path=/; expires=Thu, 01 Jan 1970 00:00:00 GMT`;
            localStorage.removeItem(`cookie_${key}`);
        }
    }
}

// Toast 相关
const toastMessage = ref('');
const toastVisible = ref(false);

export const showToast = (message: string) => {
    // 立即重置之前的计时器，以确保新消息能立即显示
    toastVisible.value = false;
    
    // 小延迟后显示新消息，避免闪烁
    setTimeout(() => {
        toastMessage.value = message;
        toastVisible.value = true;
    }, 10);

    // 自动隐藏
    setTimeout(() => {
        toastVisible.value = false;
    }, 3000); // 3秒后隐藏
};

// Toast 组件
export const useToast = () => {
    return {
        toastMessage,
        toastVisible,
    };
};
