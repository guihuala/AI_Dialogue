import { useState, useEffect } from 'react';
import { settingsApi, SystemSettings } from '../api/settingsApi';
import { gameApi } from '../api/gameApi';
import { useGameStore } from '../store/gameStore';
import { Settings, Save, RefreshCcw, Server, Thermometer, Database, Type, Trash2, Milestone, Zap } from 'lucide-react';
import { ConfirmDialog } from './common/ConfirmDialog';

const AI_PRESETS = [
    { name: 'DeepSeek (深度求索)', url: 'https://api.deepseek.com/v1', models: ['deepseek-chat', 'deepseek-reasoner'] },
    { name: 'SiliconFlow (硅基流动)', url: 'https://api.siliconflow.cn/v1', models: ['deepseek-ai/DeepSeek-V3', 'deepseek-ai/DeepSeek-R1', 'Qwen/Qwen2.5-72B-Instruct', 'THUDM/glm-4-9b-chat'] },
    { name: 'OpenAI', url: 'https://api.openai.com/v1', models: ['gpt-4o-mini', 'gpt-4o'] },
    { name: 'ZhiPu (智谱清言)', url: 'https://open.bigmodel.cn/api/paas/v4', models: ['glm-4-plus', 'glm-4-flash'] },
    { name: 'Ollama (本地推理)', url: 'http://localhost:11434/v1', models: ['qwen2.5:7b', 'llama3:8b', 'deepseek-r1:7b'] }
];

const TEMP_MIN = 0.2;
const TEMP_MAX = 1.2;
const TOKENS_MIN = 300;
const TOKENS_MAX = 2000;
const STABLE_TEMP_MIN = 0.3;
const STABLE_TEMP_MAX = 0.8;
const STABLE_TOKENS_MIN = 1000;
const STABLE_TOKENS_MAX = 1600;

export const SettingsPanel = () => {
    const [settings, setSettings] = useState<SystemSettings>({
        base_url: '',
        api_key: '',
        model_name: '',
        temperature: 0.7,
        max_tokens: 1000,
        typewriter_speed: 30,
        latency_mode: 'balanced',
        dialogue_mode: 'single_dm',
        stability_mode: 'stable'
    });
    const [isLoading, setIsLoading] = useState(true);
    const [isSaving, setIsSaving] = useState(false);
    const [message, setMessage] = useState('');
    const [activeTab, setActiveTab] = useState<'ai' | 'preferences' | 'memory'>('ai');
    const [confirmDialog, setConfirmDialog] = useState<{
        open: boolean;
        title: string;
        message: string;
        confirmText?: string;
        danger?: boolean;
        onConfirm?: () => Promise<void> | void;
    }>({ open: false, title: '', message: '' });
    const [memories, setMemories] = useState<any[]>([]);
    const [memoryFilter, setMemoryFilter] = useState({ char: '', type: '' });
    const { currentSaveId, active_roommates } = useGameStore();

    // Store values
    const {
        audioVolume, setAudioVolume,
        isMuted, setMuted,
        uiTransparency, setUiTransparency,
        resetGame,
        setTypewriterSpeed
    } = useGameStore();

    useEffect(() => {
        const fetchSettings = async () => {
            try {
                const data = await settingsApi.getSettings();
                if (data) {
                    setSettings({
                        ...data,
                        stability_mode: data.stability_mode || 'stable'
                    });
                }
            } catch (err) {
                console.error('Failed to fetch settings:', err);
                setMessage('读取设置失败。请检查后端是否正常运行。');
            } finally {
                setIsLoading(false);
            }
        };
        fetchSettings();
    }, []);

    useEffect(() => {
        if (activeTab === 'memory') {
            fetchMemories();
        }
    }, [activeTab, memoryFilter, currentSaveId]);

    const fetchMemories = async () => {
        try {
            const res = await gameApi.getMemories(currentSaveId, memoryFilter.char, memoryFilter.type);
            setMemories(res.data || []);
        } catch (err) {
            console.error('Failed to fetch memories:', err);
        }
    };

    const handleDeleteMemory = async (id: string) => {
        setConfirmDialog({
            open: true,
            title: '抹除记忆',
            message: '确定要抹除这条记忆吗？AI 将不再能检索到它。',
            confirmText: '确认抹除',
            danger: true,
            onConfirm: async () => {
                try {
                    await gameApi.deleteMemory(id);
                    setMemories(memories.filter(m => m.id !== id));
                } catch (err) {
                    console.error('Failed to delete memory:', err);
                }
            }
        });
    };

    const handleSave = async () => {
        setIsSaving(true);
        setMessage('');
        try {
            const safeSettings = {
                ...settings,
                temperature: settings.stability_mode === 'stable'
                    ? Math.max(STABLE_TEMP_MIN, Math.min(STABLE_TEMP_MAX, settings.temperature))
                    : Math.max(TEMP_MIN, Math.min(TEMP_MAX, settings.temperature)),
                max_tokens: settings.stability_mode === 'stable'
                    ? Math.max(STABLE_TOKENS_MIN, Math.min(STABLE_TOKENS_MAX, settings.max_tokens))
                    : Math.max(TOKENS_MIN, Math.min(TOKENS_MAX, settings.max_tokens))
            };
            await settingsApi.updateSettings(safeSettings);
            setSettings(safeSettings);
            setTypewriterSpeed(safeSettings.typewriter_speed);
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
                        <p className="text-sm font-bold text-[var(--color-cyan-dark)]/60">个性化调整您的生存体验</p>
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
                <button
                    onClick={() => setActiveTab('memory')}
                    className={`px-6 py-2.5 rounded-xl font-black text-xs uppercase tracking-widest transition-all ${activeTab === 'memory' ? 'bg-[var(--color-cyan-main)] text-white shadow-md' : 'text-[var(--color-cyan-dark)]/60 hover:text-[var(--color-cyan-dark)]'}`}
                >
                    记忆片段
                </button>
            </div>

            <div className="flex-1 overflow-y-auto custom-scrollbar pr-4 space-y-6">
                {activeTab === 'ai' ? (
                    <div className="animate-in fade-in slide-in-from-bottom-4 duration-500 flex flex-col h-full overflow-hidden">
                        {/* Main Interaction Area: Sidebar + Detail */}
                        <div className="flex flex-col lg:flex-row gap-6 flex-1 overflow-hidden min-h-0">
                            {/* Left: Provider Selection Sidebar */}
                            <div className="lg:w-1/3 flex flex-col space-y-3 overflow-y-auto pr-2 custom-scrollbar">
                                <div className="flex items-center justify-between px-2 mb-2">
                                    <span className="text-[11px] font-black text-[var(--color-cyan-main)] uppercase tracking-[0.15em]">推荐服务商 / Providers</span>
                                    <Zap size={14} className="text-[var(--color-yellow-main)]" />
                                </div>
                                {AI_PRESETS.map((preset) => (
                                    <button
                                        key={preset.name}
                                        onClick={() => {
                                            setSettings(s => ({
                                                ...s,
                                                base_url: preset.url,
                                                model_name: preset.models[0]
                                            }));
                                        }}
                                        className={`group relative p-4 rounded-2xl border-2 transition-all text-left flex items-start space-x-4 ${settings.base_url === preset.url
                                            ? 'bg-white border-[var(--color-cyan-main)] shadow-lg scale-[1.02]'
                                            : 'bg-white/40 border-transparent hover:border-[var(--color-cyan-main)]/30 hover:bg-white/60'
                                            }`}
                                    >
                                        <div className={`p-2.5 rounded-xl transition-colors ${settings.base_url === preset.url
                                            ? 'bg-[var(--color-cyan-main)] text-white'
                                            : 'bg-white text-[var(--color-cyan-dark)]/40 group-hover:text-[var(--color-cyan-main)] group-hover:bg-white/80 border border-[var(--color-cyan-main)]/10'
                                            }`}>
                                            <Server size={18} />
                                        </div>
                                        <div className="flex-1 min-w-0">
                                            <div className="font-black text-sm text-[var(--color-cyan-dark)] truncate">{preset.name}</div>
                                            <div className="text-[9px] font-bold text-[var(--color-cyan-dark)]/40 truncate tracking-tight">{preset.url}</div>
                                        </div>
                                        {settings.base_url === preset.url && (
                                            <div className="absolute right-4 top-1/2 -translate-y-1/2 w-1.5 h-1.5 rounded-full bg-[var(--color-yellow-main)] shadow-[0_0_8px_var(--color-yellow-main)]" />
                                        )}
                                    </button>
                                ))}
                            </div>

                            {/* Right: Configuration Form */}
                            <div className="lg:w-2/3 flex flex-col space-y-6 overflow-y-auto pr-2 custom-scrollbar">
                                {/* Base Config Card */}
                                <div className="bg-white p-6 rounded-3xl border-2 border-[var(--color-cyan-main)]/10 shadow-sm space-y-6">
                                    <div className="flex items-center space-x-3 mb-2">
                                        <Database size={18} className="text-[var(--color-cyan-main)]" />
                                        <span className="text-xs font-black text-[var(--color-cyan-dark)] uppercase">接口基础参数</span>
                                    </div>

                                    <div className="space-y-4">
                                        <div className="group">
                                            <label className="block text-[10px] font-black text-[var(--color-cyan-dark)]/40 uppercase mb-2 ml-1">网关 (Base URL)</label>
                                            <div className="relative">
                                                <input
                                                    type="text"
                                                    value={settings.base_url}
                                                    onChange={(e) => setSettings({ ...settings, base_url: e.target.value })}
                                                    className="w-full bg-[var(--color-cyan-light)]/30 text-[var(--color-cyan-dark)] font-bold p-3.5 rounded-xl border-2 border-transparent focus:border-[var(--color-cyan-main)]/30 focus:bg-white outline-none transition-all pr-12"
                                                    placeholder="https://..."
                                                />
                                                <RefreshCcw className="absolute right-4 top-1/2 -translate-y-1/2 text-[var(--color-cyan-dark)]/20 group-hover:text-[var(--color-cyan-main)]/40 transition-colors" size={16} />
                                            </div>
                                        </div>

                                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                            <div>
                                                <label className="block text-[10px] font-black text-[var(--color-cyan-dark)]/40 uppercase mb-2 ml-1">默认模型</label>
                                                {settings.base_url && AI_PRESETS.find(p => p.url === settings.base_url) ? (
                                                    <select
                                                        value={settings.model_name}
                                                        onChange={(e) => setSettings(s => ({ ...s, model_name: e.target.value }))}
                                                        className="w-full bg-white text-[var(--color-cyan-dark)] font-black p-3.5 rounded-xl border-2 border-[var(--color-cyan-main)]/10 focus:border-[var(--color-cyan-main)] outline-none transition-all appearance-none cursor-pointer"
                                                    >
                                                        {AI_PRESETS.find(p => p.url === settings.base_url)?.models.map(m => (
                                                            <option key={m} value={m}>{m}</option>
                                                        ))}
                                                    </select>
                                                ) : (
                                                    <input
                                                        type="text"
                                                        value={settings.model_name}
                                                        onChange={(e) => setSettings({ ...settings, model_name: e.target.value })}
                                                        className="w-full bg-[var(--color-cyan-light)]/30 text-[var(--color-cyan-dark)] font-bold p-3.5 rounded-xl border-2 border-transparent focus:border-[var(--color-cyan-main)]/30 focus:bg-white outline-none transition-all"
                                                        placeholder="例如: gpt-4"
                                                    />
                                                )}
                                            </div>
                                            <div>
                                                <label className="block text-[10px] font-black text-[var(--color-cyan-dark)]/40 uppercase mb-2 ml-1">通信密钥</label>
                                                <input
                                                    type="password"
                                                    value={settings.api_key}
                                                    onChange={(e) => setSettings({ ...settings, api_key: e.target.value })}
                                                    placeholder="已加密保护"
                                                    className="w-full bg-[var(--color-cyan-light)]/30 text-[var(--color-cyan-dark)] font-bold p-3.5 rounded-xl border-2 border-transparent focus:border-[var(--color-cyan-main)]/30 focus:bg-white outline-none transition-all"
                                                />
                                            </div>
                                        </div>
                                    </div>
                                </div>

                                {/* Advanced Tuning Card */}
                                <div className="bg-white/60 backdrop-blur-sm p-6 rounded-3xl border-2 border-[var(--color-cyan-main)]/10 shadow-sm space-y-6">
                                    <div className="flex items-center space-x-3 mb-2">
                                        <Thermometer size={18} className="text-[var(--color-yellow-main)]" />
                                        <span className="text-xs font-black text-[var(--color-cyan-dark)] uppercase">高级性能参数 / Advanced Tuning</span>
                                    </div>

                                    <div className="space-y-8 pl-1">
                                        <div>
                                            <div className="flex justify-between items-center mb-4">
                                                <div className="flex flex-col">
                                                    <span className="text-[11px] font-black text-[var(--color-cyan-dark)]">性能模式</span>
                                                    <span className="text-[9px] font-bold text-[var(--color-cyan-dark)]/40">调整响应速度与剧情质量的平衡</span>
                                                </div>
                                            </div>
                                            <select
                                                value={settings.latency_mode}
                                                onChange={(e) => setSettings({ ...settings, latency_mode: e.target.value as any })}
                                                className="w-full bg-white text-[var(--color-cyan-dark)] font-black p-3.5 rounded-xl border-2 border-[var(--color-cyan-main)]/10 focus:border-[var(--color-cyan-main)] outline-none transition-all appearance-none cursor-pointer"
                                            >
                                                <option value="balanced">均衡模式（推荐）</option>
                                                <option value="fast">极速模式（优先速度）</option>
                                                <option value="story">剧情优先（优先质量）</option>
                                            </select>
                                        </div>

                                        <div>
                                            <div className="flex justify-between items-center mb-4">
                                                <div className="flex flex-col">
                                                    <span className="text-[11px] font-black text-[var(--color-cyan-dark)]">对话架构</span>
                                                    <span className="text-[9px] font-bold text-[var(--color-cyan-dark)]/40">选择单一DM或多Agent模式</span>
                                                </div>
                                            </div>
                                            <select
                                                value={settings.dialogue_mode}
                                                onChange={(e) => setSettings({ ...settings, dialogue_mode: e.target.value as any })}
                                                className="w-full bg-white text-[var(--color-cyan-dark)] font-black p-3.5 rounded-xl border-2 border-[var(--color-cyan-main)]/10 focus:border-[var(--color-cyan-main)] outline-none transition-all appearance-none cursor-pointer"
                                            >
                                                <option value="single_dm">单一DM统筹（推荐稳定）</option>
                                                <option value="npc_dm">NPC-DM 多Agent（实验）</option>
                                            </select>
                                        </div>

                                        <div>
                                            <div className="flex justify-between items-center mb-4">
                                                <div className="flex flex-col">
                                                    <span className="text-[11px] font-black text-[var(--color-cyan-dark)]">输出稳定性</span>
                                                    <span className="text-[9px] font-bold text-[var(--color-cyan-dark)]/40">Stable 更抗 JSON 崩坏，Balanced 更自由</span>
                                                </div>
                                            </div>
                                            <select
                                                value={settings.stability_mode}
                                                onChange={(e) => setSettings({ ...settings, stability_mode: e.target.value as any })}
                                                className="w-full bg-white text-[var(--color-cyan-dark)] font-black p-3.5 rounded-xl border-2 border-[var(--color-cyan-main)]/10 focus:border-[var(--color-cyan-main)] outline-none transition-all appearance-none cursor-pointer"
                                            >
                                                <option value="stable">Stable（推荐）</option>
                                                <option value="balanced">Balanced（更自由）</option>
                                            </select>
                                        </div>

                                        <div>
                                            <div className="flex justify-between items-center mb-4">
                                                <div className="flex flex-col">
                                                    <span className="text-[11px] font-black text-[var(--color-cyan-dark)]">采样温度 (Temperature)</span>
                                                    <span className="text-[9px] font-bold text-[var(--color-cyan-dark)]/40">
                                                        {settings.stability_mode === 'stable' ? 'Stable 推荐 0.3-0.8（更稳）' : 'Balanced 推荐 0.2-1.2（更自由）'}
                                                    </span>
                                                </div>
                                                <span className="font-black text-[var(--color-yellow-main)] bg-[var(--color-cyan-dark)] px-3 py-1 rounded-lg text-xs tabular-nums">
                                                    {settings.temperature.toFixed(1)}
                                                </span>
                                            </div>
                                            <input
                                                type="range"
                                                min={settings.stability_mode === 'stable' ? STABLE_TEMP_MIN : TEMP_MIN}
                                                max={settings.stability_mode === 'stable' ? STABLE_TEMP_MAX : TEMP_MAX}
                                                step="0.1"
                                                value={settings.temperature}
                                                onChange={(e) => setSettings({ ...settings, temperature: parseFloat(e.target.value) })}
                                                className="w-full h-1.5 bg-[var(--color-cyan-main)]/10 rounded-lg appearance-none cursor-pointer accent-[var(--color-cyan-main)] transition-all hover:h-2"
                                            />
                                        </div>

                                        <div>
                                            <div className="flex justify-between items-center mb-4">
                                                <div className="flex flex-col">
                                                    <span className="text-[11px] font-black text-[var(--color-cyan-dark)]">单次最大Token (Limit)</span>
                                                    <span className="text-[9px] font-bold text-[var(--color-cyan-dark)]/40">
                                                        {settings.stability_mode === 'stable' ? 'Stable 推荐 1000-1600（防截断且更稳）' : 'Balanced 推荐 300-2000'}
                                                    </span>
                                                </div>
                                                <div className="flex items-center space-x-2">
                                                    <span className="font-black text-[var(--color-cyan-main)] text-sm">{settings.max_tokens}</span>
                                                    <span className="text-[9px] font-bold text-[var(--color-cyan-dark)]/20">tk</span>
                                                </div>
                                            </div>
                                            <input
                                                type="range"
                                                min={settings.stability_mode === 'stable' ? STABLE_TOKENS_MIN : TOKENS_MIN}
                                                max={settings.stability_mode === 'stable' ? STABLE_TOKENS_MAX : TOKENS_MAX}
                                                step="50"
                                                value={settings.max_tokens}
                                                onChange={(e) => setSettings({ ...settings, max_tokens: parseInt(e.target.value) })}
                                                className="w-full h-1.5 bg-[var(--color-cyan-main)]/10 rounded-lg appearance-none cursor-pointer accent-[var(--color-cyan-main)] transition-all hover:h-2"
                                            />
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>

                        {/* Sticky Action Bar */}
                        <div className="mt-8 pt-6 border-t-2 border-[var(--color-cyan-main)]/10 flex items-center justify-between bg-white/40 sticky bottom-0 backdrop-blur-sm -mx-2 px-2 pb-2">
                            <div className="flex items-center space-x-2 text-[10px] font-bold text-[var(--color-cyan-dark)]/40">
                                <span className="w-1.5 h-1.5 bg-[var(--color-yellow-main)] rounded-full mr-1"></span>
                                修改配置需要点击右侧保存生效 / Auto-save not active
                            </div>
                            <button
                                onClick={handleSave}
                                disabled={isSaving}
                                className="flex items-center px-10 py-4 bg-[var(--color-cyan-main)] text-white font-black rounded-2xl shadow-xl shadow-[var(--color-cyan-main)]/30 hover:bg-[var(--color-cyan-dark)] hover:scale-[1.05] active:scale-[0.98] transition-all disabled:opacity-50 disabled:scale-100 uppercase tracking-[0.2em] text-xs"
                            >
                                {isSaving ? <RefreshCcw className="animate-spin mr-3" size={18} /> : <Save className="mr-3" size={18} />}
                                {isSaving ? '正在应用配置...' : '保存并应用设置'}
                            </button>
                        </div>
                    </div>
                ) : activeTab === 'preferences' ? (
                    <div className="animate-in fade-in slide-in-from-bottom-4 duration-500 space-y-8">
                        {/* Audio Settings Content... */}
                        {/* (Internal content omitted for brevity, keeping structure) */}
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
                                    setConfirmDialog({
                                        open: true,
                                        title: '重置记忆与进度',
                                        message: '警告：这将重置后台所有记忆缓存并强制结束当前进程。继续吗？',
                                        confirmText: '确认重置',
                                        danger: true,
                                        onConfirm: async () => {
                                            await resetGame();
                                        }
                                    });
                                }}
                                className="w-full py-4 bg-white border-2 border-red-200 hover:bg-red-500 hover:border-red-500 hover:text-white text-red-500 font-black rounded-2xl transition-all shadow-sm flex items-center justify-center space-x-2 text-sm uppercase tracking-widest"
                            >
                                <RefreshCcw size={18} />
                                <span>重置记忆与进度</span>
                            </button>
                        </div>
                    </div>
                ) : (
                    <div className="animate-in fade-in slide-in-from-bottom-4 duration-500 flex flex-col h-full">
                        {/* Memory Control Hub */}
                        <div className="flex items-center justify-between mb-8">
                            <div className="flex items-center space-x-6">
                                <div className="bg-white/60 p-4 rounded-2xl border-2 border-[var(--color-cyan-main)]/10">
                                    <label className="block text-[9px] font-black text-[var(--color-cyan-dark)]/40 uppercase mb-2">角色筛选 Character</label>
                                    <select 
                                        value={memoryFilter.char}
                                        onChange={(e) => setMemoryFilter({...memoryFilter, char: e.target.value})}
                                        className="bg-transparent text-xs font-bold text-[var(--color-cyan-dark)] outline-none min-w-[120px]"
                                    >
                                        <option value="">全部成员</option>
                                        {active_roommates.map(name => <option key={name} value={name}>{name}</option>)}
                                    </select>
                                </div>
                                <div className="bg-white/60 p-4 rounded-2xl border-2 border-[var(--color-cyan-main)]/10">
                                    <label className="block text-[9px] font-black text-[var(--color-cyan-dark)]/40 uppercase mb-2">记忆类型 Concept</label>
                                    <select 
                                        value={memoryFilter.type}
                                        onChange={(e) => setMemoryFilter({...memoryFilter, type: e.target.value})}
                                        className="bg-transparent text-xs font-bold text-[var(--color-cyan-dark)] outline-none min-w-[120px]"
                                    >
                                        <option value="">全部类型</option>
                                        <option value="lore">固定设定 (Lore)</option>
                                        <option value="observation">观测记录 (Obs)</option>
                                        <option value="action">行为历史 (Act)</option>
                                    </select>
                                </div>
                            </div>
                            <div className="text-right">
                                <p className="text-[10px] font-black text-[var(--color-cyan-dark)] uppercase">当前检索范围</p>
                                <p className="text-[14px] font-black text-[var(--color-cyan-main)] uppercase">{currentSaveId || 'NEW GAME'}</p>
                            </div>
                        </div>

                        {/* Memory Flow Area */}
                        <div className="flex-1 space-y-4 overflow-y-auto custom-scrollbar pr-2 pb-10">
                            {memories.length === 0 ? (
                                <div className="h-60 flex flex-col items-center justify-center border-4 border-dashed border-[var(--color-cyan-main)]/10 rounded-3xl text-[var(--color-cyan-dark)]/20">
                                    <Database size={48} className="mb-4 opacity-20" />
                                    <span className="text-xs font-black uppercase tracking-widest">暂时没有符合条件的记忆碎片</span>
                                    <span className="text-[9px] font-bold mt-1 opacity-50">进行对话或在剧情中选择选项将产生新的记忆</span>
                                </div>
                            ) : (
                                memories.map((m) => (
                                    <div key={m.id} className="group bg-white/60 hover:bg-white p-5 rounded-2xl border-2 border-[var(--color-cyan-main)]/10 hover:border-[var(--color-cyan-main)]/30 transition-all shadow-sm hover:shadow-md relative overflow-hidden">
                                        <div className="flex justify-between items-start mb-3">
                                            <div className="flex items-center space-x-3">
                                                <span className={`px-2 py-0.5 rounded-md text-[9px] font-black uppercase ${
                                                    m.metadata?.type === 'lore' ? 'bg-purple-100 text-purple-600' :
                                                    m.metadata?.type === 'observation' ? 'bg-blue-100 text-blue-600' :
                                                    'bg-green-100 text-green-600'
                                                }`}>
                                                    {m.metadata?.type || 'Unknown'}
                                                </span>
                                                <span className="text-[9px] font-bold text-[var(--color-cyan-dark)]/30 tabular-nums">
                                                    {m.metadata?.timestamp ? new Date(m.metadata.timestamp).toLocaleString() : 'DATALINK_ESTABLISHED'}
                                                </span>
                                            </div>
                                            <button 
                                                onClick={() => handleDeleteMemory(m.id)}
                                                className="opacity-0 group-hover:opacity-100 p-2 text-red-300 hover:text-red-500 hover:bg-red-50 rounded-lg transition-all"
                                            >
                                                <Trash2 size={14} />
                                            </button>
                                        </div>
                                        <p className="text-xs font-bold text-[var(--color-cyan-dark)] leading-relaxed">
                                            {m.content}
                                        </p>
                                        {/* Decorative logic lines */}
                                        <div className="absolute left-0 bottom-0 h-1 bg-gradient-to-r from-[var(--color-cyan-main)] to-transparent w-full opacity-0 group-hover:opacity-40 transition-all"></div>
                                    </div>
                                ))
                            )}
                        </div>
                    </div>
                )}
            </div>

            <ConfirmDialog
                open={confirmDialog.open}
                title={confirmDialog.title}
                message={confirmDialog.message}
                confirmText={confirmDialog.confirmText || '确认'}
                danger={!!confirmDialog.danger}
                onCancel={() => setConfirmDialog({ open: false, title: '', message: '' })}
                onConfirm={async () => {
                    const handler = confirmDialog.onConfirm;
                    setConfirmDialog({ open: false, title: '', message: '' });
                    if (handler) await handler();
                }}
            />
        </div>
    );
};
