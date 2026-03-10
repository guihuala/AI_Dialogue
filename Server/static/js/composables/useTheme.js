import { ref, computed } from 'vue';

export function useTheme() {
    const activeTheme = ref('blue');
    const themeMap = {
        blue: { sidebar: 'bg-slate-900', primary: 'bg-blue-600 hover:bg-blue-700', text: 'text-blue-600', border: 'border-blue-600' },
        emerald: { sidebar: 'bg-teal-950', primary: 'bg-emerald-600 hover:bg-emerald-700', text: 'text-emerald-600', border: 'border-emerald-600' },
        violet: { sidebar: 'bg-indigo-950', primary: 'bg-violet-600 hover:bg-violet-700', text: 'text-violet-600', border: 'border-violet-600' },
        orange: { sidebar: 'bg-stone-900', primary: 'bg-orange-600 hover:bg-orange-700', text: 'text-orange-600', border: 'border-orange-600' }
    };
    const t = computed(() => themeMap[activeTheme.value]);
    return { activeTheme, t };
}