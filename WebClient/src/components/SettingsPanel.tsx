import { useState, useEffect } from 'react';
import { settingsApi, SystemSettings } from '../api/settingsApi';
import { Settings, Save, RefreshCcw, Server, Key, Cpu, Thermometer, Database } from 'lucide-react';

export const SettingsPanel = () => {
    const [settings, setSettings] = useState<SystemSettings>({
        base_url: '',
        api_key: '',
        model_name: '',
        temperature: 0.7,
        max_tokens: 1000
    });
    const [isLoading, setIsLoading] = useState(true);
    const [isSaving, setIsSaving] = useState(false);
    const [message, setMessage] = useState('');

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
                        <h2 className="text-2xl font-black text-[var(--color-cyan-dark)] tracking-wider">底层运行协议参数 (SYSTEM SETTINGS)</h2>
                        <p className="text-sm font-bold text-[var(--color-cyan-dark)]/60">调整大语言模型网关配置与生成策略</p>
                    </div>
                </div>
                {message && (
                    <div className={`px-4 py-2 rounded-lg font-bold text-sm ${message.includes('失败') ? 'bg-red-100 text-red-600' : 'bg-[var(--color-cyan-light)] text-[var(--color-cyan-dark)]'}`}>
                        {message}
                    </div>
                )}
            </div>

            <div className="flex-1 overflow-y-auto custom-scrollbar pr-4 space-y-6">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                    {/* UI components for each setting */}
                    <div className="bg-white p-5 rounded-2xl border-2 border-[var(--color-cyan-main)]/10 shadow-sm flex flex-col transition-all hover:border-[var(--color-yellow-main)]/50 group">
                        <label className="text-sm font-black text-[var(--color-cyan-main)] uppercase tracking-wider mb-3 flex items-center">
                            <Server size={16} className="mr-2" /> 网关地址 (Base URL)
                        </label>
                        <input 
                            type="text" 
                            value={settings.base_url} 
                            onChange={(e) => setSettings({...settings, base_url: e.target.value})}
                            className="bg-[var(--color-cyan-light)]/50 text-[var(--color-cyan-dark)] font-bold p-3 rounded-xl border border-[var(--color-cyan-main)]/20 outline-none focus:ring-2 focus:ring-[var(--color-yellow-main)] transition-shadow w-full"
                        />
                    </div>

                    <div className="bg-white p-5 rounded-2xl border-2 border-[var(--color-cyan-main)]/10 shadow-sm flex flex-col transition-all hover:border-[var(--color-yellow-main)]/50 group">
                        <label className="text-sm font-black text-[var(--color-cyan-main)] uppercase tracking-wider mb-3 flex items-center">
                            <Cpu size={16} className="mr-2" /> 模型版本 (Model Name)
                        </label>
                        <input 
                            type="text" 
                            value={settings.model_name} 
                            onChange={(e) => setSettings({...settings, model_name: e.target.value})}
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
                            onChange={(e) => setSettings({...settings, api_key: e.target.value})}
                            placeholder="留空则沿用后端环境变量"
                            className="bg-[var(--color-cyan-light)]/50 text-[var(--color-cyan-dark)] font-bold p-3 rounded-xl border border-[var(--color-cyan-main)]/20 outline-none focus:ring-2 focus:ring-[var(--color-yellow-main)] transition-shadow w-full"
                        />
                    </div>

                    <div className="bg-white p-5 rounded-2xl border-2 border-[var(--color-cyan-main)]/10 shadow-sm flex flex-col transition-all hover:border-[var(--color-yellow-main)]/50 group">
                        <div className="flex justify-between items-center mb-3">
                            <label className="text-sm font-black text-[var(--color-cyan-main)] uppercase tracking-wider flex items-center">
                                <Thermometer size={16} className="mr-2" /> 温度系数 (Temperature)
                            </label>
                            <span className="font-black text-[var(--color-yellow-main)] bg-[var(--color-cyan-dark)] px-2 py-0.5 rounded-lg text-xs">
                                {settings.temperature}
                            </span>
                        </div>
                        <input 
                            type="range" 
                            min="0" max="2" step="0.1"
                            value={settings.temperature} 
                            onChange={(e) => setSettings({...settings, temperature: parseFloat(e.target.value)})}
                            className="w-full h-2 bg-[var(--color-cyan-main)]/20 rounded-lg appearance-none cursor-pointer accent-[var(--color-cyan-main)] transition-colors hover:accent-[var(--color-yellow-main)]"
                        />
                    </div>

                    <div className="bg-white p-5 rounded-2xl border-2 border-[var(--color-cyan-main)]/10 shadow-sm flex flex-col transition-all hover:border-[var(--color-yellow-main)]/50 group">
                        <label className="text-sm font-black text-[var(--color-cyan-main)] uppercase tracking-wider mb-3 flex items-center">
                            <Database size={16} className="mr-2" /> 最大载荷 (Max Tokens)
                        </label>
                        <input 
                            type="number" 
                            min="100" max="4000" step="50"
                            value={settings.max_tokens} 
                            onChange={(e) => setSettings({...settings, max_tokens: parseInt(e.target.value)})}
                            className="bg-[var(--color-cyan-light)]/50 text-[var(--color-cyan-dark)] font-bold p-3 rounded-xl border border-[var(--color-cyan-main)]/20 outline-none focus:ring-2 focus:ring-[var(--color-yellow-main)] transition-shadow w-full"
                        />
                    </div>
                </div>
            </div>

            <div className="mt-8 pt-6 border-t-2 border-[var(--color-cyan-main)]/20 flex justify-end">
                <button
                    onClick={handleSave}
                    disabled={isSaving}
                    className="flex items-center px-8 py-4 bg-[var(--color-cyan-main)] text-white font-black rounded-xl shadow-lg shadow-[var(--color-cyan-main)]/30 hover:bg-[var(--color-cyan-dark)] hover:scale-105 transition-all disabled:opacity-50 disabled:scale-100 uppercase tracking-widest"
                >
                    {isSaving ? <RefreshCcw className="animate-spin mr-2" size={20} /> : <Save className="mr-2" size={20} />}
                    {isSaving ? '正在保存...' : '重写全局协议 (SAVE SETTINGS)'}
                </button>
            </div>
        </div>
    );
};
