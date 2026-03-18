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
    const [activeTab, setActiveTab] = useState<'ai' | 'preferences'>('ai');
    
    // Store values
    const { 
        audioVolume, setAudioVolume, 
        isMuted, setMuted, 
        uiTransparency, setUiTransparency,
        resetGame,
        setTypewriterSpeed 
    } = useGameStore();

    useEffect(() => {
        loadSettings();
    }, []);

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
                        <p className="text-sm font-bold text-[var(--color-cyan-dark)]/60">个性化调整您的室友生存体验</p>
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
                    AI网关
                </button>
                <button
                    onClick={() => setActiveTab('preferences')}
                    className={`px-6 py-2.5 rounded-xl font-black text-xs uppercase tracking-widest transition-all ${activeTab === 'preferences' ? 'bg-[var(--color-cyan-main)] text-white shadow-md' : 'text-[var(--color-cyan-dark)]/60 hover:text-[var(--color-cyan-dark)]'}`}
                >
                    偏好设置
                </button>
            </div>

            <div className="flex-1 overflow-y-auto custom-scrollbar pr-4 space-y-6">
                {activeTab === 'ai' ? (
                    <div className="animate-in fade-in slide-in-from-bottom-4 duration-500">
                        {/* Current Model Status Header */}
                        <div className="mb-6 p-4 bg-gradient-to-r from-[var(--color-cyan-main)]/10 to-[var(--color-yellow-main)]/5 rounded-2xl border border-[var(--color-cyan-main)]/20 flex items-center justify-between">
                            <div className="flex items-center space-x-3">
                                <div className="p-2 bg-white rounded-lg shadow-sm">
                                    <Cpu className="text-[var(--color-cyan-main)]" size={18} />
                                </div>
                                <div>
                                    <p className="text-[10px] font-black text-[var(--color-cyan-dark)]/40 uppercase tracking-widest">当前活跃模型</p>
                                    <p className="font-black text-[var(--color-cyan-dark)] tracking-tight">
                                        {settings.model_name || '未检测到模型'}
                                    </p>
                                </div>
                            </div>
                            <div className="flex items-center space-x-2">
                                <span className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></span>
                                <span className="text-[10px] font-bold text-green-600 uppercase tracking-tighter">API 连接正常</span>
                            </div>
                        </div>

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
                                        <Thermometer size={16} className="mr-2" /> 创意温度
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
                                    <Database size={16} className="mr-2" /> 多样性惩罚
                                </label>
                                <input
                                    type="number"
                                    min="100" max="4000" step="50"
                                    value={settings.max_tokens}
                                    onChange={(e) => setSettings({ ...settings, max_tokens: parseInt(e.target.value) })}
                                    className="bg-[var(--color-cyan-light)]/50 text-[var(--color-cyan-dark)] font-bold p-3 rounded-xl border border-[var(--color-cyan-main)]/20 outline-none focus:ring-2 focus:ring-[var(--color-yellow-main)] transition-shadow w-full"
                                />
                            </div>
                        </div>

                        <div className="mt-8 pt-6 border-t border-dashed border-[var(--color-cyan-main)]/10 flex justify-end">
                            <button
                                onClick={handleSave}
                                disabled={isSaving}
                                className="flex items-center px-8 py-4 bg-[var(--color-cyan-main)] text-white font-black rounded-xl shadow-lg shadow-[var(--color-cyan-main)]/30 hover:bg-[var(--color-cyan-dark)] hover:scale-105 transition-all disabled:opacity-50 disabled:scale-100 uppercase tracking-widest text-sm"
                            >
                                {isSaving ? <RefreshCcw className="animate-spin mr-2" size={20} /> : <Save className="mr-2" size={20} />}
                                {isSaving ? '正在应用...' : '应用更改'}
                            </button>
                        </div>
                    </div>
                ) : (
                    <div className="animate-in fade-in slide-in-from-bottom-4 duration-500 space-y-8">
                        {/* Audio Settings */}
                        <div className="bg-white p-6 rounded-3xl border-2 border-[var(--color-cyan-main)]/10 shadow-sm">
                            <div className="flex items-center space-x-3 mb-6">
                                <div className="p-2 bg-[var(--color-cyan-light)] rounded-xl text-[var(--color-cyan-main)]">
                                    <Milestone size={20} />
                                </div>
                                <h3 className="text-lg font-black text-[var(--color-cyan-dark)] uppercase">音视频偏好</h3>
                            </div>
                            
                            <div className="space-y-6">
                                <div className="flex flex-col">
                                    <div className="flex justify-between items-center mb-3">
                                        <label className="text-sm font-black text-[var(--color-cyan-dark)]/60 uppercase">主音量 (Master Volume)</label>
                                        <span className="font-black text-[var(--color-cyan-main)]">{audioVolume}%</span>
                                    </div>
                                    <input
                                        type="range"
                                        min="0" max="100"
                                        value={audioVolume}
                                        onChange={(e) => setAudioVolume(parseInt(e.target.value))}
                                        className="w-full h-2 bg-[var(--color-cyan-main)]/10 rounded-lg appearance-none cursor-pointer accent-[var(--color-cyan-main)]"
                                    />
                                </div>
                                
                                <div className="flex items-center justify-between p-4 bg-[var(--color-cyan-light)]/30 rounded-2xl">
                                    <div>
                                        <p className="font-black text-[var(--color-cyan-dark)] text-sm">静音模式</p>
                                        <p className="text-[10px] font-bold text-[var(--color-cyan-dark)]/40">关闭所有环境音效与背景音乐</p>
                                    </div>
                                    <button 
                                        onClick={() => setMuted(!isMuted)}
                                        className={`w-14 h-8 rounded-full transition-all relative ${isMuted ? 'bg-red-500' : 'bg-[var(--color-cyan-main)]'}`}
                                    >
                                        <div className={`absolute top-1 w-6 h-6 bg-white rounded-full transition-all shadow-sm ${isMuted ? 'left-7' : 'left-1'}`} />
                                    </button>
                                </div>
                            </div>
                        </div>

                        {/* UI Settings */}
                        <div className="bg-white p-6 rounded-3xl border-2 border-[var(--color-cyan-main)]/10 shadow-sm">
                            <div className="flex items-center space-x-3 mb-6">
                                <div className="p-2 bg-[var(--color-cyan-light)] rounded-xl text-[var(--color-cyan-main)]">
                                    <Type size={20} />
                                </div>
                                <h3 className="text-lg font-black text-[var(--color-cyan-dark)] uppercase">显示与文本</h3>
                            </div>
                            
                            <div className="space-y-6">
                                <div className="flex flex-col">
                                    <div className="flex justify-between items-center mb-3">
                                        <label className="text-sm font-black text-[var(--color-cyan-dark)]/60 uppercase">打字机速度</label>
                                        <span className="font-black text-[var(--color-cyan-main)]">{settings.typewriter_speed}ms</span>
                                    </div>
                                    <input
                                        type="range"
                                        min="5" max="100" step="5"
                                        value={settings.typewriter_speed}
                                        onChange={(e) => setSettings({ ...settings, typewriter_speed: parseInt(e.target.value) })}
                                        className="w-full h-2 bg-[var(--color-cyan-main)]/10 rounded-lg appearance-none cursor-pointer accent-[var(--color-cyan-main)]"
                                    />
                                </div>

                                <div className="flex flex-col">
                                    <div className="flex justify-between items-center mb-3">
                                        <label className="text-sm font-black text-[var(--color-cyan-dark)]/60 uppercase">界面透明度</label>
                                        <span className="font-black text-[var(--color-cyan-main)]">{uiTransparency}%</span>
                                    </div>
                                    <input
                                        type="range"
                                        min="50" max="100"
                                        value={uiTransparency}
                                        onChange={(e) => setUiTransparency(parseInt(e.target.value))}
                                        className="w-full h-2 bg-[var(--color-cyan-main)]/10 rounded-lg appearance-none cursor-pointer accent-[var(--color-cyan-main)]"
                                    />
                                </div>
                            </div>
                        </div>

                        {/* Dangerous Zone */}
                        <div className="bg-red-50/50 p-6 rounded-3xl border-2 border-red-100 shadow-sm">
                            <div className="flex items-center space-x-3 mb-4 text-red-600">
                                <Trash2 size={20} />
                                <h3 className="text-lg font-black uppercase">危险区域</h3>
                            </div>
                            <p className="text-xs font-bold text-red-600/60 mb-6 uppercase tracking-wider">以下操作将影响后端数据存储，请谨慎操作</p>
                            
                            <button 
                                onClick={() => {
                                    if(confirm('警告：这将重置后台所有记忆缓存并强制结束当前进程。继续吗？')) {
                                        resetGame();
                                    }
                                }}
                                className="w-full py-4 bg-white border-2 border-red-200 hover:bg-red-500 hover:border-red-500 hover:text-white text-red-500 font-black rounded-2xl transition-all shadow-sm flex items-center justify-center space-x-2 text-sm uppercase tracking-widest"
                            >
                                <RefreshCcw size={18} />
                                <span>重置后端记忆与当前进度</span>
                            </button>
                        </div>
                    </div>
                )}
            </div>
        </div>
    );
};
