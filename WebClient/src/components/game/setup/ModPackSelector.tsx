import { useState, useEffect, useCallback } from 'react';
import { Layers, Cloud, BookOpen, Save, Trash2, Download, Plus, RefreshCw, X, Check, Lock } from 'lucide-react';
import { gameApi } from '../../../api/gameApi';

interface ModPackSelectorProps {
  selectedMod: string;
  setSelectedMod: (id: string) => void;
  onTabChange: (tab: any) => void;
}

type ActiveTab = 'library' | 'workshop';

export const ModPackSelector = ({ selectedMod, setSelectedMod, onTabChange }: ModPackSelectorProps) => {
  const [activeTab, setActiveTab] = useState<ActiveTab>('library');
  const [libraryMods, setLibraryMods] = useState<any[]>([]);
  const [workshopMods, setWorkshopMods] = useState<any[]>([]);
  const [isLoading, setIsLoading] = useState(false);

  // Save dialog state
  const [showSaveDialog, setShowSaveDialog] = useState(false);
  const [saveName, setSaveName] = useState('');
  const [saveDesc, setSaveDesc] = useState('');
  const [isSaving, setIsSaving] = useState(false);

  // Action feedback states
  const [actionTarget, setActionTarget] = useState<string | null>(null);
  const [actionType, setActionType] = useState<'delete' | 'download' | null>(null);

  const loadLibrary = useCallback(async () => {
    setIsLoading(true);
    try {
      const res = await gameApi.getLibraryList();
      setLibraryMods(res.data || []);
    } finally {
      setIsLoading(false);
    }
  }, []);

  const loadWorkshop = useCallback(async () => {
    setIsLoading(true);
    try {
      const res = await gameApi.getWorkshopList();
      setWorkshopMods(res.data || []);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    if (activeTab === 'library') loadLibrary();
    else loadWorkshop();
  }, [activeTab, loadLibrary, loadWorkshop]);

  const handleSaveCurrent = async () => {
    if (!saveName.trim()) return;
    setIsSaving(true);
    try {
      await gameApi.saveToLibrary(saveName.trim(), saveDesc.trim());
      setShowSaveDialog(false);
      setSaveName(''); setSaveDesc('');
      loadLibrary();
    } finally {
      setIsSaving(false);
    }
  };

  const handleDelete = async (id: string) => {
    setActionTarget(id); setActionType('delete');
    try {
      await gameApi.deleteFromLibrary(id);
      if (selectedMod === id) setSelectedMod('default');
      loadLibrary();
    } finally {
      setActionTarget(null); setActionType(null);
    }
  };

  const handleDownload = async (id: string) => {
    setActionTarget(id); setActionType('download');
    try {
      const res = await gameApi.downloadWorkshopItem(id);
      if (res?.library_id) {
        setSelectedMod(res.library_id);
      }
      // Switch to library tab after download
      setActiveTab('library');
      loadLibrary();
    } finally {
      setActionTarget(null); setActionType(null);
    }
  };

  const isActing = (id: string, type: typeof actionType) =>
    actionTarget === id && actionType === type;

  return (
    <div className="w-full md:w-80 bg-white/60 border-r border-dashed border-[var(--color-cyan-main)]/20 flex flex-col shrink-0">
      {/* Header */}
      <div className="p-4 border-b border-[var(--color-cyan-main)]/10">
        <h3 className="text-[10px] font-black text-[var(--color-cyan-main)] flex items-center tracking-[0.2em] uppercase mb-3">
          <Layers size={14} className="mr-2" /> 设定模组
        </h3>
        <p className="text-[9px] text-amber-600/80 font-bold mb-3 leading-tight flex items-start gap-1">
          <Lock size={10} className="mt-0.5 shrink-0" />
          <span>这里只是为新对局选择起始模组。真正生效发生在点击“开始游戏”时，局外不会立即替换当前内容。</span>
        </p>
        {/* Tabs */}
        <div className="flex rounded-xl border border-[var(--color-cyan-main)]/20 overflow-hidden text-[10px] font-black uppercase tracking-widest">
          <button
            onClick={() => setActiveTab('library')}
            className={`flex-1 flex items-center justify-center gap-1.5 py-2.5 transition-all ${activeTab === 'library' ? 'bg-[var(--color-cyan-dark)] text-white' : 'text-[var(--color-cyan-main)] hover:bg-[var(--color-cyan-main)]/10'}`}
          >
            <BookOpen size={11} /> 我的库
          </button>
          <button
            onClick={() => setActiveTab('workshop')}
            className={`flex-1 flex items-center justify-center gap-1.5 py-2.5 transition-all ${activeTab === 'workshop' ? 'bg-[var(--color-cyan-dark)] text-white' : 'text-[var(--color-cyan-main)] hover:bg-[var(--color-cyan-main)]/10'}`}
          >
            <Cloud size={11} /> 创意工坊
          </button>
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto custom-scrollbar p-3 space-y-2">
        {/* Default Mod (Library tab only) */}
        {activeTab === 'library' && (
          <div
            onClick={() => setSelectedMod('default')}
            className={`p-3 rounded-xl cursor-pointer border-2 transition-all relative overflow-hidden ${selectedMod === 'default' ? 'bg-[var(--color-cyan-dark)] border-[var(--color-cyan-dark)] text-white shadow-lg' : 'bg-white/80 border-[var(--color-cyan-main)]/10 text-gray-600 hover:border-[var(--color-cyan-main)]'}`}
          >
            {selectedMod === 'default' && <Check size={12} className="absolute top-2 right-2 opacity-80" />}
            <h4 className="font-black text-xs">默认设定</h4>
            <p className="text-[9px] mt-0.5 opacity-60 font-bold uppercase tracking-tighter">Original Game Files</p>
          </div>
        )}

        {isLoading && (
          <div className="flex items-center justify-center py-8 text-[var(--color-cyan-main)]">
            <RefreshCw size={18} className="animate-spin" />
          </div>
        )}

        {!isLoading && activeTab === 'library' && libraryMods.length === 0 && (
          <div className="text-center py-6 text-[10px] text-gray-400 font-bold uppercase tracking-widest">
            库中暂无模组<br />
            <span className="text-[9px] normal-case">保存你的修改以创建第一个模组</span>
          </div>
        )}

        {!isLoading && activeTab === 'library' && libraryMods.map(mod => (
          <div
            key={mod.id}
            className={`p-3 rounded-xl border-2 transition-all relative overflow-hidden ${selectedMod === mod.id ? 'bg-[var(--color-cyan-dark)] border-[var(--color-cyan-dark)] text-white shadow-lg' : 'bg-white/80 border-[var(--color-cyan-main)]/10 text-gray-600 hover:border-[var(--color-cyan-main)]'}`}
          >
            <div className="flex items-start justify-between gap-1">
              <div className="flex-1 min-w-0 cursor-pointer" onClick={() => setSelectedMod(mod.id)}>
                <h4 className="font-black text-xs truncate">{mod.name}</h4>
                <p className="text-[9px] mt-0.5 opacity-60 font-bold">{mod.timestamp}</p>
                {mod.description && <p className="text-[9px] mt-1 opacity-70 line-clamp-2">{mod.description}</p>}
                <div className="mt-2 flex flex-wrap gap-1">
                  <span className="px-2 py-0.5 rounded-full text-[8px] font-black tracking-widest bg-[var(--color-cyan-main)]/10 text-[var(--color-cyan-main)]">
                    开局可选
                  </span>
                  {mod.visibility === 'public' && (
                    <span className="px-2 py-0.5 rounded-full text-[8px] font-black tracking-widest bg-emerald-50 text-emerald-600">
                      已公开
                    </span>
                  )}
                </div>
              </div>
              <div className="flex flex-col gap-1 shrink-0">
                <button
                  onClick={() => handleDelete(mod.id)}
                  title="删除"
                  className={`p-1.5 rounded-lg transition-all ${selectedMod === mod.id ? 'bg-red-400/30 hover:bg-red-400/50 text-red-100' : 'bg-red-50 hover:bg-red-100 text-red-400'}`}
                >
                  {isActing(mod.id, 'delete') ? <RefreshCw size={11} className="animate-spin" /> : <Trash2 size={11} />}
                </button>
              </div>
            </div>
          </div>
        ))}

        {!isLoading && activeTab === 'workshop' && workshopMods.length === 0 && (
          <div className="text-center py-6 text-[10px] text-gray-400 font-bold uppercase tracking-widest">
            工坊暂无模组<br />
            <span className="text-[9px] normal-case">前往编辑器发布你的作品</span>
          </div>
        )}

        {!isLoading && activeTab === 'workshop' && workshopMods.map(mod => (
          <div key={mod.id} className="p-3 rounded-xl border-2 border-[var(--color-cyan-main)]/10 bg-white/80 text-gray-600">
            <div className="flex items-start justify-between gap-1">
              <div className="flex-1 min-w-0">
                <h4 className="font-black text-xs truncate">{mod.name}</h4>
                <p className="text-[9px] mt-0.5 opacity-60 font-bold">By {mod.author} · {mod.downloads}↓</p>
                {mod.description && <p className="text-[9px] mt-1 opacity-70 line-clamp-2">{mod.description}</p>}
              </div>
              <button
                onClick={() => handleDownload(mod.id)}
                title="下载到我的库"
                className="p-1.5 rounded-lg bg-[var(--color-cyan-main)]/10 hover:bg-[var(--color-cyan-main)]/20 text-[var(--color-cyan-main)] transition-all shrink-0"
              >
                {isActing(mod.id, 'download') ? <RefreshCw size={11} className="animate-spin" /> : <Download size={11} />}
              </button>
            </div>
          </div>
        ))}
      </div>

      {/* Footer Actions */}
      <div className="p-3 border-t border-[var(--color-cyan-main)]/10 space-y-2">
        {activeTab === 'library' && (
          <button
            onClick={() => setShowSaveDialog(true)}
            className="w-full flex items-center justify-center gap-2 py-2.5 bg-[var(--color-cyan-dark)] hover:opacity-90 text-white rounded-xl text-[10px] font-black uppercase tracking-widest transition-all active:scale-95"
          >
            <Save size={12} /> 另存当前配置
          </button>
        )}
        <button
          onClick={() => onTabChange('workshop')}
          className="w-full flex items-center justify-center gap-2 py-2.5 bg-white/60 border border-dashed border-[var(--color-cyan-main)]/30 text-[var(--color-cyan-main)] rounded-xl text-[10px] font-black uppercase tracking-widest hover:bg-[var(--color-cyan-main)]/10 transition-all"
        >
          <Plus size={12} /> {activeTab === 'library' ? '前往创意工坊' : '发布模组'}
        </button>
      </div>

      {/* Save Dialog Overlay */}
      {showSaveDialog && (
        <div className="fixed inset-0 bg-black/40 backdrop-blur-sm z-50 flex items-center justify-center p-6" onClick={() => setShowSaveDialog(false)}>
          <div
            className="bg-white rounded-2xl shadow-2xl p-6 w-full max-w-sm border-2 border-[var(--color-cyan-main)]/20"
            onClick={e => e.stopPropagation()}
          >
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-sm font-black text-gray-800">另存为模组</h3>
              <button onClick={() => setShowSaveDialog(false)} className="text-gray-400 hover:text-gray-600">
                <X size={16} />
              </button>
            </div>
            <div className="space-y-3">
              <div>
                <label className="text-[10px] font-black uppercase tracking-widest text-[var(--color-cyan-main)] block mb-1">模组名称 *</label>
                <input
                  type="text"
                  value={saveName}
                  onChange={e => setSaveName(e.target.value)}
                  placeholder="给你的模组起个名字..."
                  className="w-full border-2 border-[var(--color-cyan-main)]/20 rounded-xl px-3 py-2 text-sm outline-none focus:border-[var(--color-cyan-main)] transition-colors"
                />
              </div>
              <div>
                <label className="text-[10px] font-black uppercase tracking-widest text-[var(--color-cyan-main)] block mb-1">简介 (选填)</label>
                <textarea
                  value={saveDesc}
                  onChange={e => setSaveDesc(e.target.value)}
                  placeholder="描述这个模组的特点..."
                  rows={3}
                  className="w-full border-2 border-[var(--color-cyan-main)]/20 rounded-xl px-3 py-2 text-sm outline-none focus:border-[var(--color-cyan-main)] transition-colors resize-none"
                />
              </div>
              <button
                onClick={handleSaveCurrent}
                disabled={!saveName.trim() || isSaving}
                className="w-full py-2.5 bg-[var(--color-cyan-dark)] disabled:opacity-50 text-white rounded-xl text-xs font-black uppercase tracking-widest flex items-center justify-center gap-2 transition-all"
              >
                {isSaving ? <RefreshCw size={12} className="animate-spin" /> : <Save size={12} />}
                {isSaving ? '保存中...' : '保存到库'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
