import { ref } from 'vue';

export function useSettings(showToast) {
    const settings = ref({ api_key: '', base_url: '', model_name: '', temperature: 0.7, max_tokens: 800 });

    const fetchSettings = async () => {
        try {
            const res = await fetch('/api/system/settings');
            const data = await res.json();
            if (data.status === 'success') settings.value = data.data;
        } catch (e) { }
    };

    const saveSettings = async () => {
        try {
            const res = await fetch('/api/system/settings', {
                method: 'POST', headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(settings.value)
            });
            const data = await res.json();
            showToast(data.message || "运行协议已更新生效");
        } catch (e) { showToast("协议应用失败"); }
    };

    return { settings, fetchSettings, saveSettings };
}