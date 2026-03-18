import { useState, useEffect } from 'react';
import { GameView } from './components/GameView';
import { WorkshopBrowser } from './components/WorkshopBrowser';
import { LocalMods } from './components/LocalMods';
import { SettingsPanel } from './components/SettingsPanel';
import { PromptEditor } from './components/PromptEditor';
import { PhoneOverlay } from './components/PhoneOverlay';
import { AdminDashboard } from './components/AdminDashboard';

import { Sidebar } from './components/layout/Sidebar';
import { Header } from './components/layout/Header';
import { GlobalContextMenu } from './components/layout/GlobalContextMenu';
import { Toast } from './components/layout/Toast';
import { CustomCursor } from './components/layout/CustomCursor';
import { LoadingScreen } from './components/layout/LoadingScreen';

function App() {
  const [activeTab, setActiveTab] = useState<'game' | 'workshop' | 'mods' | 'settings' | 'editor' | 'admin'>('game');
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);
  const [contextMenu, setContextMenu] = useState<{ x: number, y: number } | null>(null);
  const [showUI, setShowUI] = useState(true);
  const [toast, setToast] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  // Close context menu on click anywhere
  useEffect(() => {
    // Check for admin route on initial load
    const checkAdminRoute = () => {
      if (window.location.pathname === '/admin' || window.location.hash === '#/admin') {
        setActiveTab('admin');
      }
    };
    const handleClick = () => setContextMenu(null);
    const handleChangeTab = (e: any) => {
      if (e.detail) setActiveTab(e.detail);
    };

    const handlePopState = () => {
      checkAdminRoute();
    };

    window.addEventListener('click', handleClick);
    window.addEventListener('changeTab', handleChangeTab);
    window.addEventListener('popstate', handlePopState);
    window.addEventListener('hashchange', checkAdminRoute);

    return () => {
      window.removeEventListener('click', handleClick);
      window.removeEventListener('changeTab', handleChangeTab);
      window.removeEventListener('popstate', handlePopState);
      window.removeEventListener('hashchange', checkAdminRoute);
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

  return (
    <div
      className="w-full flex h-screen text-[var(--color-cyan-dark)] bg-[var(--color-cyan-light)] overflow-hidden relative selection:bg-[var(--color-cyan-main)] selection:text-white"
      onContextMenu={handleContextMenu}
    >
      {isLoading && <LoadingScreen onFinished={() => setIsLoading(false)} />}
      <CustomCursor />

      {/* Toast Notification */}
      {toast && <Toast message={toast} />}

      {/* Custom Context Menu */}
      {contextMenu && (
        <GlobalContextMenu
          x={contextMenu.x}
          y={contextMenu.y}
          setActiveTab={setActiveTab}
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
        setActiveTab={setActiveTab}
        showUI={showUI}
      />

      <main className="flex-1 flex flex-col items-center w-full h-screen overflow-hidden relative bg-[var(--color-cyan-light)]/50 transition-all duration-500">
        {showUI && <PhoneOverlay />}

        {showUI && (
          <Header
            onMenuClick={() => setIsSidebarOpen(true)}
            activeTab={activeTab}
            isSidebarOpen={isSidebarOpen}
          />
        )}

        <div className={`flex-1 relative flex flex-col items-stretch justify-center w-full h-full custom-scrollbar transition-all duration-500 ${activeTab === 'game' ? (showUI ? 'p-4 md:px-4 md:py-6 overflow-hidden' : 'p-0 overflow-hidden') : 'p-4 md:px-8 md:py-8 pb-20 overflow-auto'}`}>
          {activeTab === 'game' && <GameView onTabChange={setActiveTab} />}
          {activeTab === 'workshop' && <WorkshopBrowser />}
          {activeTab === 'mods' && <LocalMods />}
          {activeTab === 'editor' && <PromptEditor />}
          {activeTab === 'settings' && <SettingsPanel />}
          {activeTab === 'admin' && <AdminDashboard />}
        </div>
      </main>
    </div>
  );
}

export default App;
