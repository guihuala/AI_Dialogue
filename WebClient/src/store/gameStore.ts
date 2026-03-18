import { create } from 'zustand';
import { gameApi } from '../api/gameApi';

interface GameState {
  isPlaying: boolean;
  isLoading: boolean;
  
  // 主角数值
  san: number;
  money: number;
  gpa: number;
  hygiene: number;
  reputation: number;
  
  // 对局信息
  chapter: number;
  turn: number;
  current_evt_id: string;
  active_roommates: string[];
  affinity: Record<string, number>;
  
  // 故事与交互
  displayText: string;
  nextOptions: string[];
  isEnd: boolean;
  history: Array<{turn: number, text: string}>;
  wechatNotifications: Array<{sender: string, message: string}>;
  isPhoneOpen: boolean;
  typewriterSpeed: number;
  audioVolume: number;
  isMuted: boolean;
  uiTransparency: number;

  // actions
  startGame: (roommates?: string[], modId?: string) => Promise<void>;
  performTurn: (choice: string) => Promise<void>;
  saveGame: (slotId: number) => Promise<void>;
  loadSave: (slotId: number) => Promise<void>;
  setTypewriterSpeed: (speed: number) => void;
  setAudioVolume: (volume: number) => void;
  setMuted: (muted: boolean) => void;
  setUiTransparency: (transparency: number) => void;
  resetGame: () => Promise<void>;
  clearWechatNotifications: () => void;
  togglePhone: (open?: boolean) => void;
}

export const useGameStore = create<GameState>((set, get) => ({
  isPlaying: false,
  isLoading: false,
  san: 100,
  money: 2000,
  gpa: 4.0,
  hygiene: 100,
  reputation: 100,
  chapter: 1,
  turn: 0,
  current_evt_id: '',
  active_roommates: [],
  affinity: {},
  displayText: '',
  nextOptions: [],
  isEnd: false,
  history: [],
  wechatNotifications: [],
  isPhoneOpen: false,
  typewriterSpeed: 30,
  audioVolume: 80,
  isMuted: false,
  uiTransparency: 90,

  startGame: async (roommates = [], modId?: string) => {
    set({ isLoading: true });
    try {
      if (modId) {
        await gameApi.applyWorkshopMod(modId);
      }
      const data = await gameApi.startGame(roommates, undefined);
      set({
        isPlaying: true,
        isLoading: false,
        san: data.san,
        money: data.money,
        gpa: data.gpa,
        hygiene: data.hygiene,
        reputation: data.reputation,
        chapter: data.chapter,
        turn: data.turn,
        current_evt_id: data.current_evt_id,
        active_roommates: data.active_roommates || roommates,
        affinity: data.affinity,
        displayText: data.display_text,
        nextOptions: data.next_options || [],
        isEnd: data.is_end || false,
        history: [{ turn: data.turn, text: data.display_text }],
        wechatNotifications: data.wechat_notifications || []
      });
    } catch (e) {
      console.error(e);
      set({ isLoading: false });
    }
  },

  performTurn: async (choice: string) => {
    const state = get();
    if (state.isLoading) return;
    
    set({ isLoading: true });
    try {
      const turnReq = {
        choice,
        active_roommates: state.active_roommates,
        current_evt_id: state.current_evt_id,
        is_transition: false,
        chapter: state.chapter,
        turn: state.turn,
        san: state.san,
        money: state.money,
        gpa: state.gpa,
        hygiene: state.hygiene,
        reputation: state.reputation,
        affinity: state.affinity
      };
      
      const data = await gameApi.performTurn(turnReq, undefined);
      set((prev) => ({
        isLoading: false,
        san: data.san,
        money: data.money,
        gpa: data.gpa,
        hygiene: data.hygiene,
        reputation: data.reputation,
        chapter: data.chapter,
        turn: data.turn,
        current_evt_id: data.current_evt_id,
        affinity: data.affinity,
        displayText: data.display_text,
        nextOptions: data.next_options || [],
        isEnd: data.is_end || false,
        history: [...prev.history, { turn: data.turn, text: `【你的选择】: ${choice}\n\n${data.display_text}` }],
        wechatNotifications: data.wechat_notifications || prev.wechatNotifications
      }));
    } catch (e) {
      console.error(e);
      set({ isLoading: false });
    }
  },

  clearWechatNotifications: () => {
      set({ wechatNotifications: [] });
  },

  togglePhone: (open?: boolean) => {
      set((state) => ({ isPhoneOpen: open !== undefined ? open : !state.isPhoneOpen }));
  },

  setTypewriterSpeed: (speed: number) => {
      set({ typewriterSpeed: speed });
  },

  loadSave: async (slotId: number) => {
      set({ isLoading: true });
      try {
          const res = await gameApi.loadGame(slotId);
          const data = res; // app.py returns the state directly in data if wrapped or just the state
          // res is {"status": "success", "data": state}
          const gameState = res.data;
          set({
              isPlaying: true,
              isLoading: false,
              san: gameState.san,
              money: gameState.money,
              gpa: gameState.gpa,
              // Note: some fields might be slightly different in SaveGameRequest vs GameTurnRequest
              // but app.py SaveGameRequest has what we need
              chapter: gameState.chapter,
              turn: gameState.turn,
              current_evt_id: gameState.current_evt_id,
              active_roommates: gameState.active_roommates,
              // affinity, hygiene, etc should ideally be in save too
              displayText: "存档已成功加载，您可以继续之前的进度。",
              nextOptions: ["继续剧情..."],
              isEnd: false,
              history: gameState.history || [],
              wechatNotifications: []
          });
      } catch (e) {
          console.error(e);
          set({ isLoading: false });
      }
  },

  saveGame: async (slotId: number) => {
      const state = get();
      try {
          await gameApi.saveGame({
              slot_id: slotId,
              active_roommates: state.active_roommates,
              current_evt_id: state.current_evt_id,
              chapter: state.chapter,
              turn: state.turn,
              san: state.san,
              money: state.money,
              gpa: state.gpa,
              arg_count: 0, // Should be in state
              wechat_data_list: [], // Should be in state if we want to save wechat
              history: state.history // Custom field for loading
          });
      } catch (e) {
          console.error('Failed to save game:', e);
      }
  },

  setAudioVolume: (volume: number) => set({ audioVolume: volume }),
  setMuted: (muted: boolean) => set({ isMuted: muted }),
  setUiTransparency: (transparency: number) => set({ uiTransparency: transparency }),
  
  resetGame: async () => {
      try {
          await gameApi.resetGame();
          set({
              isPlaying: false,
              san: 100,
              money: 2000,
              gpa: 4.0,
              hygiene: 100,
              reputation: 100,
              chapter: 1,
              turn: 0,
              current_evt_id: '',
              history: [],
              wechatNotifications: [],
              displayText: ''
          });
      } catch (e) {
          console.error('Failed to reset game:', e);
      }
  }
}));
