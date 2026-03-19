import { ScrollText, X } from 'lucide-react';
import { ReactNode, RefObject } from 'react';

interface HistoryItem {
  turn: number;
  text: string;
  rawJson?: string;
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
          </div>
        ))}
      </div>
    </div>
  );
};
