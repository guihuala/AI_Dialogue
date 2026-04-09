import axios from 'axios';
import { API_BASE } from './apiBase';

const buildAuthHeaders = () => {
    const headers: Record<string, string> = {};
    const visitorId = localStorage.getItem('visitor_id');
    if (visitorId) {
        headers['X-Visitor-Id'] = visitorId;
    }
    const accountToken = localStorage.getItem('account_token');
    if (accountToken) {
        headers['X-Account-Token'] = accountToken;
    }
    return headers;
};

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
                const response = await axios.get(url, { headers: buildAuthHeaders() });
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
                const res = await axios.post(url, settings, { headers: buildAuthHeaders() });
                if (res?.data?.status === 'success') return;
            } catch (e) {
                lastError = e;
            }
        }
        throw lastError || new Error('保存系统设置失败');
    },

    validateSettings: async (): Promise<{ message: string }> => {
        const candidates = [
            `${API_BASE}/system/settings/validate`,
            `/api/system/settings/validate`,
            `${window.location.origin}/api/system/settings/validate`,
        ];
        let lastError: any = null;
        for (const url of candidates) {
            try {
                const res = await axios.get(url, { headers: buildAuthHeaders() });
                if (res?.data?.status === 'success') {
                    return { message: String(res?.data?.message || '配置有效') };
                }
            } catch (e) {
                lastError = e;
            }
        }
        throw lastError || new Error('模型配置校验失败');
    }
};
