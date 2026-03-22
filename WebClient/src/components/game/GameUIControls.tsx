import { Smartphone, Save, ScrollText, House } from 'lucide-react';

interface GameUIControlsProps {
  onTogglePhone: () => void;
  onSaveGame: () => void;
  onShowHistory: () => void;
  onBackToMenu: () => void;
  wechatNotificationCount: number;
  phoneSystemEnabled?: boolean;
}

export const GameUIControls = ({
  onTogglePhone,
  onSaveGame,
  onShowHistory,
  onBackToMenu,
  wechatNotificationCount,
  phoneSystemEnabled = true
}: GameUIControlsProps) => {
  return (
    <div className="absolute top-5 right-5 z-30 pointer-events-auto">
      <div className="rounded-2xl border border-[var(--color-cyan-main)]/25 bg-white/75 backdrop-blur-md p-2.5 shadow-xl">
      <div className="flex flex-wrap justify-end gap-2 max-w-[620px]">
      {phoneSystemEnabled && (
        <button
          onClick={onTogglePhone}
          className="flex items-center px-3.5 py-2 bg-white/90 hover:bg-white text-[var(--color-cyan-dark)] backdrop-blur-md rounded-full border border-[var(--color-cyan-main)]/30 shadow-lg transition-all font-black text-xs tracking-widest uppercase relative"
        >
          <Smartphone size={16} className="mr-2 text-[var(--color-cyan-main)]" /> 打开手机
          {wechatNotificationCount > 0 && (
            <div className="absolute -top-1 -right-1 w-5 h-5 bg-yellow-500 rounded-full border-2 border-white text-[10px] text-white font-black flex items-center justify-center shadow-lg animate-bounce z-50">
              {wechatNotificationCount}
            </div>
          )}
        </button>
      )}
      <button
        onClick={onSaveGame}
        className="flex items-center px-3.5 py-2 bg-white/90 hover:bg-white text-[var(--color-cyan-dark)] backdrop-blur-md rounded-full border border-[var(--color-cyan-main)]/30 shadow-lg transition-all font-black text-xs tracking-widest uppercase"
      >
        <Save size={16} className="mr-2 text-[var(--color-cyan-main)]" /> 保存进度
      </button>
      <button
        onClick={onShowHistory}
        className="flex items-center px-3.5 py-2 bg-white/90 hover:bg-white text-[var(--color-cyan-dark)] backdrop-blur-md rounded-full border border-[var(--color-cyan-main)]/30 shadow-lg transition-all font-black text-xs tracking-widest uppercase"
      >
        <ScrollText size={16} className="mr-2 text-[var(--color-yellow-main)] drop-shadow-sm" /> 回顾记录
      </button>
      <button
        onClick={onBackToMenu}
        className="flex items-center px-3.5 py-2 bg-white/90 hover:bg-white text-[var(--color-cyan-dark)] backdrop-blur-md rounded-full border border-[var(--color-cyan-main)]/30 shadow-lg transition-all font-black text-xs tracking-widest uppercase"
      >
        <House size={16} className="mr-2 text-[var(--color-cyan-main)]" /> 返回主菜单
      </button>
      </div>
      </div>
    </div>
  );
};
