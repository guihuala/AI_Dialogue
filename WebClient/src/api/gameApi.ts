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
  const accountToken = localStorage.getItem('account_token');
  if (accountToken) {
    config.headers['X-Account-Token'] = accountToken;
  }
  const adminToken = localStorage.getItem('admin_token');
  if (adminToken) {
    config.headers['X-Admin-Token'] = adminToken;
  }
  return config;
});

export const gameApi = {
  registerAccount: async (payload: { username: string; password: string; bind_current_visitor?: boolean }) => {
    const res = await apiClient.post(`/account/register`, payload);
    return res.data;
  },

  loginAccount: async (payload: { username: string; password: string }) => {
    const res = await apiClient.post(`/account/login`, payload);
    return res.data;
  },

  getAccountMe: async () => {
    const res = await apiClient.get(`/account/me`);
    return res.data;
  },

  logoutAccount: async () => {
    const res = await apiClient.post(`/account/logout`);
    return res.data;
  },

  changeAccountPassword: async (payload: { current_password: string; new_password: string }) => {
    const res = await apiClient.post(`/account/change_password`, payload);
    return res.data;
  },

  bindCurrentVisitorToAccount: async (payload?: { conflict_strategy?: 'keep_account' | 'overwrite_with_visitor' }) => {
    const res = await apiClient.post(`/account/bind_current_visitor`, payload || {});
    return res.data;
  },

  getVisitorBindingPreview: async () => {
    const res = await apiClient.get(`/account/visitor_binding_preview`);
    return res.data;
  },

  getAccountSessions: async () => {
    const res = await apiClient.get(`/account/sessions`);
    return res.data;
  },

  logoutOtherAccountSessions: async () => {
    const res = await apiClient.post(`/account/logout_others`);
    return res.data;
  },

  revokeAccountSession: async (sessionId: string) => {
    const res = await apiClient.post(`/account/revoke_session/${sessionId}`);
    return res.data;
  },

  startGame: async (roommates: string[] = [], modId: string = "default", customPrompts?: Record<string, string>, saveId: string = "slot_0") => {
    const res = await apiClient.post(`/game/start`, { 
        roommates,
        mod_id: modId,
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

  prefetch: async (turnData: any, customPrompts?: Record<string, string>, saveId: string = "slot_0") => {
    const res = await apiClient.post(`/game/prefetch`, {
        ...turnData,
        custom_prompts: customPrompts,
        save_id: saveId,
        is_prefetch: true
    });
    return res.data;
  },

  getMonitor: async () => {
    const res = await apiClient.get(`/game/monitor`);
    return res.data;
  },

  // Admin/Editor Management
  adminLogin: async (password: string) => {
    const res = await apiClient.post(`/admin/login`, { password });
    return res.data;
  },

  getAdminSession: async () => {
    const res = await apiClient.get(`/admin/session`);
    return res.data;
  },

  adminLogout: async () => {
    const res = await apiClient.post(`/admin/logout`);
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

  getAdminUsers: async (params?: {
    q?: string;
    sort_by?: 'updated_at' | 'created_at' | 'username';
    sort_order?: 'asc' | 'desc';
    page?: number;
    page_size?: number;
  }) => {
    const res = await apiClient.get(`/admin/users`, { params });
    return res.data;
  },

  getAdminUserStats: async () => {
    const res = await apiClient.get(`/admin/users/stats`);
    return res.data;
  },

  saveAdminFile: async (type: string, name: string, content: string) => {
    const res = await apiClient.post(`/admin/file`, { type, name, content });
    return res.data;
  },

  // Library Management
  getLibraryList: async (params?: {
    q?: string;
    sort_by?: string;
    sort_order?: 'asc' | 'desc';
    source_type?: string;
    visibility?: string;
    page?: number;
    page_size?: number;
  }) => {
    const res = await apiClient.get(`/library/list`, { params });
    return res.data;
  },

  saveToLibrary: async (name: string, description: string) => {
    const res = await apiClient.post(`/library/save_current`, { name, description });
    return res.data;
  },

  selectLibraryItemForEdit: async (itemId: string) => {
    const res = await apiClient.post(`/library/edit/${itemId}`);
    return res.data;
  },

  selectDefaultForEdit: async () => {
    const res = await apiClient.post(`/editor/default`);
    return res.data;
  },

  applyFromLibrary: async (itemId: string) => {
    const res = await apiClient.post(`/library/apply/${itemId}`);
    return res.data;
  },

  validateLibraryItem: async (itemId: string) => {
    const res = await apiClient.post(`/library/validate/${itemId}`);
    return res.data;
  },

  deleteFromLibrary: async (itemId: string) => {
    const res = await apiClient.delete(`/library/${itemId}`);
    return res.data;
  },

  syncLibraryItem: async (itemId: string) => {
    const res = await apiClient.post(`/library/sync/${itemId}`);
    return res.data;
  },

  getUserState: async () => {
    const res = await apiClient.get(`/user/state`);
    return res.data;
  },

  getStorageQuota: async () => {
    const res = await apiClient.get(`/storage/quota`);
    return res.data;
  },

  cleanupStorage: async (payload: { dry_run?: boolean; keep_recent_library?: number; keep_recent_snapshots?: number }) => {
    const res = await apiClient.post(`/storage/cleanup`, payload);
    return res.data;
  },

  getUserAudit: async (limit: number = 30) => {
    const res = await apiClient.get(`/user/audit`, { params: { limit } });
    return res.data;
  },

  getSnapshots: async () => {
    const res = await apiClient.get(`/user/snapshots`);
    return res.data;
  },

  rollbackSnapshot: async (snapshotId: string) => {
    const res = await apiClient.post(`/user/rollback/${snapshotId}`);
    return res.data;
  },

  // Workshop Management
  getWorkshopList: async (params?: {
    q?: string;
    sort_by?: string;
    sort_order?: 'asc' | 'desc';
    source_type?: string;
    focus_tag?: string;
    owned_only?: boolean;
    page?: number;
    page_size?: number;
  }) => {
    const res = await apiClient.get(`/workshop/list`, { params });
    return res.data;
  },

  getMyWorkshopList: async (params?: {
    q?: string;
    sort_by?: string;
    sort_order?: 'asc' | 'desc';
    source_type?: string;
    focus_tag?: string;
    page?: number;
    page_size?: number;
  }) => {
    const res = await apiClient.get(`/workshop/mine`, { params });
    return res.data;
  },

  downloadWorkshopItem: async (itemId: string) => {
    const res = await apiClient.post(`/workshop/download/${itemId}`);
    return res.data;
  },

  publishCurrentMod: async (metadata: { name: string, author: string, description: string }) => {
    const res = await apiClient.post(`/workshop/publish_current`, metadata);
    return res.data;
  },

  publishCreateMod: async (metadata: { name: string, author: string, description: string }) => {
    const res = await apiClient.post(`/workshop/publish_create`, metadata);
    return res.data;
  },

  publishUpdateMod: async (metadata: { name: string, author: string, description: string }) => {
    const res = await apiClient.post(`/workshop/publish_update`, metadata);
    return res.data;
  },

  publishForkMod: async (metadata: { name: string, author: string, description: string }) => {
    const res = await apiClient.post(`/workshop/publish_fork`, metadata);
    return res.data;
  },

  validateCurrentForPublish: async () => {
    const res = await apiClient.post(`/workshop/validate_current`);
    return res.data;
  },

  applyWorkshopMod: async (id: string) => {
    const res = await apiClient.post(`/workshop/apply/${id}`);
    return res.data;
  },

  deleteWorkshopItem: async (id: string) => {
    const res = await apiClient.delete(`/workshop/${id}`);
    return res.data;
  },

  updateWorkshopItem: async (id: string, metadata: { name?: string, author?: string, description?: string }) => {
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
