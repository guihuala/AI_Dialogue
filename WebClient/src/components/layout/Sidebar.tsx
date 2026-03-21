import { X, Github } from 'lucide-react';
import { PROJECT_CONFIG } from '../../config';

interface SidebarProps {
  isOpen: boolean;
  onClose: () => void;
  activeTab: string;
  setActiveTab: (tab: any) => void;
  showUI: boolean;
}

export const Sidebar = ({
  isOpen,
  onClose,
  activeTab,
  setActiveTab,
  showUI
}: SidebarProps) => {
  const tabs = [
    { id: 'game', label: '游玩' },
    { id: 'mods', label: '模组' },
    { id: 'settings', label: '设置' },
  ];

  return (
    <>
      {/* Sidebar Overlay */}
      {isOpen && (
        <div
          className="fixed inset-0 bg-black/50 z-[1200] transition-opacity"
          onClick={onClose}
        />
      )}

      {/* Sidebar Content */}
      <aside className={`fixed inset-y-0 left-0 w-64 flex flex-col transition-transform duration-500 ease-in-out shadow-2xl z-[1300] shrink-0 bg-[var(--color-cyan-main)] text-white ${(isOpen && showUI) ? 'translate-x-0' : '-translate-x-full'}`}>
        <div className="h-20 flex items-center justify-between px-6 border-b border-white/10 shrink-0 bg-[var(--color-cyan-dark)]/20">
          <span className="text-xl font-black tracking-tight text-white flex flex-col">
            <span className="text-[var(--color-yellow-main)] text-xs uppercase tracking-[0.3em] mb-1">Dorm Life</span>
            宿舍日志 <span className="text-[10px] text-white/50 font-bold">Project Memories</span>
          </span>
          <button onClick={onClose} className="text-white hover:text-[var(--color-yellow-main)] transition-colors">
            <X size={24} />
          </button>
        </div>
        <nav className="flex-1 py-8 overflow-y-auto space-y-3 custom-scrollbar px-3">
          {tabs.map((tab) => (
            <div
              key={tab.id}
              onClick={() => { setActiveTab(tab.id); onClose(); }}
              className={`px-6 py-4 cursor-pointer text-sm font-black flex justify-start items-center transition-all rounded-2xl ${activeTab === tab.id ? 'bg-[var(--color-cyan-dark)]/40 text-[var(--color-yellow-main)] shadow-inner border-l-4 border-[var(--color-yellow-main)]' : 'text-white hover:bg-white/10 hover:text-[var(--color-yellow-main)]'}`}
            >
              <span className="uppercase tracking-[0.2em]">{tab.label}</span>
            </div>
          ))}
        </nav>
        <div className="p-6 border-t border-white/10 bg-[var(--color-cyan-dark)]/20 shrink-0">
          <a
            href={PROJECT_CONFIG.links.feedback}
            target="_blank"
            rel="noreferrer"
            className="flex items-center justify-center p-4 w-full bg-white/10 hover:bg-[var(--color-yellow-main)] hover:text-[var(--color-cyan-dark)] rounded-2xl text-white transition-all text-xs font-black uppercase tracking-widest shadow-md group"
          >
            <Github size={16} className="mr-2 group-hover:rotate-12 transition-transform" /> 反馈建议
          </a>
        </div>
      </aside>
    </>
  );
};
