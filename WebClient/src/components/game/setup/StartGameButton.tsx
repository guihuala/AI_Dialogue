import { Rocket, RefreshCw } from 'lucide-react';

interface StartGameButtonProps {
  disabled: boolean;
  isLoading: boolean;
  onClick: () => void;
}

export const StartGameButton = ({ disabled, isLoading, onClick }: StartGameButtonProps) => {
  return (
    <div className="mt-auto flex justify-center pb-8 border-t border-dashed border-[var(--color-cyan-main)]/20 pt-12 relative">
      <button
        disabled={disabled || isLoading}
        onClick={onClick}
        className="group relative px-20 py-6 bg-[var(--color-cyan-dark)] hover:bg-[var(--color-cyan-main)] text-white rounded-2xl font-black tracking-[0.4em] uppercase transition-all shadow-2xl shadow-cyan-900/40 hover:-translate-y-1 active:translate-y-0 disabled:opacity-50 disabled:grayscale disabled:hover:translate-y-0 disabled:cursor-wait flex items-center justify-center overflow-hidden min-w-[320px]"
        style={{ transform: isLoading ? 'none' : '' }}
      >
        <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white/5 to-transparent -translate-x-full group-hover:animate-shimmer" />
        {isLoading ? (
          <>
            <RefreshCw className="mr-4 animate-spin" size={20} />
            <span className="animate-pulse">加载游戏...</span>
          </>
        ) : (
          <>
            <Rocket className="mr-4 group-hover:animate-bounce" size={20} />
            开始游戏
          </>
        )}
      </button>
    </div>
  );
};
