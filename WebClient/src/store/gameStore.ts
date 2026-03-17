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

  // actions
  startGame: (roommates?: string[], modId?: string) => Promise<void>;
  performTurn: (choice: string) => Promise<void>;
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
  }
}));
