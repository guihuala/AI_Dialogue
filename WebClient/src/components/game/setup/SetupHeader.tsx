import { ArrowLeft } from 'lucide-react';

interface SetupHeaderProps {
  onBack: () => void;
}

export const SetupHeader = ({ onBack }: SetupHeaderProps) => {
  return (
    <div className="px-5 py-4 md:px-8 md:py-5 border-b border-[var(--color-cyan-main)]/10 flex items-center justify-between shrink-0 bg-white/70">
      <div className="flex items-center min-w-0">
        <button
          onClick={onBack}
          className="mr-4 md:mr-5 p-3 bg-white hover:bg-[var(--color-cyan-main)] hover:text-white rounded-xl transition-all shadow-sm border border-[var(--color-cyan-main)]/20 group shrink-0"
        >
          <ArrowLeft size={20} className="group-hover:-translate-x-1 transition-transform" />
        </button>
        <div className="min-w-0">
          <h2 className="text-2xl md:text-3xl font-black text-[var(--color-cyan-dark)] tracking-tight">开始新游戏</h2>
        </div>
      </div>
    </div>
  );
};
