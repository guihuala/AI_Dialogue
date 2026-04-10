import { useState, useEffect, useRef } from 'react';
import { settingsApi, SystemSettings } from '../api/settingsApi';
import { gameApi } from '../api/gameApi';
import { useGameStore } from '../store/gameStore';
import { RefreshCcw, Thermometer, Database, Type, Trash2 } from 'lucide-react';
import { ConfirmDialog } from './common/ConfirmDialog';

const AI_PRESETS = [
    { id: 'deepseek', name: 'DeepSeek', url: 'https://api.deepseek.com/v1', models: ['deepseek-chat', 'deepseek-reasoner'] },
    { id: 'siliconflow', name: 'SiliconFlow', url: 'https://api.siliconflow.cn/v1', models: ['deepseek-ai/DeepSeek-V3', 'deepseek-ai/DeepSeek-R1', 'Qwen/Qwen2.5-72B-Instruct', 'THUDM/glm-4-9b-chat'] },
    { id: 'openai', name: 'OpenAI', url: 'https://api.openai.com/v1', models: ['gpt-4o-mini', 'gpt-4o'] },
    { id: 'zhipu', name: 'ZhiPu', url: 'https://open.bigmodel.cn/api/paas/v4', models: ['glm-4-plus', 'glm-4-flash'] },
    { id: 'ollama', name: 'Ollama', url: 'http://localhost:11434/v1', models: ['qwen2.5:7b', 'llama3:8b', 'deepseek-r1:7b'] }
];

const TEMP_MIN = 0.2;
const TEMP_MAX = 1.2;
const TOKENS_MIN = 300;
const TOKENS_MAX = 2000;
const STABLE_TEMP_MIN = 0.3;
const STABLE_TEMP_MAX = 0.8;
const STABLE_TOKENS_MIN = 700;
const STABLE_TOKENS_MAX = 1200;

const PROVIDER_BRANDS = {
    deepseek: {
        label: 'DS',
        logoUrl: 'https://cdn.deepseek.com/logo.png?x-image-process=image%2Fresize%2Cw_1920',
        logoClassName: 'object-contain scale-[1.85]',
        className: 'bg-white text-white',
        ringClassName: 'ring-sky-200/70'
    },
    siliconflow: {
        label: 'SF',
        logoUrl: 'https://www.siliconflow.cn/favicon.ico',
        logoClassName: 'object-contain',
        className: 'bg-white text-white',
        ringClassName: 'ring-fuchsia-200/70'
    },
    openai: {
        label: 'OA',
        logoUrl: 'https://openai.com/favicon.ico',
        logoClassName: 'object-contain',
        className: 'bg-white text-white',
        ringClassName: 'ring-slate-300/70'
    },
    zhipu: {
        label: 'ZP',
        logoUrl: 'https://docs.bigmodel.cn/favicon.ico',
        logoClassName: 'object-contain',
        className: 'bg-white text-white',
        ringClassName: 'ring-emerald-200/70'
    },
    ollama: {
        label: 'OL',
        logoUrl: 'https://docs.ollama.com/favicon.ico',
        logoClassName: 'object-contain',
        className: 'bg-white text-white',
        ringClassName: 'ring-orange-200/70'
    }
} as const;

const MEMORY_TYPE_LABELS: Record<string, string> = {
    lore: '固定设定',
    event_reflection: '事件总结',
    narrative_milestone: '关系里程碑',
    weekly_summary: '阶段总结',
    short_term_dialogue: '短期缓存',
};

const ProviderLogo = ({
    providerId,
    isActive
}: {
    providerId: keyof typeof PROVIDER_BRANDS;
    isActive: boolean;
}) => {
    const brand = PROVIDER_BRANDS[providerId];
    const [imageFailed, setImageFailed] = useState(false);

    return (
        <div className={`flex h-11 w-11 items-center justify-center overflow-hidden rounded-xl text-[11px] font-black tracking-[0.18em] shadow-sm ring-1 ${brand.className} ${isActive ? `${brand.ringClassName} shadow-md` : 'opacity-90'}`}>
            {!imageFailed ? (
                <img
                    src={brand.logoUrl}
                    alt={`${providerId} logo`}
                    className={`h-7 w-7 ${brand.logoClassName}`}
                    loading="lazy"
                    onError={() => setImageFailed(true)}
                />
            ) : (
                <span className="text-[var(--color-cyan-dark)]">{brand.label}</span>
            )}
        </div>
    );
};

export const SettingsPanel = () => {
    const didHydrateRef = useRef(false);
    const toastTimerRef = useRef<number | null>(null);
    const [settings, setSettings] = useState<SystemSettings>({
        base_url: '',
        api_key: '',
        model_name: '',
        temperature: 0.7,
        max_tokens: 1000,
        typewriter_speed: 30,
        latency_mode: 'balanced',
        dialogue_mode: 'single_dm',
        stability_mode: 'stable',
        turn_debug: false
    });
    const [isLoading, setIsLoading] = useState(true);
    const [toast, setToast] = useState<{ text: string; tone: 'error' | 'success' } | null>(null);
    const [validationState, setValidationState] = useState<'idle' | 'checking' | 'success' | 'error'>('idle');
    const [validationMessage, setValidationMessage] = useState('尚未校验');
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
    const [memoryFilter, setMemoryFilter] = useState({ char: '', type: 'event_reflection' });
    const { currentSaveId, active_roommates } = useGameStore();

    // Store values
    const {
        uiTransparency, setUiTransparency,
        resetGame,
        setTypewriterSpeed
    } = useGameStore();

    const showToast = (text: string, tone: 'error' | 'success') => {
        setToast({ text, tone });
        if (toastTimerRef.current) {
            window.clearTimeout(toastTimerRef.current);
        }
        toastTimerRef.current = window.setTimeout(() => setToast(null), tone === 'error' ? 3200 : 1800);
    };

    useEffect(() => {
        const fetchSettings = async () => {
            try {
                const data = await settingsApi.getSettings();
                if (data) {
                    setSettings({
                        ...data,
                        stability_mode: data.stability_mode || 'stable',
                        turn_debug: !!data.turn_debug
                    });
                    const hasApiConfig = Boolean(String(data.api_key || '').trim() && String(data.base_url || '').trim() && String(data.model_name || '').trim());
                    setValidationState(hasApiConfig ? 'idle' : 'error');
                    setValidationMessage(hasApiConfig ? '已保存，建议测试连接' : '当前还没有完成模型配置');
                }
            } catch (err) {
                console.error('Failed to fetch settings:', err);
                showToast('读取设置失败。请检查后端是否正常运行。', 'error');
            } finally {
                setIsLoading(false);
            }
        };
        fetchSettings();
    }, []);

    useEffect(() => {
        if (isLoading) return;
        if (!didHydrateRef.current) {
            didHydrateRef.current = true;
            return;
        }

        const timer = window.setTimeout(async () => {
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
                setValidationState('idle');
                setValidationMessage('已保存，建议测试连接');
                showToast('已自动保存', 'success');
            } catch (error) {
                console.error('Failed to auto-save settings:', error);
                showToast('保存失败，请重试。', 'error');
            }
        }, 700);

        return () => window.clearTimeout(timer);
    }, [settings, isLoading, setTypewriterSpeed]);

    useEffect(() => {
        if (isLoading) return;
        setValidationState('idle');
        setValidationMessage('已修改，等待自动保存');
    }, [isLoading, settings.api_key, settings.base_url, settings.model_name]);

    useEffect(() => {
        return () => {
            if (toastTimerRef.current) {
                window.clearTimeout(toastTimerRef.current);
            }
        };
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
            title: '删除记忆',
            message: '确定要删除这条记忆吗？AI 将不再能检索到它。',
            confirmText: '确认',
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

    const handleValidateSettings = async () => {
        setValidationState('checking');
        setValidationMessage('正在测试连接...');
        try {
            const result = await settingsApi.validateSettings();
            setValidationState('success');
            setValidationMessage(result.message || '配置有效');
            showToast('模型配置可用', 'success');
        } catch (error: any) {
            const detail = String(error?.response?.data?.detail || error?.message || '').trim();
            setValidationState('error');
            setValidationMessage(detail || '配置无效，请检查网关、模型和 API Key');
            showToast(detail || '配置校验失败', 'error');
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
        <div className="flex-1 flex flex-col h-full relative p-4 md:p-4">
            {toast && (
                <div className="pointer-events-none fixed right-6 top-24 z-[120] animate-fade-in-up">
                    <div className={`rounded-2xl px-4 py-3 text-sm font-black shadow-xl backdrop-blur-xl ${toast.tone === 'error' ? 'bg-red-100/95 text-red-600 border border-red-200/80' : 'bg-white/92 text-[var(--color-cyan-dark)] border border-[var(--color-cyan-main)]/10'}`}>
                        {toast.text}
                    </div>
                </div>
            )}

            {/* Tab Header */}
            <div className="flex space-x-2 mb-4 bg-[var(--color-cyan-light)]/30 p-1 rounded-xl w-fit">
                <button
                    onClick={() => setActiveTab('ai')}
                    className={`px-5 py-2 rounded-lg font-black text-sm transition-all ${activeTab === 'ai' ? 'bg-[var(--color-cyan-main)] text-white shadow-md' : 'text-[var(--color-cyan-dark)]/60 hover:text-[var(--color-cyan-dark)]'}`}
                >
                    AI网关
                </button>
                <button
                    onClick={() => setActiveTab('preferences')}
                    className={`px-5 py-2 rounded-lg font-black text-sm transition-all ${activeTab === 'preferences' ? 'bg-[var(--color-cyan-main)] text-white shadow-md' : 'text-[var(--color-cyan-dark)]/60 hover:text-[var(--color-cyan-dark)]'}`}
                >
                    偏好设置
                </button>
                <button
                    onClick={() => setActiveTab('memory')}
                    className={`px-5 py-2 rounded-lg font-black text-sm transition-all ${activeTab === 'memory' ? 'bg-[var(--color-cyan-main)] text-white shadow-md' : 'text-[var(--color-cyan-dark)]/60 hover:text-[var(--color-cyan-dark)]'}`}
                >
                    记忆片段
                </button>
            </div>

            <div className="flex-1 overflow-y-auto custom-scrollbar pr-1 space-y-3">
                {activeTab === 'ai' ? (
                    <div className="animate-in fade-in slide-in-from-bottom-4 duration-500 flex flex-col h-full min-h-0">
                        {/* Main Interaction Area: Sidebar + Detail */}
                        <div className="flex flex-col lg:flex-row gap-3 flex-1 h-full overflow-hidden min-h-0">
                            {/* Left: Provider Selection Sidebar */}
                            <div className="lg:w-1/3 h-full min-h-0 flex flex-col space-y-2 overflow-y-auto pr-1 custom-scrollbar">
                                <div className="px-2 mb-2 text-sm font-black text-[var(--color-cyan-main)]">服务商</div>
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
                                        className={`group relative p-3 rounded-xl border transition-all text-left flex items-start space-x-3 ${settings.base_url === preset.url
                                            ? 'bg-white border-[var(--color-cyan-main)] shadow-md'
                                            : 'bg-white/40 border-[var(--color-cyan-main)]/8 hover:border-[var(--color-cyan-main)]/30 hover:bg-white/60'
                                            }`}
                                    >
                                        <ProviderLogo
                                            providerId={preset.id as keyof typeof PROVIDER_BRANDS}
                                            isActive={settings.base_url === preset.url}
                                        />
                                        <div className="flex-1 min-w-0">
                                            <div className="font-black text-sm text-[var(--color-cyan-dark)] truncate">{preset.name}</div>
                                            <div className="text-xs font-bold text-[var(--color-cyan-dark)]/40 truncate">{preset.url}</div>
                                        </div>
                                        {settings.base_url === preset.url && (
                                            <div className="absolute right-4 top-1/2 -translate-y-1/2 w-1.5 h-1.5 rounded-full bg-[var(--color-yellow-main)] shadow-[0_0_8px_var(--color-yellow-main)]" />
                                        )}
                                    </button>
                                ))}
                            </div>

                            {/* Right: Configuration Form */}
                            <div className="lg:w-2/3 h-full min-h-0 flex flex-col space-y-3 pr-1 overflow-y-auto custom-scrollbar">
                                {/* Base Config Card */}
                                <div className="bg-white/72 p-4 rounded-xl border border-[var(--color-cyan-main)]/10 shadow-sm space-y-4">
                                    <div className="flex items-center justify-between gap-3 mb-2">
                                        <div className="flex items-center space-x-3">
                                            <Database size={18} className="text-[var(--color-cyan-main)]" />
                                            <span className="text-sm font-black text-[var(--color-cyan-dark)]">参数</span>
                                        </div>
                                        <button
                                            type="button"
                                            onClick={handleValidateSettings}
                                            className="rounded-lg border border-[var(--color-cyan-main)]/15 bg-white px-3 py-2 text-xs font-black text-[var(--color-cyan-main)] transition-colors hover:bg-[var(--color-cyan-light)]/30"
                                        >
                                            {validationState === 'checking' ? '测试中...' : '测试连接'}
                                        </button>
                                    </div>

                                    <div className="space-y-3">
                                        <div className="group">
                                            <label className="block text-xs font-black text-[var(--color-cyan-dark)]/40 mb-2 ml-1">网关</label>
                                            <div className="relative">
                                                <input
                                                    type="text"
                                                    value={settings.base_url}
                                                    onChange={(e) => setSettings({ ...settings, base_url: e.target.value })}
                                                    className="w-full bg-[var(--color-cyan-light)]/30 text-[var(--color-cyan-dark)] font-bold p-3 rounded-lg border border-transparent focus:border-[var(--color-cyan-main)]/30 focus:bg-white outline-none transition-all pr-12"
                                                    placeholder="https://..."
                                                />
                                                <RefreshCcw className="absolute right-4 top-1/2 -translate-y-1/2 text-[var(--color-cyan-dark)]/20 group-hover:text-[var(--color-cyan-main)]/40 transition-colors" size={16} />
                                            </div>
                                        </div>

                                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                            <div>
                                                <label className="block text-xs font-black text-[var(--color-cyan-dark)]/40 mb-2 ml-1">默认模型</label>
                                                {settings.base_url && AI_PRESETS.find(p => p.url === settings.base_url) ? (
                                                    <select
                                                        value={settings.model_name}
                                                        onChange={(e) => setSettings(s => ({ ...s, model_name: e.target.value }))}
                                                        className="w-full bg-white text-[var(--color-cyan-dark)] font-black p-3 rounded-lg border border-[var(--color-cyan-main)]/10 focus:border-[var(--color-cyan-main)] outline-none transition-all appearance-none cursor-pointer"
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
                                                        className="w-full bg-[var(--color-cyan-light)]/30 text-[var(--color-cyan-dark)] font-bold p-3 rounded-lg border border-transparent focus:border-[var(--color-cyan-main)]/30 focus:bg-white outline-none transition-all"
                                                        placeholder="例如: gpt-4"
                                                    />
                                                )}
                                            </div>
                                            <div>
                                                <label className="block text-xs font-black text-[var(--color-cyan-dark)]/40 mb-2 ml-1">API</label>
                                                <input
                                                    type="password"
                                                    value={settings.api_key}
                                                    onChange={(e) => setSettings({ ...settings, api_key: e.target.value })}
                                                    placeholder="已加密保护"
                                                    className="w-full bg-[var(--color-cyan-light)]/30 text-[var(--color-cyan-dark)] font-bold p-3 rounded-lg border border-transparent focus:border-[var(--color-cyan-main)]/30 focus:bg-white outline-none transition-all"
                                                />
                                            </div>
                                        </div>
                                    </div>

                                    <div className={`rounded-lg px-3 py-2 text-xs font-bold ${
                                        validationState === 'success'
                                            ? 'bg-emerald-50 text-emerald-600 border border-emerald-100'
                                            : validationState === 'error'
                                                ? 'bg-red-50 text-red-600 border border-red-100'
                                                : 'bg-[var(--color-cyan-light)]/25 text-[var(--color-cyan-dark)]/65 border border-[var(--color-cyan-main)]/8'
                                    }`}>
                                        当前状态：{validationMessage}
                                    </div>
                                </div>

                                {/* Advanced Tuning Card */}
                                <div className="bg-white/60 backdrop-blur-sm p-4 rounded-xl border border-[var(--color-cyan-main)]/10 shadow-sm space-y-4">
                                    <div className="flex items-center space-x-3 mb-2">
                                        <Thermometer size={18} className="text-[var(--color-yellow-main)]" />
                                        <span className="text-sm font-black text-[var(--color-cyan-dark)]">高级参数</span>
                                    </div>

                                    <div className="space-y-6">
                                        <div>
                                            <div className="flex justify-between items-center mb-4">
                                                <div className="flex flex-col">
                                                    <span className="text-[11px] font-black text-[var(--color-cyan-dark)]">性能模式</span>
                                                </div>
                                            </div>
                                            <select
                                                value={settings.latency_mode}
                                                onChange={(e) => setSettings({ ...settings, latency_mode: e.target.value as any })}
                                                className="w-full bg-white text-[var(--color-cyan-dark)] font-black p-3 rounded-lg border border-[var(--color-cyan-main)]/10 focus:border-[var(--color-cyan-main)] outline-none transition-all appearance-none cursor-pointer"
                                            >
                                                <option value="balanced">均衡模式（推荐）</option>
                                                <option value="fast">极速模式（优先速度）</option>
                                                <option value="story">剧情优先（优先质量）</option>
                                            </select>
                                        </div>

                                        <div className="rounded-lg border border-[var(--color-cyan-main)]/10 bg-white px-3 py-3">
                                            <div className="flex items-center justify-between gap-3">
                                                <div className="flex flex-col">
                                                    <span className="text-[11px] font-black text-[var(--color-cyan-dark)]">回合调试面板</span>
                                                    <span className="text-xs font-bold text-[var(--color-cyan-dark)]/40">
                                                        开启后返回每回合timings与prompt规模
                                                    </span>
                                                </div>
                                                <button
                                                    type="button"
                                                    onClick={() => setSettings({ ...settings, turn_debug: !settings.turn_debug })}
                                                    className={`relative inline-flex h-7 w-14 items-center rounded-full transition-colors ${
                                                        settings.turn_debug ? 'bg-[var(--color-cyan-main)]' : 'bg-slate-300'
                                                    }`}
                                                >
                                                    <span
                                                        className={`inline-block h-5 w-5 transform rounded-full bg-white transition-transform ${
                                                            settings.turn_debug ? 'translate-x-8' : 'translate-x-1'
                                                        }`}
                                                    />
                                                </button>
                                            </div>
                                        </div>

                                        <div>
                                            <div className="flex justify-between items-center mb-4">
                                                <div className="flex flex-col">
                                                    <span className="text-[11px] font-black text-[var(--color-cyan-dark)]">对话架构</span>
                                                </div>
                                            </div>
                                            <select
                                                value={settings.dialogue_mode}
                                                onChange={(e) => setSettings({ ...settings, dialogue_mode: e.target.value as any })}
                                                className="w-full bg-white text-[var(--color-cyan-dark)] font-black p-3 rounded-lg border border-[var(--color-cyan-main)]/10 focus:border-[var(--color-cyan-main)] outline-none transition-all appearance-none cursor-pointer"
                                            >
                                                <option value="single_dm">单一DM统筹（稳定）</option>
                                                <option value="hybrid">Hybrid 预生成分支（实验）</option>
                                                <option value="tree_only">Tree Only 分支树（实验）</option>
                                                <option value="npc_dm">NPC-DM 多Agent（慢，偏实验）</option>
                                            </select>
                                        </div>

                                        <div>
                                            <div className="flex justify-between items-center mb-4">
                                                <div className="flex flex-col">
                                                    <span className="text-[11px] font-black text-[var(--color-cyan-dark)]">输出稳定性</span>
                                                </div>
                                            </div>
                                            <select
                                                value={settings.stability_mode}
                                                onChange={(e) => setSettings({ ...settings, stability_mode: e.target.value as any })}
                                                className="w-full bg-white text-[var(--color-cyan-dark)] font-black p-3 rounded-lg border border-[var(--color-cyan-main)]/10 focus:border-[var(--color-cyan-main)] outline-none transition-all appearance-none cursor-pointer"
                                            >
                                                <option value="stable">Stable（推荐）</option>
                                                <option value="balanced">Balanced</option>
                                            </select>
                                        </div>

                                        <div>
                                            <div className="flex justify-between items-center mb-4">
                                                <div className="flex flex-col">
                                                    <span className="text-[11px] font-black text-[var(--color-cyan-dark)]">Temperature</span>
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
                                                    <span className="text-[11px] font-black text-[var(--color-cyan-dark)]">单次最大Token</span>
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

                    </div>
                ) : activeTab === 'preferences' ? (
                    <div className="animate-in fade-in slide-in-from-bottom-4 duration-500 space-y-4">
                        <div className="bg-white/78 p-4 rounded-xl border border-[var(--color-cyan-main)]/10 shadow-sm">
                            <div className="flex items-center space-x-3 mb-4">
                                <div className="p-2 bg-[var(--color-cyan-light)] rounded-xl text-[var(--color-cyan-main)]">
                                    <Type size={20} />
                                </div>
                                <h3 className="text-lg font-black text-[var(--color-cyan-dark)]">文本</h3>
                            </div>

                            <div className="space-y-5">
                                <div>
                                    <div className="flex justify-between items-center mb-2">
                                        <label className="text-sm font-black text-[var(--color-cyan-dark)]/70">打字机速度</label>
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

                                <div>
                                    <div className="flex justify-between items-center mb-2">
                                        <label className="text-sm font-black text-[var(--color-cyan-dark)]/70">界面透明度</label>
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

                        <div className="bg-red-50/50 p-4 rounded-xl border border-red-100 shadow-sm">
                            <div className="flex items-center space-x-3 mb-4 text-red-600">
                                <Trash2 size={20} />
                                <h3 className="text-lg font-black">危险区域</h3>
                            </div>
                            <p className="text-sm font-bold text-red-600/60 mb-6">以下操作会影响后端数据存储，请谨慎执行。</p>

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
                                className="w-full py-3 bg-white border border-red-200 hover:bg-red-500 hover:border-red-500 hover:text-white text-red-500 font-black rounded-xl transition-all shadow-sm flex items-center justify-center space-x-2 text-sm"
                            >
                                <RefreshCcw size={18} />
                                <span>重置记忆与进度</span>
                            </button>
                        </div>
                    </div>
                ) : (
                    <div className="animate-in fade-in slide-in-from-bottom-4 duration-500 flex flex-col h-full">
                        {/* Memory Control Hub */}
                        <div className="flex items-center justify-between mb-5">
                            <div className="flex items-center space-x-3">
                                <div className="bg-white/60 p-3 rounded-lg border border-[var(--color-cyan-main)]/10">
                                    <label className="block text-xs font-black text-[var(--color-cyan-dark)]/40 mb-2">角色筛选</label>
                                    <select 
                                        value={memoryFilter.char}
                                        onChange={(e) => setMemoryFilter({...memoryFilter, char: e.target.value})}
                                        className="bg-transparent text-xs font-bold text-[var(--color-cyan-dark)] outline-none min-w-[120px]"
                                    >
                                        <option value="">全部成员</option>
                                        {active_roommates.map(name => <option key={name} value={name}>{name}</option>)}
                                    </select>
                                </div>
                                <div className="bg-white/60 p-3 rounded-lg border border-[var(--color-cyan-main)]/10">
                                    <label className="block text-xs font-black text-[var(--color-cyan-dark)]/40 mb-2">记忆类型</label>
                                    <select 
                                        value={memoryFilter.type}
                                        onChange={(e) => setMemoryFilter({...memoryFilter, type: e.target.value})}
                                        className="bg-transparent text-xs font-bold text-[var(--color-cyan-dark)] outline-none min-w-[120px]"
                                    >
                                        <option value="">高价值记忆</option>
                                        <option value="event_reflection">事件总结</option>
                                        <option value="narrative_milestone">关系里程碑</option>
                                        <option value="weekly_summary">阶段总结</option>
                                        <option value="lore">固定设定</option>
                                        <option value="short_term_dialogue">短期对话缓存</option>
                                    </select>
                                </div>
                            </div>
                            <div className="text-right">
                                <p className="text-xs font-black text-[var(--color-cyan-dark)]">当前检索范围</p>
                                <p className="text-[14px] font-black text-[var(--color-cyan-main)]">{currentSaveId || '新游戏'}</p>
                            </div>
                        </div>

                        {/* Memory Flow Area */}
                        <div className="flex-1 space-y-3 overflow-y-auto custom-scrollbar pr-1 pb-8">
                            {memories.length === 0 ? (
                                    <div className="h-56 flex flex-col items-center justify-center border-2 border-dashed border-[var(--color-cyan-main)]/10 rounded-xl text-[var(--color-cyan-dark)]/20">
                                        <Database size={48} className="mb-4 opacity-20" />
                                        <span className="text-sm font-black">暂时没有符合条件的记忆</span>
                                    <span className="text-xs font-bold mt-1 opacity-50">推进到事件结束后，这里会出现对应的事件总结。</span>
                                </div>
                            ) : (
                                memories.map((m) => (
                                    <div key={m.id} className="group bg-white/60 hover:bg-white p-4 rounded-lg border border-[var(--color-cyan-main)]/10 hover:border-[var(--color-cyan-main)]/30 transition-all shadow-sm hover:shadow-md relative overflow-hidden">
                                        <div className="flex justify-between items-start mb-3">
                                            <div className="flex items-center space-x-3">
                                                <span className={`px-2 py-0.5 rounded-md text-[10px] font-black ${
                                                    m.metadata?.type === 'lore' ? 'bg-purple-100 text-purple-600' :
                                                    m.metadata?.type === 'event_reflection' ? 'bg-amber-100 text-amber-700' :
                                                    m.metadata?.type === 'narrative_milestone' ? 'bg-emerald-100 text-emerald-700' :
                                                    m.metadata?.type === 'weekly_summary' ? 'bg-cyan-100 text-cyan-700' :
                                                    m.metadata?.type === 'short_term_dialogue' ? 'bg-slate-100 text-slate-600' :
                                                    'bg-green-100 text-green-600'
                                                }`}>
                                                    {MEMORY_TYPE_LABELS[String(m.metadata?.type || '')] || m.metadata?.type || 'unknown'}
                                                </span>
                                                <span className="text-[10px] font-bold text-[var(--color-cyan-dark)]/30 tabular-nums">
                                                    {m.metadata?.timestamp ? new Date(m.metadata.timestamp).toLocaleString() : '无时间'}
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
