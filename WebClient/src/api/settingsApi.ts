import axios from 'axios';

// 使用与 gameApi 相同的基础地址
const API_BASE_URL = 'http://127.0.0.1:8000/api/system';

const apiClient = axios.create({
    baseURL: API_BASE_URL
});

apiClient.interceptors.request.use((config) => {
    const visitorId = localStorage.getItem('visitor_id');
    if (visitorId) {
        config.headers['X-Visitor-Id'] = visitorId;
    }
    const accountToken = localStorage.getItem('account_token');
    if (accountToken) {
        config.headers['X-Account-Token'] = accountToken;
    }
    return config;
});

export interface SystemSettings {
    base_url: string;
    api_key: string;
    model_name: string;
    temperature: number;
    max_tokens: number;
    typewriter_speed: number;
    latency_mode: 'balanced' | 'fast' | 'story';
    dialogue_mode: 'single_dm' | 'npc_dm' | 'hybrid' | 'tree_only';
    stability_mode: 'stable' | 'balanced';
}

export const settingsApi = {
    getSettings: async (): Promise<SystemSettings> => {
        const response = await apiClient.get(`/settings`);
        return response.data.data;
    },

    updateSettings: async (settings: Partial<SystemSettings>): Promise<void> => {
        await apiClient.post(`/settings`, settings);
    }
};
