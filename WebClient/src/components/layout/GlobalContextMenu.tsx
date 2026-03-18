import { PlayCircle, Save, EyeOff, FastForward, Settings, RefreshCw, Github } from 'lucide-react';

interface GlobalContextMenuProps {
  x: number;
  y: number;
  setActiveTab: (tab: any) => void;
  showUI: boolean;
  setShowUI: (show: boolean) => void;
  showToastMsg: (msg: string) => void;
  onClose: () => void;
}

export const GlobalContextMenu = ({
  x,
  y,
  setActiveTab,
  showUI,
  setShowUI,
  showToastMsg,
  onClose
}: GlobalContextMenuProps) => {
  return (
    <div
      className="fixed z-[9999] bg-white/95 backdrop-blur-md border-2 border-[var(--color-cyan-main)]/30 rounded-[1rem] shadow-[0_20px_60px_rgba(0,188,212,0.15)] p-3 w-60 animate-in slide-in-from-bottom-5 zoom-in-95 fade-in-0 duration-300 ease-[cubic-bezier(0.16,1,0.3,1)] overflow-hidden"
      style={{
        top: Math.min(y, window.innerHeight - 320),
        left: Math.min(x, window.innerWidth - 240)
      }}
      onClick={(e) => e.stopPropagation()}
    >
      <div className="flex flex-col space-y-1">
        <div className="px-3 py-1.5 text-[10px] font-black text-[var(--color-cyan-main)] uppercase tracking-[0.2em] animate-in fade-in slide-in-from-left-2 duration-300 fill-mode-both">快速操作</div>
        <button
          onClick={() => { setActiveTab('game'); onClose(); }}
          className="flex items-center px-4 py-2.5 text-xs font-black text-[var(--color-cyan-dark)] hover:bg-[var(--color-cyan-main)] hover:text-white rounded-2xl transition-all hover:translate-x-1 animate-in fade-in slide-in-from-left-3 duration-300 delay-75 fill-mode-both shadow-sm hover:shadow-md"
        >
          <PlayCircle size={16} className="mr-3 text-[var(--color-cyan-main)] group-hover:text-white" /> 继续游戏
        </button>
        <button
          onClick={() => { showToastMsg("对局已自动存档"); onClose(); }}
          className="flex items-center px-4 py-2.5 text-xs font-black text-[var(--color-cyan-dark)] hover:bg-[var(--color-cyan-main)] hover:text-white rounded-2xl transition-all hover:translate-x-1 animate-in fade-in slide-in-from-left-3 duration-300 delay-100 fill-mode-both shadow-sm hover:shadow-md"
        >
          <Save size={16} className="mr-3 text-[var(--color-cyan-main)]" /> 快速存档
        </button>
        <button
          onClick={() => { setShowUI(!showUI); onClose(); }}
          className="flex items-center px-4 py-2.5 text-xs font-black text-[var(--color-cyan-dark)] hover:bg-[var(--color-cyan-main)] hover:text-white rounded-2xl transition-all hover:translate-x-1 animate-in fade-in slide-in-from-left-3 duration-300 delay-150 fill-mode-both shadow-sm hover:shadow-md"
        >
          <EyeOff size={16} className="mr-3 text-[var(--color-cyan-main)]" /> {showUI ? '隐藏界面 (预览)' : '显示界面'}
        </button>
        <button
          onClick={() => { showToastMsg("正在加速跳过..."); onClose(); }}
          className="flex items-center px-4 py-2.5 text-xs font-black text-[var(--color-cyan-dark)] hover:bg-[var(--color-cyan-main)] hover:text-white rounded-2xl transition-all hover:translate-x-1 animate-in fade-in slide-in-from-left-3 duration-300 delay-200 fill-mode-both shadow-sm hover:shadow-md"
        >
          <FastForward size={16} className="mr-3 text-[var(--color-cyan-main)]" /> 跳过剧情
        </button>

        <div className="h-px bg-[var(--color-cyan-main)]/10 my-3 mx-2" />
        <div className="px-3 py-1.5 text-[10px] font-black text-[var(--color-cyan-main)] uppercase tracking-[0.2em] animate-in fade-in duration-300 delay-250 fill-mode-both">系统菜单</div>

        <button
          onClick={() => { setActiveTab('settings'); onClose(); }}
          className="flex items-center px-4 py-2.5 text-xs font-black text-[var(--color-cyan-dark)] hover:bg-[var(--color-cyan-main)] hover:text-white rounded-2xl transition-all hover:translate-x-1 animate-in fade-in slide-in-from-left-3 duration-300 delay-300 fill-mode-both shadow-sm hover:shadow-md"
        >
          <Settings size={16} className="mr-3 text-[var(--color-cyan-main)]" /> 系统设定
        </button>
        <button
          onClick={() => { window.location.reload(); }}
          className="flex items-center px-4 py-2.5 text-xs font-black text-rose-500 hover:bg-rose-500 hover:text-white rounded-2xl transition-all hover:translate-x-1 animate-in fade-in slide-in-from-left-4 duration-300 delay-350 fill-mode-both shadow-sm hover:shadow-md"
        >
          <RefreshCw size={16} className="mr-3" /> 强制刷新界面
        </button>
      </div>
    </div>
  );
};
