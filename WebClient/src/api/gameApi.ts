import axios from 'axios';

const API_BASE = 'http://127.0.0.1:8000/api';

const apiClient = axios.create({
  baseURL: API_BASE,
});

apiClient.interceptors.request.use((config) => {
  const visitorId = localStorage.getItem('visitor_id');
  if (visitorId) {
    config.headers['X-Visitor-Id'] = visitorId;
  }
  return config;
});

export const gameApi = {
  startGame: async (roommates: string[] = [], customPrompts?: Record<string, string>, saveId: string = "slot_0") => {
    const res = await apiClient.post(`/game/start`, { 
        roommates,
        custom_prompts: customPrompts,
        save_id: saveId
    });
    return res.data;
  },

  getCandidates: async () => {
    const res = await apiClient.get(`/game/candidates`);
    return res.data;
  },

  performTurn: async (turnData: any, customPrompts?: Record<string, string>, saveId: string = "slot_0") => {
    const res = await apiClient.post(`/game/turn`, {
        ...turnData,
        custom_prompts: customPrompts,
        save_id: saveId
    });
    return res.data;
  },

  getMonitor: async () => {
    const res = await apiClient.get(`/game/monitor`);
    return res.data;
  },

  getWorkshopList: async () => {
    const res = await apiClient.get(`/workshop/list`);
    return res.data;
  },

  downloadWorkshopItem: async (itemId: string) => {
    const res = await apiClient.get(`/workshop/download/${itemId}`);
    return res.data;
  },

  uploadWorkshopItem: async (payload: any) => {
    const res = await apiClient.post(`/workshop/upload`, payload);
    return res.data;
  },

  getAdminFiles: async () => {
    const res = await apiClient.get(`/admin/files`);
    return res.data;
  },

  getAdminFile: async (type: string, name: string) => {
    const res = await apiClient.get(`/admin/file`, { params: { type, name } });
    return res.data;
  },

  saveAdminFile: async (type: string, name: string, content: string) => {
    const res = await apiClient.post(`/admin/file`, { type, name, content });
    return res.data;
  },

  publishCurrentMod: async (metadata: { name: string, author: string, description: string }) => {
    const res = await apiClient.post(`/workshop/publish_current`, metadata);
    return res.data;
  },

  applyWorkshopMod: async (id: string) => {
    const res = await apiClient.post(`/workshop/apply/${id}`);
    return res.data;
  },

  deleteWorkshopMod: async (id: string) => {
    const res = await apiClient.delete(`/workshop/${id}`);
    return res.data;
  },

  updateWorkshopMod: async (id: string, metadata: { name?: string, author?: string, description?: string }) => {
    const res = await apiClient.patch(`/workshop/${id}`, metadata);
    return res.data;
  },

  uploadPortrait: async (file: File) => {
    const formData = new FormData();
    formData.append('file', file);
    const res = await apiClient.post(`/admin/upload_portrait`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    });
    return res.data;
  },

  saveGame: async (saveData: any) => {
    const res = await apiClient.post(`/game/save`, saveData);
    return res.data;
  },

  getSavesInfo: async () => {
    const res = await apiClient.get(`/game/saves_info`);
    return res.data;
  },

  loadGame: async (slotId: number) => {
    const res = await apiClient.get(`/game/load/${slotId}`);
    return res.data;
  },

  deleteSave: async (slotId: number) => {
    const res = await apiClient.delete(`/game/save/${slotId}`);
    return res.data;
  },

  resetGame: async () => {
    const res = await apiClient.post(`/game/reset`);
    return res.data;
  },

  generateSkillPrompt: async (concept: string) => {
    const res = await apiClient.post(`/admin/generate_skill_prompt`, { concept });
    return res.data;
  },
  
  // Memory Management
  getMemories: async (saveId: string, charName?: string, type?: string) => {
    const res = await apiClient.get(`/game/memories`, {
      params: { save_id: saveId, char_name: charName, type }
    });
    return res.data;
  },

  deleteMemory: async (memoryId: string) => {
    const res = await apiClient.delete(`/game/memories/${memoryId}`);
    return res.data;
  }
};
