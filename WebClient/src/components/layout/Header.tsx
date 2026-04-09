import { useEffect, useState } from 'react';
import { Menu, Github, UserRound } from 'lucide-react';
import { PROJECT_CONFIG } from '../../config';
import { gameApi } from '../../api/gameApi';

interface HeaderProps {
  onMenuClick: () => void;
  onAccountClick: () => void;
  activeTab: string;
  isSidebarOpen: boolean;
}

export const Header = ({ onMenuClick, onAccountClick, activeTab, isSidebarOpen }: HeaderProps) => {
  const [accountInfo, setAccountInfo] = useState<any>(null);

  useEffect(() => {
    let cancelled = false;

    const syncAccount = async () => {
      try {
        const res = await gameApi.getAccountMe();
        if (!cancelled) {
          setAccountInfo(res?.data || null);
        }
      } catch (error) {
        if (!cancelled) {
          setAccountInfo(null);
        }
      }
    };

    syncAccount();
    const handleFocus = () => { syncAccount(); };
    const handleStorage = () => { syncAccount(); };
    window.addEventListener('focus', handleFocus);
    window.addEventListener('storage', handleStorage);
    return () => {
      cancelled = true;
      window.removeEventListener('focus', handleFocus);
      window.removeEventListener('storage', handleStorage);
    };
  }, [activeTab]);

  const getTitle = () => {
    switch (activeTab) {
      case 'game': return '主界面';
      case 'workshop': return '创意工坊';
      case 'mods': return '模组';
      case 'account': return '用户';
      case 'editor': return '编辑';
      case 'settings': return '设置';
      default: return '';
    }
  };

  const isLoggedIn = accountInfo?.auth_mode === 'account' && accountInfo?.account;
  const accountLabel = isLoggedIn ? `账户：${accountInfo.account.username}` : '访客模式';

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
          <h2 className="text-xl font-black text-[var(--color-cyan-dark)] tracking-tight truncate">
            {getTitle()}
          </h2>
        </div>
      </div>
      <div className="hidden md:flex flex-shrink-0 items-center gap-3">
        <button
          onClick={onAccountClick}
          title={accountLabel}
          className={`flex h-11 w-11 items-center justify-center rounded-2xl border shadow-sm transition-all ${
            isLoggedIn
              ? 'bg-emerald-50 text-emerald-600 border-emerald-200 hover:bg-emerald-100'
              : 'bg-amber-50 text-amber-700 border-amber-200 hover:bg-amber-100'
          }`}
        >
          <UserRound size={18} />
        </button>
        <a
          href={PROJECT_CONFIG.links.github}
          target="_blank"
          rel="noreferrer"
          title="参与建设"
          className="flex h-11 w-11 items-center justify-center rounded-2xl border border-[var(--color-cyan-main)]/20 bg-[var(--color-cyan-light)] text-[var(--color-cyan-main)] shadow-sm transition-all hover:bg-[var(--color-cyan-main)] hover:text-white"
        >
          <Github size={18} />
        </a>
      </div>
    </header>
  );
};
