import { useState, useEffect } from 'react';
import { RotateCw } from 'lucide-react';
import { GameView } from './components/GameView';
import { ModManager } from './components/ModManager';
import { SettingsPanel } from './components/SettingsPanel';
import { AccountPanel } from './components/AccountPanel';
import { PromptEditor } from './components/PromptEditor';
import { PhoneOverlay } from './components/PhoneOverlay';
import { AdminDashboard } from './components/AdminDashboard';

import { Sidebar } from './components/layout/Sidebar';
import { Header } from './components/layout/Header';
import { GlobalContextMenu } from './components/layout/GlobalContextMenu';
import { Toast } from './components/layout/Toast';
import { CustomCursor } from './components/layout/CustomCursor';
import { LoadingScreen } from './components/layout/LoadingScreen';
import { TabId, locationToTab, tabToPath } from './router/tabs';

function App() {
  const [activeTab, setActiveTab] = useState<TabId>(locationToTab(window.location));
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);
  const [contextMenu, setContextMenu] = useState<{ x: number, y: number } | null>(null);
  const [showUI, setShowUI] = useState(true);
  const [toast, setToast] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [viewport, setViewport] = useState(() => ({
    isMobile: window.innerWidth <= 900,
    isPortrait: window.innerHeight >= window.innerWidth
  }));

  const navigateToTab = (tab: TabId, options?: { replace?: boolean }) => {
    const path = tabToPath(tab);
    const currentPath = window.location.pathname;
    const currentHash = window.location.hash;
    if (currentPath === path && !currentHash) return;
    if (options?.replace) {
      window.history.replaceState({}, '', path);
    } else {
      window.history.pushState({}, '', path);
    }
  };

  const setActiveTabWithRoute = (tab: TabId, options?: { replace?: boolean }) => {
    setActiveTab(tab);
    navigateToTab(tab, options);
  };

  // Close context menu on click anywhere
  useEffect(() => {
    const syncTabFromLocation = () => {
      const tab = locationToTab(window.location);
      setActiveTab(tab);
      const canonical = tabToPath(tab);
      if (window.location.pathname !== canonical || window.location.hash) {
        window.history.replaceState({}, '', canonical);
      }
    };
    syncTabFromLocation();

    const handleClick = () => setContextMenu(null);
    const handleChangeTab = (e: Event) => {
      const detail = (e as CustomEvent<TabId>).detail;
      if (detail) setActiveTabWithRoute(detail);
    };

    window.addEventListener('click', handleClick);
    window.addEventListener('changeTab', handleChangeTab);
    window.addEventListener('popstate', syncTabFromLocation);
    window.addEventListener('hashchange', syncTabFromLocation);

    return () => {
      window.removeEventListener('click', handleClick);
      window.removeEventListener('changeTab', handleChangeTab);
      window.removeEventListener('popstate', syncTabFromLocation);
      window.removeEventListener('hashchange', syncTabFromLocation);
    };
  }, []);

  useEffect(() => {
    const handleViewportChange = () => {
      setViewport({
        isMobile: window.innerWidth <= 900,
        isPortrait: window.innerHeight >= window.innerWidth
      });
    };

    handleViewportChange();
    window.addEventListener('resize', handleViewportChange);
    window.addEventListener('orientationchange', handleViewportChange);

    return () => {
      window.removeEventListener('resize', handleViewportChange);
      window.removeEventListener('orientationchange', handleViewportChange);
    };
  }, []);

  const handleContextMenu = (e: React.MouseEvent) => {
    // Only show global context menu if target is not already handling its own context menu
    // (though e.preventDefault() in children will prevent this)
    e.preventDefault();
    setContextMenu({ x: e.clientX, y: e.clientY });
  };

  const showToastMsg = (msg: string) => {
    setToast(msg);
    setTimeout(() => setToast(null), 2000);
  };

  const shouldForceLandscape = viewport.isMobile && viewport.isPortrait;

  return (
    <div
      className="w-full flex h-screen text-[var(--color-cyan-dark)] bg-[var(--color-cyan-light)] overflow-hidden relative selection:bg-[var(--color-cyan-main)] selection:text-white"
      onContextMenu={handleContextMenu}
    >
      {isLoading && <LoadingScreen onFinished={() => setIsLoading(false)} />}
      <CustomCursor />

      {/* Toast Notification */}
      {toast && <Toast message={toast} />}

      {shouldForceLandscape && (
        <div className="fixed inset-0 z-[2000] flex items-center justify-center bg-[var(--color-cyan-light)]/96 px-6 text-center backdrop-blur-md">
          <div className="w-full max-w-sm rounded-[2rem] border border-[var(--color-cyan-main)]/15 bg-white/92 px-6 py-8 shadow-2xl">
            <div className="mx-auto flex h-16 w-16 items-center justify-center rounded-2xl bg-[var(--color-cyan-light)] text-[var(--color-cyan-main)] shadow-sm">
              <RotateCw size={28} />
            </div>
            <h2 className="mt-5 text-2xl font-black text-[var(--color-cyan-dark)]">请横屏使用</h2>
            <p className="mt-3 text-sm font-bold leading-relaxed text-[var(--color-cyan-dark)]/65">
              手机竖屏空间不足，很多编辑和操作按钮会错位。为了保证可玩性，请将设备横过来继续。
            </p>
          </div>
        </div>
      )}

      {/* Custom Context Menu */}
      {contextMenu && (
        <GlobalContextMenu
          x={contextMenu.x}
          y={contextMenu.y}
          setActiveTab={setActiveTabWithRoute}
          showUI={showUI}
          setShowUI={setShowUI}
          showToastMsg={showToastMsg}
          onClose={() => setContextMenu(null)}
        />
      )}

      <Sidebar
        isOpen={isSidebarOpen}
        onClose={() => setIsSidebarOpen(false)}
        activeTab={activeTab}
        setActiveTab={setActiveTabWithRoute}
        showUI={showUI}
      />

      <main className="flex-1 flex flex-col items-center w-full h-screen overflow-hidden relative bg-[var(--color-cyan-light)]/50 transition-all duration-500">
        {showUI && !viewport.isMobile && <PhoneOverlay />}

        {showUI && !shouldForceLandscape && (
          <Header
            onMenuClick={() => setIsSidebarOpen(true)}
            onAccountClick={() => setActiveTabWithRoute('account')}
            activeTab={activeTab}
            isSidebarOpen={isSidebarOpen}
          />
        )}

        <div className={`flex-1 relative flex flex-col items-stretch w-full h-full custom-scrollbar transition-all duration-500 ${(activeTab === 'game' || activeTab === 'editor') ? 'justify-center p-0 overflow-hidden' : 'justify-start px-3 py-3 pb-16 md:px-8 md:py-8 md:pb-20 overflow-auto'}`}>
          {activeTab === 'game' && <GameView onTabChange={setActiveTabWithRoute} />}
          {activeTab === 'mods' && <ModManager onTabChange={setActiveTabWithRoute} />}
          {activeTab === 'workshop' && <ModManager onTabChange={setActiveTabWithRoute} />}
          {activeTab === 'editor' && <PromptEditor />}
          {activeTab === 'settings' && <SettingsPanel />}
          {activeTab === 'account' && <AccountPanel />}
          {activeTab === 'admin' && <AdminDashboard />}
        </div>
      </main>
    </div>
  );
}

export default App;
