import { useState, useEffect } from 'react';
import { settingsApi, SystemSettings } from '../api/settingsApi';
import { gameApi } from '../api/gameApi';
import { useGameStore } from '../store/gameStore';
import { Settings, Save, RefreshCcw, Server, Key, Cpu, Thermometer, Database, Type, Trash2, Milestone } from 'lucide-react';

export const SettingsPanel = () => {
    const [settings, setSettings] = useState<SystemSettings>({
        base_url: '',
        api_key: '',
        model_name: '',
        temperature: 0.7,
        max_tokens: 1000,
        typewriter_speed: 30
    });
    const [isLoading, setIsLoading] = useState(true);
    const [isSaving, setIsSaving] = useState(false);
    const [message, setMessage] = useState('');
    const [saves, setSaves] = useState<any[]>([]);
    const [activeTab, setActiveTab] = useState<'ai' | 'archives'>('ai');
    const loadSaveAction = useGameStore(state => state.loadSave);
    const setTypewriterSpeed = useGameStore(state => state.setTypewriterSpeed);

    useEffect(() => {
        loadSettings();
        loadSaves();
    }, []);

    const loadSaves = async () => {
        try {
            const data = await gameApi.getSavesInfo();
            setSaves(data.slots || []);
        } catch (error) {
            console.error('Failed to load saves:', error);
        }
    };

    const loadSettings = async () => {
        setIsLoading(true);
        try {
            const data = await settingsApi.getSettings();
            setSettings(data);
        } catch (error) {
            console.error('Failed to load settings:', error);
            setMessage('读取设置失败。请检查后端是否正常运行。');
        } finally {
            setIsLoading(false);
        }
    };

    const handleSave = async () => {
        setIsSaving(true);
        setMessage('');
        try {
            await settingsApi.updateSettings(settings);
            setTypewriterSpeed(settings.typewriter_speed);
            setMessage('设置保存成功！');
            setTimeout(() => setMessage(''), 3000);
        } catch (error) {
            console.error('Failed to save settings:', error);
            setMessage('保存失败，请重试。');
        } finally {
            setIsSaving(false);
        }
    };

    if (isLoading) {
        return (
            <div className="flex-1 flex items-center justify-center h-full">
                <RefreshCcw className="animate-spin text-[var(--color-cyan-main)]" size={48} />
            </div>
        );
    }

    return (
        <div className="flex-1 flex flex-col h-full bg-white/80 backdrop-blur-md rounded-2xl border-2 border-[var(--color-cyan-main)]/20 shadow-xl overflow-hidden relative p-8">
            <div className="flex items-center justify-between mb-8 border-b-2 border-[var(--color-cyan-main)]/20 pb-4">
                <div className="flex items-center space-x-4">
                    <div className="w-12 h-12 rounded-xl bg-[var(--color-cyan-main)] text-white flex items-center justify-center shadow-lg shadow-cyan-main/30">
                        <Settings size={28} />
                    </div>
                    <div>
                        <h2 className="text-2xl font-black text-[var(--color-cyan-dark)] tracking-wider">系统设置</h2>
                        <p className="text-sm font-bold text-[var(--color-cyan-dark)]/60">调整大语言模型网关配置与生成策略</p>
                    </div>
                </div>
                {message && (
                    <div className={`px-4 py-2 rounded-lg font-bold text-sm ${message.includes('失败') ? 'bg-red-100 text-red-600' : 'bg-[var(--color-cyan-light)] text-[var(--color-cyan-dark)]'}`}>
                        {message}
                    </div>
                )}
            </div>

            {/* Tab Header */}
            <div className="flex space-x-2 mb-8 bg-[var(--color-cyan-light)]/30 p-1 rounded-2xl w-fit">
                <button
                    onClick={() => setActiveTab('ai')}
                    className={`px-6 py-2.5 rounded-xl font-black text-xs uppercase tracking-widest transition-all ${activeTab === 'ai' ? 'bg-[var(--color-cyan-main)] text-white shadow-md' : 'text-[var(--color-cyan-dark)]/60 hover:text-[var(--color-cyan-dark)]'}`}
                >
                    AI配置
                </button>
                <button
                    onClick={() => setActiveTab('archives')}
                    className={`px-6 py-2.5 rounded-xl font-black text-xs uppercase tracking-widest transition-all ${activeTab === 'archives' ? 'bg-[var(--color-cyan-main)] text-white shadow-md' : 'text-[var(--color-cyan-dark)]/60 hover:text-[var(--color-cyan-dark)]'}`}
                >
                    存档管理
                </button>
            </div>

            <div className="flex-1 overflow-y-auto custom-scrollbar pr-4 space-y-6">
                {activeTab === 'ai' ? (
                    <div className="animate-in fade-in slide-in-from-bottom-4 duration-500">
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                            <div className="bg-white p-5 rounded-2xl border-2 border-[var(--color-cyan-main)]/10 shadow-sm flex flex-col transition-all hover:border-[var(--color-yellow-main)]/50 group">
                                <label className="text-sm font-black text-[var(--color-cyan-main)] uppercase tracking-wider mb-3 flex items-center">
                                    <Server size={16} className="mr-2" /> 网关地址
                                </label>
                                <input
                                    type="text"
                                    value={settings.base_url}
                                    onChange={(e) => setSettings({ ...settings, base_url: e.target.value })}
                                    className="bg-[var(--color-cyan-light)]/50 text-[var(--color-cyan-dark)] font-bold p-3 rounded-xl border border-[var(--color-cyan-main)]/20 outline-none focus:ring-2 focus:ring-[var(--color-yellow-main)] transition-shadow w-full"
                                />
                            </div>

                            <div className="bg-white p-5 rounded-2xl border-2 border-[var(--color-cyan-main)]/10 shadow-sm flex flex-col transition-all hover:border-[var(--color-yellow-main)]/50 group">
                                <label className="text-sm font-black text-[var(--color-cyan-main)] uppercase tracking-wider mb-3 flex items-center">
                                    <Cpu size={16} className="mr-2" /> 模型版本
                                </label>
                                <input
                                    type="text"
                                    value={settings.model_name}
                                    onChange={(e) => setSettings({ ...settings, model_name: e.target.value })}
                                    className="bg-[var(--color-cyan-light)]/50 text-[var(--color-cyan-dark)] font-bold p-3 rounded-xl border border-[var(--color-cyan-main)]/20 outline-none focus:ring-2 focus:ring-[var(--color-yellow-main)] transition-shadow w-full"
                                />
                            </div>

                            <div className="bg-white p-5 rounded-2xl border-2 border-[var(--color-cyan-main)]/10 shadow-sm flex flex-col transition-all hover:border-[var(--color-yellow-main)]/50 group md:col-span-2">
                                <label className="text-sm font-black text-[var(--color-cyan-main)] uppercase tracking-wider mb-3 flex items-center">
                                    <Key size={16} className="mr-2" /> 通信密钥 (API Key)
                                </label>
                                <input
                                    type="password"
                                    value={settings.api_key}
                                    onChange={(e) => setSettings({ ...settings, api_key: e.target.value })}
                                    placeholder="留空则沿用后端环境变量"
                                    className="bg-[var(--color-cyan-light)]/50 text-[var(--color-cyan-dark)] font-bold p-3 rounded-xl border border-[var(--color-cyan-main)]/20 outline-none focus:ring-2 focus:ring-[var(--color-yellow-main)] transition-shadow w-full"
                                />
                            </div>

                            <div className="bg-white p-5 rounded-2xl border-2 border-[var(--color-cyan-main)]/10 shadow-sm flex flex-col transition-all hover:border-[var(--color-yellow-main)]/50 group">
                                <div className="flex justify-between items-center mb-3">
                                    <label className="text-sm font-black text-[var(--color-cyan-main)] uppercase tracking-wider flex items-center">
                                        <Thermometer size={16} className="mr-2" /> 温度
                                    </label>
                                    <span className="font-black text-[var(--color-yellow-main)] bg-[var(--color-cyan-dark)] px-2 py-0.5 rounded-lg text-xs">
                                        {settings.temperature}
                                    </span>
                                </div>
                                <input
                                    type="range"
                                    min="0" max="2" step="0.1"
                                    value={settings.temperature}
                                    onChange={(e) => setSettings({ ...settings, temperature: parseFloat(e.target.value) })}
                                    className="w-full h-2 bg-[var(--color-cyan-main)]/20 rounded-lg appearance-none cursor-pointer accent-[var(--color-cyan-main)] transition-colors hover:accent-[var(--color-yellow-main)]"
                                />
                            </div>

                            <div className="bg-white p-5 rounded-2xl border-2 border-[var(--color-cyan-main)]/10 shadow-sm flex flex-col transition-all hover:border-[var(--color-yellow-main)]/50 group">
                                <label className="text-sm font-black text-[var(--color-cyan-main)] uppercase tracking-wider mb-3 flex items-center">
                                    <Database size={16} className="mr-2" /> Max Tokens
                                </label>
                                <input
                                    type="number"
                                    min="100" max="4000" step="50"
                                    value={settings.max_tokens}
                                    onChange={(e) => setSettings({ ...settings, max_tokens: parseInt(e.target.value) })}
                                    className="bg-[var(--color-cyan-light)]/50 text-[var(--color-cyan-dark)] font-bold p-3 rounded-xl border border-[var(--color-cyan-main)]/20 outline-none focus:ring-2 focus:ring-[var(--color-yellow-main)] transition-shadow w-full"
                                />
                            </div>

                            <div className="bg-white p-5 rounded-2xl border-2 border-[var(--color-cyan-main)]/10 shadow-sm flex flex-col transition-all hover:border-[var(--color-yellow-main)]/50 group md:col-span-2">
                                <div className="flex justify-between items-center mb-3">
                                    <label className="text-sm font-black text-[var(--color-cyan-main)] uppercase tracking-wider flex items-center">
                                        <Type size={16} className="mr-2" /> 打字机速度
                                    </label>
                                    <span className="font-black text-[var(--color-yellow-main)] bg-[var(--color-cyan-dark)] px-2 py-0.5 rounded-lg text-xs">
                                        {settings.typewriter_speed} ms/字
                                    </span>
                                </div>
                                <input
                                    type="range"
                                    min="5" max="100" step="5"
                                    value={settings.typewriter_speed}
                                    onChange={(e) => setSettings({ ...settings, typewriter_speed: parseInt(e.target.value) })}
                                    className="w-full h-2 bg-[var(--color-cyan-main)]/20 rounded-lg appearance-none cursor-pointer accent-[var(--color-cyan-main)] transition-colors hover:accent-[var(--color-yellow-main)]"
                                />
                                <p className="mt-2 text-[10px] text-[var(--color-cyan-dark)]/40 font-bold uppercase tracking-tighter">数值越小，文字显示越快</p>
                            </div>
                        </div>

                        <div className="mt-8 pt-6 border-t border-dashed border-[var(--color-cyan-main)]/10 flex justify-end">
                            <button
                                onClick={handleSave}
                                disabled={isSaving}
                                className="flex items-center px-8 py-4 bg-[var(--color-cyan-main)] text-white font-black rounded-xl shadow-lg shadow-[var(--color-cyan-main)]/30 hover:bg-[var(--color-cyan-dark)] hover:scale-105 transition-all disabled:opacity-50 disabled:scale-100 uppercase tracking-widest text-sm"
                            >
                                {isSaving ? <RefreshCcw className="animate-spin mr-2" size={20} /> : <Save className="mr-2" size={20} />}
                                {isSaving ? '正在保存...' : '保存'}
                            </button>
                        </div>
                    </div>
                ) : (
                    <div className="animate-in fade-in slide-in-from-bottom-4 duration-500">
                        <div className="flex items-center space-x-3 mb-6">
                            <Milestone className="text-[var(--color-yellow-main)]" />
                            <h3 className="text-xl font-black text-[var(--color-cyan-dark)] uppercase">存档管理</h3>
                        </div>

                        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                            {saves.map((slot) => (
                                <div key={slot.slot_id} className={`group relative p-6 rounded-2xl border-2 transition-all duration-300 ${slot.is_empty ? 'border-dashed border-[var(--color-cyan-main)]/20 bg-transparent opacity-60' : 'border-[var(--color-cyan-main)]/10 bg-white hover:border-[var(--color-yellow-main)]/50 shadow-sm'}`}>
                                    <div className="absolute top-4 right-4 flex space-x-2 opacity-0 group-hover:opacity-100 transition-opacity">
                                        {!slot.is_empty && (
                                            <button
                                                onClick={async () => {
                                                    if (confirm('确认要抹除此存档位吗？此操作不可撤销。')) {
                                                        await gameApi.deleteSave(slot.slot_id);
                                                        loadSaves();
                                                    }
                                                }}
                                                className="p-1.5 bg-red-500/10 text-red-500 hover:bg-red-500 hover:text-white rounded-lg transition-all"
                                                title="抹除存档"
                                            >
                                                <Trash2 size={16} />
                                            </button>
                                        )}
                                    </div>

                                    <div className="mb-4">
                                        <span className="text-[10px] font-black text-[var(--color-cyan-main)] uppercase tracking-[0.2em]">SLOT 0{slot.slot_id}</span>
                                        <h4 className="text-lg font-black text-[var(--color-cyan-dark)] truncate mt-1">
                                            {slot.is_empty ? '空' : slot.chapter_info}
                                        </h4>
                                    </div>

                                    {!slot.is_empty ? (
                                        <>
                                            <div className="text-[10px] font-bold text-[var(--color-cyan-dark)]/40 uppercase mb-6 flex items-center">
                                                <RefreshCcw size={10} className="mr-1" /> 最后修改: {slot.timestamp}
                                            </div>
                                            <button
                                                onClick={() => {
                                                    if (confirm(`准备加载存档 [${slot.chapter_info}]？当前进度将被覆盖。`)) {
                                                        loadSaveAction(slot.slot_id);
                                                    }
                                                }}
                                                className="w-full py-2 bg-[var(--color-cyan-light)] hover:bg-[var(--color-yellow-main)] text-[var(--color-cyan-dark)] font-black rounded-lg text-xs uppercase tracking-widest transition-all"
                                            >
                                                读取
                                            </button>
                                        </>
                                    ) : (
                                        <div className="h-[76px] flex items-center justify-center text-[10px] font-black text-[var(--color-cyan-main)]/30 uppercase tracking-[0.3em]">
                                            等待写入...
                                        </div>
                                    )}
                                </div>
                            ))}
                        </div>
                    </div>
                )}
            </div>
        </div>
    );
};
