import { Smartphone, Save, ScrollText, House } from 'lucide-react';

interface GameUIControlsProps {
  onTogglePhone: () => void;
  onSaveGame: () => void;
  onShowHistory: () => void;
  onBackToMenu: () => void;
  wechatNotificationCount: number;
}

export const GameUIControls = ({
  onTogglePhone,
  onSaveGame,
  onShowHistory,
  onBackToMenu,
  wechatNotificationCount
}: GameUIControlsProps) => {
  return (
    <div className="absolute top-6 right-6 z-30 flex space-x-3 pointer-events-auto">
      <button
        onClick={onTogglePhone}
        className="flex items-center px-4 py-2 bg-white/90 hover:bg-white text-[var(--color-cyan-dark)] backdrop-blur-md rounded-full border border-[var(--color-cyan-main)]/30 shadow-lg transition-all font-black text-sm tracking-widest uppercase relative"
      >
        <Smartphone size={16} className="mr-2 text-[var(--color-cyan-main)]" /> 打开手机
        {wechatNotificationCount > 0 && (
          <div className="absolute -top-1 -right-1 w-5 h-5 bg-yellow-500 rounded-full border-2 border-white text-[10px] text-white font-black flex items-center justify-center shadow-lg animate-bounce z-50">
            {wechatNotificationCount}
          </div>
        )}
      </button>
      <button
        onClick={onSaveGame}
        className="flex items-center px-4 py-2 bg-white/90 hover:bg-white text-[var(--color-cyan-dark)] backdrop-blur-md rounded-full border border-[var(--color-cyan-main)]/30 shadow-lg transition-all font-black text-sm tracking-widest uppercase"
      >
        <Save size={16} className="mr-2 text-[var(--color-cyan-main)]" /> 保存进度
      </button>
      <button
        onClick={onShowHistory}
        className="flex items-center px-4 py-2 bg-white/90 hover:bg-white text-[var(--color-cyan-dark)] backdrop-blur-md rounded-full border border-[var(--color-cyan-main)]/30 shadow-lg transition-all font-black text-sm tracking-widest uppercase"
      >
        <ScrollText size={16} className="mr-2 text-[var(--color-yellow-main)] drop-shadow-sm" /> 回顾记录
      </button>
      <button
        onClick={onBackToMenu}
        className="flex items-center px-4 py-2 bg-white/90 hover:bg-white text-[var(--color-cyan-dark)] backdrop-blur-md rounded-full border border-[var(--color-cyan-main)]/30 shadow-lg transition-all font-black text-sm tracking-widest uppercase"
      >
        <House size={16} className="mr-2 text-[var(--color-cyan-main)]" /> 返回主菜单
      </button>
    </div>
  );
};
