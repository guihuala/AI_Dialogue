import axios from 'axios';

// 使用与 gameApi 相同的基础地址
const API_BASE_URL = 'http://127.0.0.1:8000/api/system';

export interface SystemSettings {
    base_url: string;
    api_key: string;
    model_name: string;
    temperature: number;
    max_tokens: number;
    typewriter_speed: number;
}

export const settingsApi = {
    getSettings: async (): Promise<SystemSettings> => {
        const response = await axios.get(`${API_BASE_URL}/settings`);
        return response.data.data;
    },

    updateSettings: async (settings: Partial<SystemSettings>): Promise<void> => {
        await axios.post(`${API_BASE_URL}/settings`, settings);
    }
};
