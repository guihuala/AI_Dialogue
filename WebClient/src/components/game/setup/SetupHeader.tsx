import { ArrowLeft } from 'lucide-react';

interface SetupHeaderProps {
  onBack: () => void;
  isReady: boolean;
}

export const SetupHeader = ({ onBack, isReady }: SetupHeaderProps) => {
  return (
    <div className="p-8 border-b border-[var(--color-cyan-main)]/10 flex items-center justify-between shrink-0 bg-white/50">
      <div className="flex items-center">
        <button
          onClick={onBack}
          className="mr-6 p-3 bg-white hover:bg-[var(--color-cyan-main)] hover:text-white rounded-xl transition-all shadow-sm border border-[var(--color-cyan-main)]/20 group"
        >
          <ArrowLeft size={20} className="group-hover:-translate-x-1 transition-transform" />
        </button>
        <div>
          <h2 className="text-3xl font-black text-[var(--color-cyan-dark)] tracking-tight">开始新游戏</h2>
          <p className="mt-1 text-sm text-[var(--color-cyan-dark)]/60">先确定模组、舍友和局长。</p>
        </div>
      </div>
      {isReady && (
        <div className="hidden md:flex items-center bg-[var(--color-yellow-main)]/20 px-4 py-2 rounded-full border border-[var(--color-yellow-main)]/30 animate-in zoom-in duration-300">
          <span className="text-sm font-black text-[var(--color-yellow-dark)]">已可开始</span>
        </div>
      )}
    </div>
  );
};
