import axios from 'axios';
import { API_BASE } from './apiBase';

const API_BASE_URL = `${API_BASE}/system`;

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
    turn_debug?: boolean;
}

export const settingsApi = {
    getSettings: async (): Promise<SystemSettings> => {
        const candidates = [
            `${API_BASE}/system/settings`,
            `/api/system/settings`,
            `${window.location.origin}/api/system/settings`,
        ];
        let lastError: any = null;
        for (const url of candidates) {
            try {
                const response = await apiClient.get(url);
                if (response?.data?.status === 'success' && response?.data?.data) {
                    return response.data.data;
                }
            } catch (e) {
                lastError = e;
            }
        }
        throw lastError || new Error('读取系统设置失败');
    },

    updateSettings: async (settings: Partial<SystemSettings>): Promise<void> => {
        const candidates = [
            `${API_BASE}/system/settings`,
            `/api/system/settings`,
            `${window.location.origin}/api/system/settings`,
        ];
        let lastError: any = null;
        for (const url of candidates) {
            try {
                const res = await apiClient.post(url, settings);
                if (res?.data?.status === 'success') return;
            } catch (e) {
                lastError = e;
            }
        }
        throw lastError || new Error('保存系统设置失败');
    }
};
