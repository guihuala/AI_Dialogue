import { ScrollText, X } from 'lucide-react';
import { ReactNode, RefObject } from 'react';

interface HistoryItem {
  turn: number;
  text: string;
  rawJson?: string;
  narrativeState?: Record<string, any>;
}

interface HistoryPanelProps {
  history: HistoryItem[];
  showHistory: boolean;
  setShowHistory: (show: boolean) => void;
  historyScrollRef: RefObject<HTMLDivElement>;
  parseMarktext: (text: string) => ReactNode;
}

export const HistoryPanel = ({
  history,
  showHistory,
  setShowHistory,
  historyScrollRef,
  parseMarktext
}: HistoryPanelProps) => {
  if (!showHistory) return null;

  return (
    <div className="absolute inset-0 z-40 bg-black/80 backdrop-blur-lg flex flex-col p-6 overflow-hidden">
      <div className="flex justify-between items-center mb-6 shrink-0">
        <h3 className="text-2xl font-black text-[var(--color-cyan-main)] tracking-widest uppercase flex items-center">
          <ScrollText className="mr-3" /> 对话记录
        </h3>
        <button
          onClick={() => setShowHistory(false)}
          className="p-2 bg-white/10 hover:bg-red-500/80 text-white rounded-full transition-colors"
        >
          <X size={24} />
        </button>
      </div>
      <div
        ref={historyScrollRef}
        className="flex-1 overflow-y-auto pr-4 space-y-6 custom-scrollbar"
      >
        {history.length === 0 && <div className="text-white/50 text-center mt-10 font-bold">暂无记录</div>}
        {history.map((h, i) => (
          <div key={i} className="bg-white/5 border border-white/10 p-4 rounded-xl">
            <span className="text-[var(--color-yellow-main)] text-xs font-black tracking-widest uppercase mb-2 block">
              回合 {h.turn}
            </span>
            <div className="text-white/90 whitespace-pre-wrap font-bold leading-relaxed">
              {parseMarktext(h.text)}
            </div>
            {h.rawJson && (
              <details className="mt-3">
                <summary className="cursor-pointer text-[10px] tracking-widest uppercase font-black text-cyan-300/90">
                  查看 AI 原始 JSON
                </summary>
                <div className="mt-2 flex justify-end">
                  <button
                    onClick={() => navigator.clipboard.writeText(h.rawJson || '')}
                    className="text-[10px] px-3 py-1 rounded-lg bg-cyan-500/20 text-cyan-200 hover:bg-cyan-500/40 transition-colors font-black tracking-widest uppercase"
                  >
                    复制 JSON
                  </button>
                </div>
                <pre className="mt-2 text-[11px] leading-relaxed text-cyan-100/95 bg-black/40 border border-white/10 rounded-lg p-3 overflow-x-auto whitespace-pre-wrap">
                  {h.rawJson}
                </pre>
              </details>
            )}
            {h.narrativeState && Object.keys(h.narrativeState).length > 0 && (
              <details className="mt-3">
                <summary className="cursor-pointer text-[10px] tracking-widest uppercase font-black text-emerald-300/90">
                  查看剧情状态摘要
                </summary>
                <div className="mt-2 flex justify-end">
                  <button
                    onClick={() => navigator.clipboard.writeText(JSON.stringify(h.narrativeState || {}, null, 2))}
                    className="text-[10px] px-3 py-1 rounded-lg bg-emerald-500/20 text-emerald-200 hover:bg-emerald-500/40 transition-colors font-black tracking-widest uppercase"
                  >
                    复制状态
                  </button>
                </div>
                <div className="mt-2 bg-black/40 border border-white/10 rounded-lg p-3 space-y-3">
                  {Array.isArray(h.narrativeState.player_arc) && h.narrativeState.player_arc.length > 0 && (
                    <div>
                      <div className="text-[10px] font-black tracking-widest uppercase text-emerald-300/80 mb-1">主角弧光</div>
                      <div className="space-y-1">
                        {h.narrativeState.player_arc.map((item: string, idx: number) => (
                          <div key={idx} className="text-[11px] text-white/90 leading-relaxed">- {item}</div>
                        ))}
                      </div>
                    </div>
                  )}
                  {h.narrativeState.room_tension && (
                    <div>
                      <div className="text-[10px] font-black tracking-widest uppercase text-emerald-300/80 mb-1">宿舍局势</div>
                      <div className="text-[11px] text-white/90 leading-relaxed">{h.narrativeState.room_tension}</div>
                    </div>
                  )}
                  {Array.isArray(h.narrativeState.recent_impressions) && h.narrativeState.recent_impressions.length > 0 && (
                    <div>
                      <div className="text-[10px] font-black tracking-widest uppercase text-emerald-300/80 mb-1">最近形成的印象</div>
                      <div className="space-y-1">
                        {h.narrativeState.recent_impressions.map((item: string, idx: number) => (
                          <div key={idx} className="text-[11px] text-white/90 leading-relaxed">- {item}</div>
                        ))}
                      </div>
                    </div>
                  )}
                  {Array.isArray(h.narrativeState.active_threads) && h.narrativeState.active_threads.length > 0 && (
                    <div>
                      <div className="text-[10px] font-black tracking-widest uppercase text-emerald-300/80 mb-1">发酵中的线头</div>
                      <div className="space-y-1">
                        {h.narrativeState.active_threads.map((item: string, idx: number) => (
                          <div key={idx} className="text-[11px] text-white/90 leading-relaxed">- {item}</div>
                        ))}
                      </div>
                    </div>
                  )}
                  {h.narrativeState.mood_flags && Object.keys(h.narrativeState.mood_flags).length > 0 && (
                    <div>
                      <div className="text-[10px] font-black tracking-widest uppercase text-emerald-300/80 mb-1">情绪标签</div>
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                        {Object.entries(h.narrativeState.mood_flags).map(([name, mood]) => (
                          <div key={name} className="text-[11px] text-white/90 leading-relaxed">
                            <span className="text-emerald-200 font-black">{name}</span>
                            <span className="text-white/70"> : </span>
                            <span>{String(mood)}</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                  {h.narrativeState.relationship_state && Object.keys(h.narrativeState.relationship_state).length > 0 && (
                    <div>
                      <div className="text-[10px] font-black tracking-widest uppercase text-emerald-300/80 mb-1">关系状态</div>
                      <div className="space-y-2">
                        {Object.entries(h.narrativeState.relationship_state).slice(0, 6).map(([name, rel]: any) => (
                          <div key={name} className="rounded-lg bg-white/5 border border-white/10 px-2.5 py-2">
                            <div className="flex items-center justify-between">
                              <span className="text-[11px] text-emerald-200 font-black">{name}</span>
                              <span className="text-[10px] text-white/85 font-black">{rel?.relationship_stage || '熟悉'}</span>
                            </div>
                            <div className="mt-1 text-[10px] text-white/75">
                              信任 {Math.round(Number(rel?.trust || 0))} / 紧张 {Math.round(Number(rel?.tension || 0))} / 亲密 {Math.round(Number(rel?.intimacy || 0))}
                            </div>
                            {Array.isArray(rel?.recent_flags) && rel.recent_flags.length > 0 && (
                              <div className="mt-1 text-[10px] text-white/65">
                                最近：{String(rel.recent_flags[0])}
                              </div>
                            )}
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                  {Array.isArray(h.narrativeState.long_term_milestones) && h.narrativeState.long_term_milestones.length > 0 && (
                    <div>
                      <div className="text-[10px] font-black tracking-widest uppercase text-emerald-300/80 mb-1">长期里程碑</div>
                      <div className="space-y-1">
                        {h.narrativeState.long_term_milestones.slice(0, 5).map((item: string, idx: number) => (
                          <div key={idx} className="text-[11px] text-white/90 leading-relaxed">- {item}</div>
                        ))}
                      </div>
                    </div>
                  )}
                  <details className="pt-1">
                    <summary className="cursor-pointer text-[10px] tracking-widest uppercase font-black text-white/45">
                      查看完整状态 JSON
                    </summary>
                    <pre className="mt-2 text-[11px] leading-relaxed text-emerald-100/95 bg-black/30 border border-white/10 rounded-lg p-3 overflow-x-auto whitespace-pre-wrap">
                      {JSON.stringify(h.narrativeState, null, 2)}
                    </pre>
                  </details>
                </div>
              </details>
            )}
          </div>
        ))}
      </div>
    </div>
  );
};
