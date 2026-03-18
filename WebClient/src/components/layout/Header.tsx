import { Menu, Github } from 'lucide-react';
import { PROJECT_CONFIG } from '../../config';

interface HeaderProps {
  onMenuClick: () => void;
  activeTab: string;
  isSidebarOpen: boolean;
}

export const Header = ({ onMenuClick, activeTab, isSidebarOpen }: HeaderProps) => {
  const getTitle = () => {
    switch (activeTab) {
      case 'game': return '当前游戏';
      case 'workshop': return '创意工坊';
      case 'mods': return '本地模组';
      case 'editor': return '本地编撰区';
      case 'settings': return '系统设置';
      default: return '';
    }
  };

  return (
    <header className="w-full h-20 flex items-center justify-between px-6 md:px-10 bg-white/80 backdrop-blur-md border-b-2 border-[var(--color-cyan-main)]/20 shrink-0 z-10 relative">
      <div className="flex items-center flex-1">
        {!isSidebarOpen && (
          <button
            onClick={onMenuClick}
            className="mr-6 p-3 rounded-2xl bg-[var(--color-cyan-light)] text-[var(--color-cyan-dark)] hover:bg-[var(--color-cyan-main)] hover:text-white transition-all shadow-sm"
          >
            <Menu size={24} />
          </button>
        )}
        <div className="flex flex-col">
          <span className="text-[9px] font-black text-[var(--color-cyan-main)] uppercase tracking-[0.4em] mb-1">Dorm Diary</span>
          <h2 className="text-xl font-black text-[var(--color-cyan-dark)] tracking-tight truncate">
            {getTitle()}
          </h2>
        </div>
      </div>
      <div className="hidden md:flex flex-shrink-0">
        <a
          href={PROJECT_CONFIG.links.github}
          target="_blank"
          rel="noreferrer"
          className="flex items-center px-6 py-2.5 bg-[var(--color-cyan-light)] text-[var(--color-cyan-main)] hover:bg-[var(--color-cyan-main)] hover:text-white border border-[var(--color-cyan-main)]/20 rounded-full text-xs font-black uppercase tracking-widest transition-all shadow-sm"
        >
          <Github size={18} className="mr-2" />
          参与建设
        </a>
      </div>
    </header>
  );
};
