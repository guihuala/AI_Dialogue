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
  current_scene: string;
  player_name: string;
  active_roommates: string[];
  affinity: Record<string, number>;
  narrativeState: Record<string, any>;
  systemState: Record<string, any>;
  systemDailyPlan: Record<string, any> | null;
  systemKeyResolution: Record<string, any> | null;
  weeklySummary: Record<string, any> | null;
  
  // 故事与交互
  displayText: string;
  nextOptions: string[];
  isEnd: boolean;
  history: Array<{turn: number, text: string, rawJson?: string, narrativeState?: Record<string, any>}>;
  wechatNotifications: Array<{sender: string, message: string}>;
  phoneSystemEnabled: boolean;
  isPhoneOpen: boolean;
  typewriterSpeed: number;
  audioVolume: number;
  isMuted: boolean;
  uiTransparency: number;
  currentSaveId: string;
  visitorId: string;
  pendingChoice: string | null;

  eventScript: any | null;
  turnDebug: {
    timings?: Record<string, number>;
    prompt_diagnostics?: any;
    render_source?: string;
    ai_usage?: any;
    state_delta?: any;
  } | null;

  // actions
  startGame: (roommates?: string[], modId?: string) => Promise<void>;
  performTurn: (choice: string) => Promise<void>;
  saveGame: (slotId: number) => Promise<void>;
  loadSave: (slotId: number) => Promise<void>;
  setTypewriterSpeed: (speed: number) => void;
  setAudioVolume: (volume: number) => void;
  setMuted: (muted: boolean) => void;
  setUiTransparency: (transparency: number) => void;
  prefetch: (choice: string) => Promise<void>;
  resetGame: () => Promise<void>;
  clearWechatNotifications: () => void;
  togglePhone: (open?: boolean) => void;
  setEventScript: (script: any) => void;
}

const isTransitionChoice = (choice: string): boolean => {
  const text = String(choice || '');
  return /继续剧情|进入下一幕|下一幕|转场|进入下一事件|继续前进/.test(text);
};

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
  current_scene: '宿舍',
  player_name: '陆陈安然',
  active_roommates: [],
  affinity: {},
  narrativeState: {},
  systemState: {},
  systemDailyPlan: null,
  systemKeyResolution: null,
  weeklySummary: null,
  displayText: '',
  nextOptions: [],
  isEnd: false,
  history: [],
  wechatNotifications: [],
  phoneSystemEnabled: true,
  isPhoneOpen: false,
  typewriterSpeed: 30,
  audioVolume: 80,
  isMuted: false,
  uiTransparency: 90,
  currentSaveId: 'slot_0',
  eventScript: null,
  visitorId: (() => {
    const existingId = localStorage.getItem('visitor_id');
    if (existingId) return existingId;
    const generatedId =
      (crypto as any).randomUUID?.() ||
      Math.random().toString(36).substring(2, 15) + Math.random().toString(36).substring(2, 15);
    localStorage.setItem('visitor_id', generatedId);
    return generatedId;
  })(),
  pendingChoice: null,
  turnDebug: null,

  setEventScript: (script: any) => set({ eventScript: script }),

  startGame: async (roommates = [], modId?: string) => {
    set({ isLoading: true, pendingChoice: null });
    try {
      const data = await gameApi.startGame(roommates, modId || 'default', undefined, 'slot_0');
      set({
        currentSaveId: 'slot_0',
        isPlaying: true,
        isLoading: false,
        pendingChoice: null,
        san: data.san,
        money: data.money,
        gpa: data.gpa,
        hygiene: data.hygiene,
        reputation: data.reputation,
        chapter: data.chapter,
        turn: data.turn,
        current_evt_id: data.current_evt_id,
        current_scene: data.current_scene || '宿舍',
        player_name: data.player_name || '陆陈安然',
        active_roommates: data.active_roommates || roommates,
        affinity: data.affinity,
        narrativeState: data.narrative_state || {},
        systemState: data.system_state || {},
        systemDailyPlan: data.system_daily_plan || null,
        systemKeyResolution: data.system_key_resolution || null,
        weeklySummary: data.weekly_summary || null,
        displayText: data.display_text,
        nextOptions: data.next_options || [],
        isEnd: data.is_end || false,
        history: [{
          turn: data.turn,
          text: data.display_text,
          rawJson: data.res_text || '',
          narrativeState: data.narrative_state || {}
        }],
        wechatNotifications: data.wechat_notifications || [],
        phoneSystemEnabled: data.phone_system_enabled !== false,
        eventScript: data.event_script || null
        ,
        turnDebug: (data.timings || data.prompt_diagnostics || data.render_source || data.ai_usage || data.state_delta)
          ? {
              timings: data.timings || undefined,
              prompt_diagnostics: data.prompt_diagnostics || undefined,
              render_source: data.render_source || undefined,
              ai_usage: data.ai_usage || undefined,
              state_delta: data.state_delta || undefined,
            }
          : null
      });
    } catch (e) {
      console.error(e);
      set({ isLoading: false });
    }
  },

  performTurn: async (choice: string) => {
    const state = get();
    if (state.isLoading) return;

    // --- [LOCAL SCRIPT RESOLUTION] ---
    if (state.eventScript && !state.isEnd && !isTransitionChoice(choice)) {
      const script = state.eventScript;
      const turnData = (script.turns || []).find((t: any) => t.turn_num === state.turn);
      
      if (turnData) {
        const selectedChoice = (turnData.player_choices || []).find((c: any) => 
          choice.includes(c.text) || c.text.includes(choice)
        );

        if (selectedChoice) {
          console.log("🚀 [Frontend] Script HIT: Resolving turn locally");
          const nextTurnNum = selectedChoice.leads_to_turn;
          const nextTurn = (script.turns || []).find((t: any) => t.turn_num === nextTurnNum);
          
          const dialogueSeq = [...(selectedChoice.immediate_outcome_dialogue || [])];
          if (nextTurn && nextTurn.dialogue_sequence) {
            dialogueSeq.push(...nextTurn.dialogue_sequence);
          }

          const displayLines = dialogueSeq.map((d: any) => `**[${d.speaker}]** ${d.content}`);
          const newDisplayText = `你选择了：${selectedChoice.text}\n\n` + displayLines.join('\n\n');

          const stats = selectedChoice.stat_changes || {};
          
          set((prev) => ({
            san: Math.max(0, Math.min(100, prev.san + (stats.san_delta || 0))),
            money: prev.money + (stats.money_delta || 0),
            turn: nextTurnNum || prev.turn + 1,
            displayText: newDisplayText,
            nextOptions: nextTurn ? (nextTurn.player_choices || []).map((c: any) => c.text) : [],
            isEnd: nextTurn ? nextTurn.is_end : true,
            history: [...prev.history, {
              turn: prev.turn,
              text: newDisplayText,
              rawJson: '',
              narrativeState: prev.narrativeState || {}
            }],
            eventScript: nextTurn && nextTurn.is_end ? null : prev.eventScript
          }));
          return;
        }
      }
    }
    
    // --- [BACKEND FALLBACK / TRANSITION] ---
    set({ isLoading: true, pendingChoice: choice });
    try {
      const isTransition = isTransitionChoice(choice) || state.isEnd;
      const turnReq = {
        choice,
        active_roommates: state.active_roommates,
        current_evt_id: state.current_evt_id,
        is_transition: isTransition,
        chapter: state.chapter,
        turn: state.turn,
        san: state.san,
        money: state.money,
        gpa: state.gpa,
        hygiene: state.hygiene,
        reputation: state.reputation,
        affinity: state.affinity,
        save_id: state.currentSaveId
      };
      
      const data = await gameApi.performTurn(turnReq, undefined, state.currentSaveId);
      set((prev) => ({
        isLoading: false,
        pendingChoice: null,
        san: data.san,
        money: data.money,
        gpa: data.gpa,
        hygiene: data.hygiene,
        reputation: data.reputation,
        chapter: data.chapter,
        turn: data.turn,
        current_evt_id: data.current_evt_id,
        current_scene: data.current_scene || prev.current_scene || '宿舍',
        player_name: data.player_name || prev.player_name || '陆陈安然',
        affinity: data.affinity,
        narrativeState: data.narrative_state || prev.narrativeState || {},
        systemState: data.system_state || prev.systemState || {},
        systemDailyPlan: data.system_daily_plan || prev.systemDailyPlan || null,
        systemKeyResolution: data.system_key_resolution || null,
        weeklySummary: data.weekly_summary || null,
        displayText: data.display_text,
        nextOptions: data.next_options || [],
        isEnd: data.is_end || false,
        history: [...prev.history, {
          turn: data.turn,
          text: isTransition ? data.display_text : `【你的选择】: ${choice}\n\n${data.display_text}`,
          rawJson: data.res_text || '',
          narrativeState: data.narrative_state || prev.narrativeState || {}
        }],
        wechatNotifications: data.wechat_notifications || prev.wechatNotifications,
        phoneSystemEnabled: data.phone_system_enabled !== false,
        isPhoneOpen: (data.phone_system_enabled === false) ? false : prev.isPhoneOpen,
        eventScript: data.event_script || null
        ,
        turnDebug: (data.timings || data.prompt_diagnostics || data.render_source || data.ai_usage || data.state_delta)
          ? {
              timings: data.timings || undefined,
              prompt_diagnostics: data.prompt_diagnostics || undefined,
              render_source: data.render_source || undefined,
              ai_usage: data.ai_usage || undefined,
              state_delta: data.state_delta || undefined,
            }
          : null
      }));

      // 性能优化：如果在 transition 之后拿到了新剧本，则无需预取
      if (!data.event_script && data.next_options && data.next_options.length > 0 && !data.is_end) {
          get().prefetch(data.next_options[0]);
      }
    } catch (e) {
      console.error(e);
      set({ isLoading: false, pendingChoice: null });
    }
  },

  prefetch: async (choice: string) => {
    const state = get();
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
        affinity: state.affinity,
        save_id: state.currentSaveId
      };
      await gameApi.prefetch(turnReq, undefined, state.currentSaveId);
    } catch (e) {
      console.warn('Prefetch failed (silent):', e);
    }
  },

  clearWechatNotifications: () => {
      set({ wechatNotifications: [] });
  },

  togglePhone: (open?: boolean) => {
      set((state) => {
        if (!state.phoneSystemEnabled) {
          return { isPhoneOpen: false };
        }
        return { isPhoneOpen: open !== undefined ? open : !state.isPhoneOpen };
      });
  },

  setTypewriterSpeed: (speed: number) => {
      set({ typewriterSpeed: speed });
  },

  loadSave: async (slotId: number) => {
      set({ isLoading: true });
      try {
          const res = await gameApi.loadGame(slotId);
          const gameState = res.data;
          set({
              currentSaveId: `slot_${slotId}`,
              isPlaying: true,
              isLoading: false,
              pendingChoice: null,
              san: gameState.san,
              money: gameState.money,
              gpa: gameState.gpa,
              // Note: some fields might be slightly different in SaveGameRequest vs GameTurnRequest
              // but app.py SaveGameRequest has what we need
              chapter: gameState.chapter,
              turn: gameState.turn,
              current_evt_id: gameState.current_evt_id,
              current_scene: gameState.current_scene || '宿舍',
              player_name: gameState.player_name || '陆陈安然',
              active_roommates: gameState.active_roommates,
              narrativeState: gameState.narrative_state || {},
              systemState: gameState.system_state || {},
              systemDailyPlan: gameState.system_daily_plan || null,
              systemKeyResolution: gameState.system_key_resolution || null,
              weeklySummary: null,
              // affinity, hygiene, etc should ideally be in save too
              displayText: "存档已成功加载，您可以继续之前的进度。",
              nextOptions: ["【进入下一幕】继续当前存档"],
              isEnd: false,
              history: gameState.history || [],
              wechatNotifications: []
              ,
              phoneSystemEnabled: true
              ,
              turnDebug: null
          });
      } catch (e) {
          console.error(e);
          set({ isLoading: false, pendingChoice: null });
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
              narrative_state: state.narrativeState,
              system_state: state.systemState,
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
              pendingChoice: null,
              san: 100,
              money: 2000,
              gpa: 4.0,
              hygiene: 100,
              reputation: 100,
              chapter: 1,
              turn: 0,
              current_evt_id: '',
              current_scene: '宿舍',
              player_name: '陆陈安然',
              narrativeState: {},
              systemState: {},
              systemDailyPlan: null,
              systemKeyResolution: null,
              weeklySummary: null,
              history: [],
              wechatNotifications: [],
              phoneSystemEnabled: true,
              isPhoneOpen: false,
              displayText: '',
              turnDebug: null
          });
      } catch (e) {
          console.error('Failed to reset game:', e);
      }
  }
}));
