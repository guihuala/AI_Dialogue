import { Rocket, RefreshCw } from 'lucide-react';

interface StartGameButtonProps {
  disabled: boolean;
  isLoading: boolean;
  onClick: () => void;
}

export const StartGameButton = ({ disabled, isLoading, onClick }: StartGameButtonProps) => {
  return (
    <div className="flex justify-end relative w-full max-w-[260px]">
      <button
        disabled={disabled || isLoading}
        onClick={onClick}
        className="group relative w-full px-8 py-3.5 bg-[var(--color-cyan-dark)] hover:bg-[var(--color-cyan-main)] text-white rounded-2xl font-black transition-all shadow-xl shadow-cyan-900/20 active:scale-[0.99] disabled:opacity-50 disabled:grayscale disabled:cursor-wait flex items-center justify-center overflow-hidden min-w-[220px]"
        style={{ transform: isLoading ? 'none' : '' }}
      >
        <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white/5 to-transparent -translate-x-full group-hover:animate-shimmer" />
        {isLoading ? (
          <>
            <RefreshCw className="mr-3 animate-spin" size={18} />
            <span className="animate-pulse">加载游戏...</span>
          </>
        ) : (
          <>
            <Rocket className="mr-3" size={18} />
            开始游戏
          </>
        )}
      </button>
    </div>
  );
};
