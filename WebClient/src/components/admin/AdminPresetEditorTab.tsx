import { useEffect, useMemo, useState } from 'react';
import { FileEdit, RefreshCw, Save, Braces, Search } from 'lucide-react';
import { gameApi } from '../../api/gameApi';

type TargetType = 'default' | 'preset';
type FileType = 'md' | 'csv';

const splitLabel = (path: string) => path.split('/').pop() || path;

export const AdminPresetEditorTab = () => {
    const [target, setTarget] = useState<TargetType>('default');
    const [mods, setMods] = useState<any[]>([]);
    const [modId, setModId] = useState('');
    const [files, setFiles] = useState<{ md: string[]; csv: string[] }>({ md: [], csv: [] });
    const [selectedFile, setSelectedFile] = useState<{ type: FileType; name: string } | null>(null);
    const [content, setContent] = useState('');
    const [query, setQuery] = useState('');
    const [loading, setLoading] = useState(false);
    const [reading, setReading] = useState(false);
    const [saving, setSaving] = useState(false);
    const [dirty, setDirty] = useState(false);
    const [message, setMessage] = useState('');

    const showMessage = (text: string) => {
        setMessage(text);
        window.setTimeout(() => setMessage(''), 1800);
    };

    const loadMods = async () => {
        try {
            const res = await gameApi.getAdminPresetMods();
            const rows = Array.isArray(res?.data) ? res.data : [];
            setMods(rows);
            if (!modId && rows.length > 0) {
                setModId(rows[0].id);
            }
        } catch {
            setMods([]);
        }
    };

    const loadFiles = async () => {
        if (target === 'preset' && !modId) return;
        setLoading(true);
        try {
            const res = await gameApi.getAdminPresetFiles(target, modId);
            const nextFiles = {
                md: Array.isArray(res?.md) ? res.md : [],
                csv: Array.isArray(res?.csv) ? res.csv : [],
            };
            setFiles(nextFiles);
            const first = nextFiles.md[0]
                ? { type: 'md' as const, name: nextFiles.md[0] }
                : nextFiles.csv[0]
                  ? { type: 'csv' as const, name: nextFiles.csv[0] }
                  : null;
            setSelectedFile(first);
            setDirty(false);
        } finally {
            setLoading(false);
        }
    };

    const loadContent = async () => {
        if (!selectedFile) {
            setContent('');
            return;
        }
        setReading(true);
        try {
            const res = await gameApi.getAdminPresetFile({
                target,
                modId,
                type: selectedFile.type,
                name: selectedFile.name,
            });
            setContent(String(res?.content || ''));
            setDirty(false);
        } catch (e: any) {
            showMessage(e?.response?.data?.detail || '读取失败');
            setContent('');
        } finally {
            setReading(false);
        }
    };

    useEffect(() => {
        loadMods();
    }, []);

    useEffect(() => {
        loadFiles();
    }, [target, modId]);

    useEffect(() => {
        loadContent();
    }, [selectedFile, target, modId]);

    const allFiles = useMemo(() => {
        const rows = [
            ...files.md.map((name) => ({ type: 'md' as const, name })),
            ...files.csv.map((name) => ({ type: 'csv' as const, name })),
        ];
        const q = query.trim().toLowerCase();
        if (!q) return rows;
        return rows.filter((f) => f.name.toLowerCase().includes(q));
    }, [files, query]);

    const groupedFiles = useMemo(() => {
        const groups: Record<string, Array<{ type: FileType; name: string }>> = {};
        allFiles.forEach((f) => {
            const key = f.name.includes('/') ? f.name.split('/')[0] : (f.type === 'md' ? 'prompts' : 'events');
            if (!groups[key]) groups[key] = [];
            groups[key].push(f);
        });
        return Object.entries(groups).sort((a, b) => a[0].localeCompare(b[0]));
    }, [allFiles]);

    const saveCurrent = async () => {
        if (!selectedFile) return;
        setSaving(true);
        try {
            await gameApi.saveAdminPresetFile({
                target,
                modId,
                type: selectedFile.type,
                name: selectedFile.name,
                content,
            });
            setDirty(false);
            showMessage('保存成功');
        } catch (e: any) {
            showMessage(e?.response?.data?.detail || '保存失败');
        } finally {
            setSaving(false);
        }
    };

    const formatJsonIfPossible = () => {
        try {
            const parsed = JSON.parse(content);
            setContent(JSON.stringify(parsed, null, 2));
            setDirty(true);
            showMessage('JSON 已格式化');
        } catch {
            showMessage('当前内容不是合法 JSON');
        }
    };

    const selectedModName = mods.find((m) => m.id === modId)?.name || modId;

    return (
        <div className="h-full min-h-0 flex flex-col">
            <div className="shrink-0 px-4 py-3 border-b border-[var(--color-cyan-main)]/10 bg-white/60">
                <h3 className="text-[10px] font-black text-[var(--color-cyan-main)] uppercase tracking-[0.2em] flex items-center">
                    <FileEdit size={14} className="mr-2" /> 后台专用模板编辑器
                </h3>
                <div className="mt-2 grid grid-cols-1 md:grid-cols-3 gap-3">
                    <div>
                        <div className="text-[10px] font-black text-[var(--color-cyan-main)] uppercase tracking-widest mb-1">编辑目标</div>
                        <select
                            value={target}
                            onChange={(e) => setTarget(e.target.value as TargetType)}
                            className="w-full rounded-xl border border-[var(--color-cyan-main)]/20 bg-white px-3 py-2 text-sm font-bold text-[var(--color-cyan-dark)] outline-none"
                        >
                            <option value="default">默认模板</option>
                            <option value="preset">预设模组</option>
                        </select>
                    </div>
                    <div>
                        <div className="text-[10px] font-black text-[var(--color-cyan-main)] uppercase tracking-widest mb-1">预设模组</div>
                        <select
                            value={modId}
                            disabled={target !== 'preset'}
                            onChange={(e) => setModId(e.target.value)}
                            className="w-full rounded-xl border border-[var(--color-cyan-main)]/20 bg-white px-3 py-2 text-sm font-bold text-[var(--color-cyan-dark)] outline-none disabled:opacity-40"
                        >
                            {mods.map((m) => (
                                <option key={m.id} value={m.id}>
                                    {m.name || m.id}
                                </option>
                            ))}
                        </select>
                    </div>
                    <div className="flex items-end justify-end gap-2">
                        <button
                            onClick={formatJsonIfPossible}
                            className="px-3 py-2 rounded-xl border border-[var(--color-cyan-main)]/20 bg-white text-[var(--color-cyan-main)] text-xs font-black hover:bg-[var(--color-cyan-light)] transition-all"
                        >
                            <Braces size={14} className="inline mr-1" />
                            格式化 JSON
                        </button>
                        <button
                            onClick={saveCurrent}
                            disabled={!selectedFile || saving || !dirty}
                            className="px-3 py-2 rounded-xl bg-[var(--color-cyan-main)] text-white text-xs font-black hover:opacity-90 transition-all disabled:opacity-50"
                        >
                            <Save size={14} className="inline mr-1" />
                            {saving ? '保存中...' : '保存'}
                        </button>
                    </div>
                </div>
                <div className="mt-2 text-[11px] font-bold text-slate-500">
                    {target === 'default' ? '当前：默认模板' : `当前：预设模组 / ${selectedModName || '-'}`} {dirty ? ' · 有未保存更改' : ''}
                </div>
            </div>

            <div className="flex-1 min-h-0 grid grid-cols-1 md:grid-cols-[280px_minmax(0,1fr)]">
                <aside className="border-r border-[var(--color-cyan-main)]/10 bg-white/55 min-h-0 overflow-auto custom-scrollbar p-3">
                    <div className="relative mb-3">
                        <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
                        <input
                            value={query}
                            onChange={(e) => setQuery(e.target.value)}
                            placeholder="搜索文件..."
                            className="w-full rounded-xl border border-[var(--color-cyan-main)]/15 bg-white pl-9 pr-3 py-2 text-sm font-bold text-[var(--color-cyan-dark)] outline-none"
                        />
                    </div>
                    <button
                        onClick={loadFiles}
                        disabled={loading}
                        className="w-full mb-3 px-3 py-2 rounded-xl border border-[var(--color-cyan-main)]/20 bg-white text-[var(--color-cyan-main)] text-xs font-black hover:bg-[var(--color-cyan-light)] transition-all disabled:opacity-50"
                    >
                        <RefreshCw size={14} className={`inline mr-1 ${loading ? 'animate-spin' : ''}`} />
                        刷新文件
                    </button>
                    <div className="space-y-3">
                        {groupedFiles.map(([group, rows]) => (
                            <div key={group}>
                                <div className="text-[10px] font-black uppercase tracking-widest text-[var(--color-cyan-main)] mb-1.5">
                                    {group}
                                </div>
                                <div className="space-y-1">
                                    {rows.map((f) => {
                                        const active = selectedFile?.name === f.name && selectedFile?.type === f.type;
                                        return (
                                            <button
                                                key={`${f.type}:${f.name}`}
                                                onClick={() => setSelectedFile({ type: f.type, name: f.name })}
                                                className={`w-full text-left rounded-lg px-2.5 py-2 border transition-all ${
                                                    active
                                                        ? 'border-[var(--color-cyan-main)] bg-[var(--color-cyan-main)]/10'
                                                        : 'border-transparent hover:border-[var(--color-cyan-main)]/20 hover:bg-white'
                                                }`}
                                            >
                                                <div className="text-xs font-black text-[var(--color-cyan-dark)] break-all">{splitLabel(f.name)}</div>
                                                <div className="text-[10px] font-bold text-slate-400 break-all">{f.name}</div>
                                            </button>
                                        );
                                    })}
                                </div>
                            </div>
                        ))}
                    </div>
                </aside>

                <section className="min-h-0 flex flex-col bg-white/30">
                    <div className="shrink-0 px-4 py-2.5 border-b border-[var(--color-cyan-main)]/10 bg-white/70 text-xs font-black text-[var(--color-cyan-dark)]">
                        {selectedFile ? `${selectedFile.type.toUpperCase()} / ${selectedFile.name}` : '请选择左侧文件'}
                    </div>
                    <div className="flex-1 min-h-0 p-3">
                        {reading ? (
                            <div className="h-full rounded-2xl border border-[var(--color-cyan-main)]/10 bg-white flex items-center justify-center text-sm font-black text-slate-400">
                                读取中...
                            </div>
                        ) : (
                            <textarea
                                value={content}
                                onChange={(e) => {
                                    setContent(e.target.value);
                                    setDirty(true);
                                }}
                                className="w-full h-full rounded-2xl border border-[var(--color-cyan-main)]/15 bg-white p-4 font-mono text-[13px] leading-6 text-slate-700 outline-none resize-none"
                            />
                        )}
                    </div>
                    <div className="shrink-0 px-4 py-2 border-t border-[var(--color-cyan-main)]/10 bg-white/70 text-[11px] font-bold text-slate-500">
                        {message || `文件数：${files.md.length + files.csv.length}（md ${files.md.length} / csv ${files.csv.length}）`}
                    </div>
                </section>
            </div>
        </div>
    );
};

