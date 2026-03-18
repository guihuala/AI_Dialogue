import { RefreshCcw } from 'lucide-react';

interface EndOverlayProps {
  isLoading: boolean;
  onRestart: () => void;
}

export const EndOverlay = ({ isLoading, onRestart }: EndOverlayProps) => {
  return (
    <div className="absolute inset-0 flex items-center justify-center bg-white/50 backdrop-blur-sm z-30 pointer-events-auto rounded-2xl">
      <div className="text-center w-full animate-in zoom-in duration-700">
        <h3 className="text-4xl font-black text-[var(--color-cyan-dark)] mb-8 drop-shadow-sm tracking-[0.5em] ml-[0.5em] uppercase">故事已落幕</h3>
        <button
          onClick={onRestart}
          disabled={isLoading}
          className="px-12 py-5 bg-gradient-to-br from-[var(--color-cyan-main)] to-[var(--color-cyan-dark)] text-white rounded-full font-black shadow-[0_10px_30px_rgba(0,188,212,0.4)] transition-all uppercase tracking-[0.3em] text-sm border-2 border-white/20 mx-auto disabled:opacity-50 disabled:cursor-wait flex items-center justify-center"
        >
          {isLoading ? (
            <>
              <RefreshCcw className="animate-spin mr-3" size={18} />
              <span className="animate-pulse">对话生成中...</span>
            </>
          ) : (
            <span className="hover:scale-105 active:scale-95 transition-transform inline-block">开启新的故事</span>
          )}
        </button>
      </div>
    </div>
  );
};
