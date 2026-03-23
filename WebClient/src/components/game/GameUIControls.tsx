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
      <div className="flex flex-wrap justify-end gap-2 max-w-[620px]">
      {phoneSystemEnabled && (
        <button
          onClick={onTogglePhone}
          className="flex items-center justify-center w-10 h-10 text-[var(--color-cyan-dark)] hover:text-[var(--color-cyan-main)] transition-all relative"
          title="手机"
          aria-label="打开手机"
        >
          <Smartphone size={16} className="text-[var(--color-cyan-main)]" />
          {wechatNotificationCount > 0 && (
            <div className="absolute -top-1 -right-1 w-5 h-5 bg-yellow-500 rounded-full border-2 border-white text-[10px] text-white font-black flex items-center justify-center shadow-lg animate-bounce z-50">
              {wechatNotificationCount}
            </div>
          )}
        </button>
      )}
      <button
        onClick={onSaveGame}
        className="flex items-center justify-center w-10 h-10 text-[var(--color-cyan-dark)] hover:text-[var(--color-cyan-main)] transition-all"
        title="保存进度"
        aria-label="保存进度"
      >
        <Save size={16} className="text-[var(--color-cyan-main)]" />
      </button>
      <button
        onClick={onShowHistory}
        className="flex items-center justify-center w-10 h-10 text-[var(--color-cyan-dark)] hover:text-[var(--color-cyan-main)] transition-all"
        title="回顾记录"
        aria-label="回顾记录"
      >
        <ScrollText size={16} className="text-[var(--color-yellow-main)] drop-shadow-sm" />
      </button>
      <button
        onClick={onBackToMenu}
        className="flex items-center justify-center w-10 h-10 text-[var(--color-cyan-dark)] hover:text-[var(--color-cyan-main)] transition-all"
        title="返回主菜单"
        aria-label="返回主菜单"
      >
        <House size={16} className="text-[var(--color-cyan-main)]" />
      </button>
      </div>
    </div>
  );
};
