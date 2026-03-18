import axios from 'axios';

const API_BASE = 'http://127.0.0.1:8000/api';

export const gameApi = {
  startGame: async (roommates: string[] = [], customPrompts?: Record<string, string>) => {
    const res = await axios.post(`${API_BASE}/game/start`, { 
        roommates,
        custom_prompts: customPrompts 
    });
    return res.data;
  },

  getCandidates: async () => {
    const res = await axios.get(`${API_BASE}/game/candidates`);
    return res.data;
  },

  performTurn: async (turnData: any, customPrompts?: Record<string, string>) => {
    const res = await axios.post(`${API_BASE}/game/turn`, {
        ...turnData,
        custom_prompts: customPrompts
    });
    return res.data;
  },

  getMonitor: async () => {
    const res = await axios.get(`${API_BASE}/game/monitor`);
    return res.data;
  },

  getWorkshopList: async () => {
    const res = await axios.get(`${API_BASE}/workshop/list`);
    return res.data;
  },

  downloadWorkshopItem: async (itemId: string) => {
    const res = await axios.get(`${API_BASE}/workshop/download/${itemId}`);
    return res.data;
  },

  uploadWorkshopItem: async (payload: any) => {
    const res = await axios.post(`${API_BASE}/workshop/upload`, payload);
    return res.data;
  },

  getAdminFiles: async () => {
    const res = await axios.get(`${API_BASE}/admin/files`);
    return res.data;
  },

  getAdminFile: async (type: string, name: string) => {
    const res = await axios.get(`${API_BASE}/admin/file`, { params: { type, name } });
    return res.data;
  },

  saveAdminFile: async (type: string, name: string, content: string) => {
    const res = await axios.post(`${API_BASE}/admin/file`, { type, name, content });
    return res.data;
  },

  publishCurrentMod: async (metadata: { name: string, author: string, description: string }) => {
    const res = await axios.post(`${API_BASE}/workshop/publish_current`, metadata);
    return res.data;
  },

  applyWorkshopMod: async (id: string) => {
    const res = await axios.post(`${API_BASE}/workshop/apply/${id}`);
    return res.data;
  },

  deleteWorkshopMod: async (id: string) => {
    const res = await axios.delete(`${API_BASE}/workshop/${id}`);
    return res.data;
  },

  updateWorkshopMod: async (id: string, metadata: { name?: string, author?: string, description?: string }) => {
    const res = await axios.patch(`${API_BASE}/workshop/${id}`, metadata);
    return res.data;
  },

  uploadPortrait: async (file: File) => {
    const formData = new FormData();
    formData.append('file', file);
    const res = await axios.post(`${API_BASE}/admin/upload_portrait`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    });
    return res.data;
  },

  saveGame: async (saveData: any) => {
    const res = await axios.post(`${API_BASE}/game/save`, saveData);
    return res.data;
  },

  getSavesInfo: async () => {
    const res = await axios.get(`${API_BASE}/game/saves_info`);
    return res.data;
  },

  loadGame: async (slotId: number) => {
    const res = await axios.get(`${API_BASE}/game/load/${slotId}`);
    return res.data;
  },

  deleteSave: async (slotId: number) => {
    const res = await axios.delete(`${API_BASE}/game/save/${slotId}`);
    return res.data;
  }
};
