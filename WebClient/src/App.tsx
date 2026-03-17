import { useState } from 'react';
import { GameView } from './components/GameView';
import { WorkshopBrowser } from './components/WorkshopBrowser';
import { LocalMods } from './components/LocalMods';
import { SettingsPanel } from './components/SettingsPanel';
import { PromptEditor } from './components/PromptEditor';
import { PhoneOverlay } from './components/PhoneOverlay';
import { Menu, X } from 'lucide-react';

function App() {
  const [activeTab, setActiveTab] = useState<'game' | 'workshop' | 'mods' | 'settings' | 'editor'>('game');
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);

  return (
    <div className="w-full flex h-screen text-[var(--color-cyan-dark)] bg-[var(--color-cyan-light)] overflow-hidden">
      {/* Mobile/Collapsible Sidebar Overlay */}
      {isSidebarOpen && (
        <div 
          className="fixed inset-0 bg-black/50 z-20 transition-opacity"
          onClick={() => setIsSidebarOpen(false)}
        />
      )}

      {/* Sidebar */}
      <aside className={`fixed inset-y-0 left-0 w-64 flex flex-col transition-transform duration-300 ease-in-out shadow-2xl z-30 shrink-0 bg-[var(--color-cyan-main)] text-white ${isSidebarOpen ? 'translate-x-0' : '-translate-x-full'}`}>
        <div className="h-16 flex items-center justify-between px-6 border-b border-white/10 shrink-0 bg-black/10">
          <span className="text-xl font-bold tracking-wider text-[var(--color-yellow-main)] drop-shadow-sm flex items-center">
             RS Web <span className="ml-2 text-xs text-white/50 bg-white/10 px-2 py-0.5 rounded-sm">v1</span>
          </span>
          <button onClick={() => setIsSidebarOpen(false)} className="text-white hover:text-[var(--color-yellow-main)] transition-colors">
              <X size={24} />
          </button>
        </div>
        <nav className="flex-1 py-6 overflow-y-auto space-y-2 custom-scrollbar">
          <div 
             onClick={() => { setActiveTab('game'); setIsSidebarOpen(false); }}
             className={`px-4 py-3 cursor-pointer text-sm font-black flex justify-start items-center transition-colors border-l-4 ${activeTab === 'game' ? 'bg-[var(--color-cyan-dark)]/20 border-[var(--color-yellow-main)] text-[var(--color-yellow-main)] shadow-inner' : 'border-transparent text-white hover:bg-white/10 hover:text-[var(--color-yellow-main)]'}`}>
             <span className="uppercase tracking-widest pl-2">游玩</span>
          </div>
          <div 
             onClick={() => { setActiveTab('workshop'); setIsSidebarOpen(false); }}
             className={`px-4 py-3 cursor-pointer text-sm font-black flex justify-start items-center transition-colors border-l-4 ${activeTab === 'workshop' ? 'bg-[var(--color-cyan-dark)]/20 border-[var(--color-yellow-main)] text-[var(--color-yellow-main)] shadow-inner' : 'border-transparent text-white hover:bg-white/10 hover:text-[var(--color-yellow-main)]'}`}>
             <span className="uppercase tracking-widest pl-2">工坊</span>
          </div>
          <div 
             onClick={() => { setActiveTab('mods'); setIsSidebarOpen(false); }}
             className={`px-4 py-3 cursor-pointer text-sm font-black flex justify-start items-center transition-colors border-l-4 ${activeTab === 'mods' ? 'bg-[var(--color-cyan-dark)]/20 border-[var(--color-yellow-main)] text-[var(--color-yellow-main)] shadow-inner' : 'border-transparent text-white hover:bg-white/10 hover:text-[var(--color-yellow-main)]'}`}>
             <span className="uppercase tracking-widest pl-2">本地</span>
          </div>
          <div 
             onClick={() => { setActiveTab('editor'); setIsSidebarOpen(false); }}
             className={`px-4 py-3 cursor-pointer text-sm font-black flex justify-start items-center transition-colors border-l-4 ${activeTab === 'editor' ? 'bg-[var(--color-cyan-dark)]/20 border-[var(--color-yellow-main)] text-[var(--color-yellow-main)] shadow-inner' : 'border-transparent text-white hover:bg-white/10 hover:text-[var(--color-yellow-main)]'}`}>
             <span className="uppercase tracking-widest pl-2">编辑器</span>
          </div>
          <div 
             onClick={() => { setActiveTab('settings'); setIsSidebarOpen(false); }}
             className={`px-4 py-3 cursor-pointer text-sm font-black flex justify-start items-center transition-colors border-l-4 ${activeTab === 'settings' ? 'bg-[var(--color-cyan-dark)]/20 border-[var(--color-yellow-main)] text-[var(--color-yellow-main)] shadow-inner' : 'border-transparent text-white hover:bg-white/10 hover:text-[var(--color-yellow-main)]'}`}>
             <span className="uppercase tracking-widest pl-2">设置</span>
          </div>
        </nav>
      </aside>

      <main className="flex-1 flex flex-col w-full h-screen overflow-hidden relative bg-[var(--color-cyan-light)]/50">
        <PhoneOverlay />
        <header className="h-16 flex items-center justify-start px-4 md:px-8 bg-white border-b-2 border-[var(--color-cyan-main)]/20 shrink-0 z-10 shadow-sm relative">
          {!isSidebarOpen && (
              <button 
                onClick={() => setIsSidebarOpen(true)}
                className="mr-4 p-2 rounded-lg bg-[var(--color-cyan-light)] text-[var(--color-cyan-dark)] hover:bg-[var(--color-cyan-main)] hover:text-white transition-colors"
              >
                  <Menu size={24} />
              </button>
          )}
          <h2 className="text-xl font-black text-[var(--color-cyan-dark)] tracking-wide uppercase">
              {activeTab === 'game' && '生存实录 (当前对局)'}
              {activeTab === 'workshop' && '创意工坊'}
              {activeTab === 'mods' && '本地模组'}
              {activeTab === 'editor' && '本地编撰区'}
              {activeTab === 'settings' && '系统级参数设定'}
          </h2>
        </header>

        <div className={`flex-1 overflow-auto relative flex flex-col md:flex-row space-y-4 md:space-y-0 md:space-x-8 items-start justify-center w-full h-full pb-10 custom-scrollbar ${activeTab === 'game' ? 'p-4 md:px-4 md:py-8' : 'p-4 md:px-8 md:py-8 max-w-7xl mx-auto'}`}>
            {activeTab === 'game' && (
                <>
                    <GameView onTabChange={setActiveTab} />
                </>
            )}
            {activeTab === 'workshop' && <WorkshopBrowser />}
            {activeTab === 'mods' && <LocalMods />}
            {activeTab === 'editor' && <PromptEditor />}
            {activeTab === 'settings' && <SettingsPanel />}
        </div>
      </main>
    </div>
  );
}

export default App;
