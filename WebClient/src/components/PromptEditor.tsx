import { useState, useEffect, useMemo } from 'react';
import { Globe, Users, ScrollText, Terminal, Sparkles, GitGraph, Zap, Image } from 'lucide-react';
import { gameApi } from '../api/gameApi';

import { EditorHeader } from './editor/EditorHeader';
import { EditorSidebar } from './editor/EditorSidebar';
import { CharacterEditor } from './editor/CharacterEditor';
import { EventEditor } from './editor/EventEditor';
import { EventSkeletonEditor } from './editor/EventSkeletonEditor';
import { SceneConfigEditor } from './editor/SceneConfigEditor';
import { CodeWorkspace } from './editor/CodeWorkspace';
import { TimelineView } from './editor/TimelineView';
import { TopicExplorer } from './editor/TopicExplorer';
import { EditorModals } from './editor/EditorModals';
import { EditorGuide } from './editor/EditorGuide';
import { CharacterDetailModal } from './editor/CharacterDetailModal';
import { RelationshipMatrix } from './editor/RelationshipMatrix';
import { AUTO_FIX_PRESETS, AutoFixPresetId } from '../config/eventSkeletonAutoFixPresets';

import { Category } from './editor/types';

interface PromptEditorProps {
    adminPresetMode?: boolean;
    adminPresetTarget?: 'default' | 'preset';
    adminPresetModId?: string;
}

export const PromptEditor = ({
    adminPresetMode = false,
    adminPresetTarget = 'default',
    adminPresetModId = '',
}: PromptEditorProps) => {
    const [eventWorkbench, setEventWorkbench] = useState<'story' | 'skeleton'>('story');
    const [activeCategory, setActiveCategory] = useState<Category>('char');
    const [files, setFiles] = useState<{ md: string[], csv: string[] }>({ md: [], csv: [] });
    const [selectedFile, setSelectedFile] = useState<{ type: 'md' | 'csv', name: string } | null>(null);
    const [fileContent, setFileContent] = useState('');
    const [editMode, setEditMode] = useState<'visual' | 'code'>('visual');
    const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
    const [stableRoster, setStableRoster] = useState<any>(null);
    const [showExplorer, setShowExplorer] = useState(true);
    const [eventFilter, setEventFilter] = useState<{ chapter?: string, type?: string } | undefined>(undefined);
    const [userState, setUserState] = useState<any>(null);
    const [libraryMods, setLibraryMods] = useState<any[]>([]);
    const [workshopMods, setWorkshopMods] = useState<any[]>([]);
    const [accountInfo, setAccountInfo] = useState<any>(null);
    const [skeletonValidation, setSkeletonValidation] = useState<any>(null);
    const [isValidatingSkeleton, setIsValidatingSkeleton] = useState(false);
    const [isPromotingSkeleton, setIsPromotingSkeleton] = useState(false);
    const [skeletonAutoFixConfig, setSkeletonAutoFixConfig] = useState({
        fixInvalidType: true,
        fixInvalidNumbers: true,
        fixInvalidTriggers: true,
        normalizeKeyOptions: true,
        fillKeyOptions: true,
        resetReviewed: true,
    });
    const [skeletonAutoFixPreset, setSkeletonAutoFixPreset] = useState<AutoFixPresetId>('balanced');
    const [skeletonRules, setSkeletonRules] = useState<any>(null);
    const [modFeatures, setModFeatures] = useState<any>({ phone_system_enabled: true });
    const [isSavingFeatures, setIsSavingFeatures] = useState(false);

    const [message, setMessage] = useState('');
    const [isLoading, setIsLoading] = useState(false);
    const [isSaving, setIsSaving] = useState(false);
    const [showPublishModal, setShowPublishModal] = useState(false);
    const [showGuide, setShowGuide] = useState(false);
    const [publishMetadata, setPublishMetadata] = useState({
        name: '我的自定义模组',
        author: '佚名',
        description: '包含了我修改过的世界观和角色设定。'
    });

    const [deleteConfirm, setDeleteConfirm] = useState<{
        type: 'char' | 'csv-row',
        id: string,
        name: string,
        index?: number
    } | null>(null);

    const [newItemModal, setNewItemModal] = useState<{
        type: 'char' | 'event' | 'skill',
        name: string,
        archetype?: string,
        description: string
    } | null>(null);

    const [editingCharDetail, setEditingCharDetail] = useState<{
        id: string,
        char: any,
        content: string
    } | null>(null);

    const readFileContent = async (type: 'md' | 'csv', name: string) => {
        if (adminPresetMode) {
            return gameApi.getAdminPresetFile({
                target: adminPresetTarget,
                modId: adminPresetModId,
                type,
                name,
            });
        }
        return gameApi.getAdminFile(type, name);
    };

    const saveFileContent = async (type: 'md' | 'csv', name: string, content: string) => {
        if (adminPresetMode) {
            return gameApi.saveAdminPresetFile({
                target: adminPresetTarget,
                modId: adminPresetModId,
                type,
                name,
                content,
            });
        }
        return gameApi.saveAdminFile(type, name, content);
    };

    const fetchFiles = async () => {
        try {
            const [filesRes, stateRes, libraryRes, workshopRes, accountRes] = adminPresetMode
                ? await Promise.all([
                    gameApi.getAdminPresetFiles(adminPresetTarget, adminPresetModId),
                    Promise.resolve({ data: null }),
                    Promise.resolve({ data: [] }),
                    Promise.resolve({ data: [] }),
                    Promise.resolve({ data: null }),
                ])
                : await Promise.all([
                    gameApi.getAdminFiles(),
                    gameApi.getUserState(),
                    gameApi.getLibraryList(),
                    gameApi.getWorkshopList(),
                    gameApi.getAccountMe()
                ]);
            if (filesRes.status === 'success') {
                setFiles({ md: filesRes.md || [], csv: filesRes.csv || [] });
                setUserState(stateRes?.data || null);
                setLibraryMods(libraryRes?.data || []);
                setWorkshopMods(workshopRes?.data || []);
                setAccountInfo(accountRes?.data || null);
                if (activeCategory === 'char' && !selectedFile) {
                    const roster = filesRes.md.find((f: string) => f.endsWith('roster.json'));
                    if (roster) {
                        setSelectedFile({ type: 'md', name: roster });
                        setShowExplorer(false);
                    }
                }
                await loadModFeatures(filesRes.md || []);
            }
        } catch (e) {
            setMessage('无法获取文件列表');
        }
    };

    const loadModFeatures = async (mdFiles?: string[]) => {
        const mdList = Array.isArray(mdFiles) ? mdFiles : files.md;
        const target = mdList.find((f: string) => f === 'system/mod_features.json') || 'system/mod_features.json';
        try {
            const res = await readFileContent('md', target);
            if (res?.status === 'success' && res.content) {
                const parsed = JSON.parse(res.content);
                if (parsed && typeof parsed === 'object') {
                    setModFeatures({
                        phone_system_enabled: parsed.phone_system_enabled !== false,
                        ...parsed,
                    });
                    return;
                }
            }
        } catch {
            // fall through to default
        }
        setModFeatures({ phone_system_enabled: true });
    };

    const handleTogglePhoneSystem = async (enabled: boolean) => {
        if (!canEditCurrentMod) {
            setMessage('默认模组为只读，请先另存到本地模组库后再编辑');
            setTimeout(() => setMessage(''), 3000);
            return;
        }
        const next = {
            ...(modFeatures || {}),
            phone_system_enabled: enabled,
            wechat_system_enabled: enabled,
        };
        setModFeatures(next);
        setIsSavingFeatures(true);
        try {
            await saveFileContent('md', 'system/mod_features.json', JSON.stringify(next, null, 2));
            setMessage('手机系统开关已更新');
        } catch {
            setMessage('手机系统开关保存失败');
        } finally {
            setIsSavingFeatures(false);
            setTimeout(() => setMessage(''), 2500);
        }
    };

    useEffect(() => {
        console.log('[PromptEditor] Active Category:', activeCategory);
        if (files.md.length === 0 && files.csv.length === 0) {
            console.log('[PromptEditor] Waiting for files...');
            return;
        }

        if (activeCategory === 'char') {
            const roster = files.md.find(f => f.includes('roster.json'));
            if (roster) {
                setSelectedFile({ type: 'md', name: roster });
                setShowExplorer(false);
                setEditMode('visual');
            }
        } else if (activeCategory === 'event') {
            const skeletonDraft = files.csv.find(f => f.includes('event_skeletons.generated.json'))
                || files.csv.find(f => f.includes('event_skeletons.json'));
            const timeline = files.csv.find(f => f.includes('timeline.json'));
            const firstStoryCsv = files.csv.find(
                f => f.endsWith('.csv') && !f.includes('event_skeletons') && !f.includes('timeline.json')
            );
            console.log('[PromptEditor] Event category, workbench/files:', eventWorkbench, skeletonDraft, timeline, firstStoryCsv);
            setShowExplorer(false);
            setEditMode('visual');
            if (eventWorkbench === 'skeleton') {
                if (skeletonDraft) {
                    setSelectedFile({ type: 'csv', name: skeletonDraft });
                } else if (timeline) {
                    setSelectedFile({ type: 'csv', name: timeline });
                }
            } else {
                if (timeline) {
                    setSelectedFile({ type: 'csv', name: timeline });
                } else if (firstStoryCsv) {
                    setSelectedFile({ type: 'csv', name: firstStoryCsv });
                } else if (skeletonDraft) {
                    setSelectedFile({ type: 'csv', name: skeletonDraft });
                }
            }
        } else if (activeCategory === 'scene') {
            const sceneFile = files.md.find((f) => f === 'world/scenes.json') || files.md.find((f) => f.includes('world/scenes.json'));
            if (sceneFile) {
                setSelectedFile({ type: 'md', name: sceneFile });
                setShowExplorer(false);
                setEditMode('visual');
            }
        } else if (activeCategory === 'world' || activeCategory === 'skills') {
            setShowExplorer(false);
            setEditMode('visual');
            setSelectedFile(null); 
        } else if (activeCategory === 'relation') {
            const rel = files.md.find(f => f.includes('relationship.csv'));
            console.log('[PromptEditor] Relation category, found rel:', rel);
            if (rel) {
                setSelectedFile({ type: 'md', name: rel });
                setShowExplorer(false);
                setEditMode('visual');
            }
        } else {
            setShowExplorer(true);
        }
    }, [activeCategory, files, eventWorkbench]);

    useEffect(() => {
        fetchFiles();
    }, [adminPresetMode, adminPresetTarget, adminPresetModId]);

    useEffect(() => {
        if (files.md.length > 0 && !stableRoster) {
                const rosterFile = files.md.find(f => f.includes('roster.json'));
                if (rosterFile) {
                    console.log('[PromptEditor] Fetching roster from:', rosterFile);
                readFileContent('md', rosterFile).then((res) => {
                    try {
                        if (res?.status === 'success') {
                            setStableRoster(JSON.parse(res.content || '{}'));
                        }
                    } catch (e) {
                        console.error("Failed to parse roster:", e);
                    }
                });
            }
        }
    }, [files, stableRoster]);

    useEffect(() => {
        if (!selectedFile) return;
        const loadContent = async () => {
            setIsLoading(true);
            setFileContent('Loading...');
            try {
                const res = await readFileContent(selectedFile.type, selectedFile.name);
                if (res.status === 'success') {
                    setFileContent(res.content || '');
                }
            } catch (e) {
                setFileContent('');
                setMessage(`读取失败: ${selectedFile.name}`);
            } finally {
                setIsLoading(false);
            }
        };
        loadContent();
    }, [selectedFile]);

    useEffect(() => {
        setSkeletonValidation(null);
    }, [selectedFile?.name, activeCategory]);

    useEffect(() => {
        const loadRules = async () => {
            if (activeCategory !== 'event') return;
            if (!selectedFile?.name?.includes('event_skeletons')) return;
            try {
                const res = await gameApi.getEventSkeletonRules();
                setSkeletonRules(res?.data?.rules || null);
            } catch {
                setSkeletonRules(null);
            }
        };
        loadRules();
    }, [activeCategory, selectedFile?.name]);

    const handleSave = async (contentToSave = fileContent) => {
        if (!selectedFile) return;
        if (String(userState?.editor_source || 'default') !== 'library') {
            setMessage('默认模组为只读，请先另存到本地模组库后再编辑');
            setTimeout(() => setMessage(''), 3000);
            return;
        }
        setIsSaving(true);
        try {
            await saveFileContent(selectedFile.type, selectedFile.name, contentToSave);
            setMessage('同步成功');
            setFileContent(contentToSave);
            if (selectedFile.name.endsWith('roster.json')) {
                try { setStableRoster(JSON.parse(contentToSave)); } catch(e) {}
            }
        } catch (e) {
            setMessage('保存失败!');
        } finally {
            setIsSaving(false);
            setTimeout(() => setMessage(''), 3000);
        }
    };

    const categories = [
        { id: 'world', name: '世界设定', icon: Globe },
        { id: 'scene', name: '场景配置', icon: Image },
        { id: 'char', name: '角色管理', icon: Users },
        { id: 'relation', name: '人物关系', icon: GitGraph }, 
        { id: 'event', name: '剧情编排', icon: ScrollText },
        { id: 'skills', name: '系统逻辑', icon: Zap },
        { id: 'all', name: '底层文件', icon: Terminal },
    ];

    const parsedRoster = useMemo(() => {
        if (selectedFile?.name.endsWith('roster.json')) {
            try { return JSON.parse(fileContent); } catch (e) { return null; }
        }
        return stableRoster;
    }, [fileContent, selectedFile, stableRoster]);

    const parsedScenes = useMemo(() => {
        if (selectedFile?.name === 'world/scenes.json') {
            try {
                const parsed = JSON.parse(fileContent || '{}');
                return {
                    default_image: parsed?.default_image || '/assets/backgrounds/宿舍.jpg',
                    scenes: Array.isArray(parsed?.scenes) ? parsed.scenes : [],
                };
            } catch {
                return { default_image: '/assets/backgrounds/宿舍.jpg', scenes: [] };
            }
        }
        return null;
    }, [fileContent, selectedFile]);

    const updateRosterItem = (id: string, field: string, value: any) => {
        if (!parsedRoster) return;
        let newRoster = { ...parsedRoster, [id]: { ...parsedRoster[id], [field]: value } };
        
        // Ensure only one protagonist
        if (field === 'is_player' && value === true) {
            Object.keys(newRoster).forEach(key => {
                if (key !== id) {
                    newRoster[key] = { ...newRoster[key], is_player: false };
                }
            });
        }
        
        handleSave(JSON.stringify(newRoster, null, 4));
    };

    const handleAvatarUpload = async (id: string, file: File) => {
        setIsLoading(true);
        try {
            const res = await gameApi.uploadPortrait(file);
            if (res.status === 'success') {
                updateRosterItem(id, 'avatar', res.url);
                setMessage('头像上传成功');
            } else {
                setMessage('上传失败: ' + (res.message || '未知错误'));
            }
        } catch (e) {
            setMessage('上传出错');
        } finally {
            setIsLoading(false);
        }
    };

    const addRosterItem = async (data: { name: string, archetype: string, description: string }) => {
        if (!parsedRoster) return;
        const id = `new_char_${Date.now()}`;
        const fileName = `characters/${id}.md`;
        setIsLoading(true);
        try {
            await saveFileContent('md', fileName, `# ${data.name}\n\n## 身份标签\n${data.archetype}\n\n## 背景设定\n${data.description}\n\n## 性格特征\n请输入性格特征...\n\n## 行为准则\n请输入行为准则...`);
            const newRoster = {
                ...parsedRoster,
                [id]: {
                    name: data.name,
                    avatar: "/assets/portraits/default.webp",
                    archetype: data.archetype,
                    tags: ["待补完"],
                    description: data.description.slice(0, 50) + "...",
                    file: fileName,
                    is_player: false
                }
            };
            await handleSave(JSON.stringify(newRoster, null, 4));
            fetchFiles();
            setNewItemModal(null);
        } catch (e) {
            setMessage('初始化角色文件失败');
        } finally {
            setIsLoading(false);
        }
    };

    const removeRosterItem = (id: string) => {
        if (!parsedRoster) return;
        const newRoster = { ...parsedRoster };
        delete newRoster[id];
        handleSave(JSON.stringify(newRoster, null, 4));
        setDeleteConfirm(null);
    };

    const parsedCsv = useMemo(() => {
        if (!selectedFile || !fileContent) return null;
        console.log('[PromptEditor] Parsing file:', selectedFile.name, 'type:', selectedFile.type);

        if (selectedFile.name.endsWith('.json')) {
            try {
                const data = JSON.parse(fileContent);
                return { headers: ['JSON'], rows: [{ 'Data': JSON.stringify(data) }] };
            } catch (e) { return null; }
        }

        if (selectedFile?.type === 'csv' || selectedFile?.name.endsWith('.csv')) {
            const lines = fileContent.split('\n').filter(l => l.trim());
            if (lines.length === 0) return { headers: [], rows: [] };
            // Normalize headers to avoid BOM/CRLF issues (e.g. "评价者")
            const headers = lines[0]
                .split(',')
                .map((h, idx) => {
                    const clean = h.replace(/\r/g, '').trim();
                    return idx === 0 ? clean.replace(/^\uFEFF/, '') : clean;
                });
            const rows = lines.slice(1).map(line => {
                // Robust CSV splitting that handles commas inside quotes
                const values = line.split(/,(?=(?:(?:[^"]*"){2})*[^"]*$)/);
                const row: Record<string, string> = {};
                headers.forEach((h, i) => {
                    let val = (values[i] || '').replace(/\r/g, '').trim();
                    // Remove surrounding quotes if present
                    if (val.startsWith('"') && val.endsWith('"')) {
                        val = val.substring(1, val.length - 1);
                    }
                    row[h] = val;
                });
                return row;
            });
            return { headers, rows };
        }
        return null;
    }, [fileContent, selectedFile]);

    const relationCsv = useMemo(() => {
        if (activeCategory !== 'relation' || !selectedFile?.name?.includes('relationship.csv')) {
            return parsedCsv;
        }
        if (!parsedCsv || !parsedRoster) return parsedCsv;

        const characterNames = Object.values(parsedRoster)
            .map((c: any) => (c?.name || '').trim())
            .filter((name: string) => !!name);

        const rowKey = (row: Record<string, string>) => `${row['评价者'] || ''}::${row['被评价者'] || ''}`;
        const existing = new Set(parsedCsv.rows.map(rowKey));
        const fullRows = [...parsedCsv.rows];

        for (const evaluator of characterNames) {
            for (const evaluatee of characterNames) {
                if (evaluator === evaluatee) continue;
                const key = `${evaluator}::${evaluatee}`;
                if (!existing.has(key)) {
                    fullRows.push({
                        '评价者': evaluator,
                        '被评价者': evaluatee,
                        '表面态度': '普通交流',
                        '内心真实评价': '尚未深入了解'
                    });
                    existing.add(key);
                }
            }
        }

        const headers = parsedCsv.headers.length > 0
            ? parsedCsv.headers
            : ['评价者', '被评价者', '表面态度', '内心真实评价'];

        return { headers, rows: fullRows };
    }, [activeCategory, selectedFile, parsedCsv, parsedRoster]);

    const eventSkeletonPayload = useMemo(() => {
        if (activeCategory !== 'event') return null;
        if (!selectedFile?.name?.includes('event_skeletons')) return null;
        try {
            const parsed = JSON.parse(fileContent || '{}');
            if (!parsed || typeof parsed !== 'object') return null;
            const events = Array.isArray(parsed.events) ? parsed.events : [];
            return {
                version: parsed.version,
                generated_at: parsed.generated_at,
                events
            };
        } catch {
            return null;
        }
    }, [activeCategory, selectedFile, fileContent]);

    const saveSkeletonPayload = (nextPayload: { version?: number; generated_at?: string; events: any[] }) => {
        handleSave(JSON.stringify(nextPayload, null, 2));
    };

    const runSkeletonValidation = async () => {
        if (!selectedFile?.name?.includes('event_skeletons')) return;
        if (adminPresetMode) {
            setMessage('预设编辑模式暂不走发布校验流程，可直接保存骨架文件');
            setTimeout(() => setMessage(''), 2200);
            return;
        }
        setIsValidatingSkeleton(true);
        try {
            const res = await gameApi.validateEventSkeletons({
                name: selectedFile.name,
                content: fileContent || '',
                rules: skeletonRules || undefined,
            });
            setSkeletonValidation(res?.data || null);
            setMessage('校验完成');
        } catch (e: any) {
            const detail = e?.response?.data?.detail || '校验失败';
            setMessage(String(detail));
        } finally {
            setIsValidatingSkeleton(false);
            setTimeout(() => setMessage(''), 2400);
        }
    };

    const runSkeletonAutoFix = () => {
        if (!eventSkeletonPayload) return;
        const cfg = skeletonAutoFixConfig;
        const safeEvents = Array.isArray(eventSkeletonPayload.events) ? eventSkeletonPayload.events : [];
        const fixedEvents = safeEvents.map((evt: any) => {
            const next = { ...evt };
            const meta = { ...(next.meta || {}) };
            const noteList = Array.isArray(meta.migration_notes) ? [...meta.migration_notes] : [];
            const evtType = String(next.type || '').toLowerCase();
            if (cfg.fixInvalidType && evtType !== 'daily' && evtType !== 'key') {
                next.type = 'daily';
                noteList.push('auto_fix: 无效 type 已回退为 daily');
            }
            if (cfg.fixInvalidNumbers) {
                if (!Number.isFinite(Number(next.priority))) next.priority = 50;
                if (!Number.isFinite(Number(next.cooldown_days))) next.cooldown_days = 1;
                if (typeof next.once !== 'boolean') next.once = false;
            }
            if (cfg.fixInvalidTriggers && (!next.triggers || typeof next.triggers !== 'object' || Array.isArray(next.triggers))) {
                next.triggers = { day_min: 1 };
                noteList.push('auto_fix: triggers 非对象已重置');
            }
            if (String(next.type) === 'key' && (cfg.normalizeKeyOptions || cfg.fillKeyOptions)) {
                const options = Array.isArray(next.options) ? [...next.options] : [];
                const normalizeAttitude = (raw: string) => {
                    const text = String(raw || '').trim();
                    if (['支持', '中立', '回避', '对抗'].includes(text)) return text;
                    if (text.includes('支')) return '支持';
                    if (text.includes('避') || text.includes('拒')) return '回避';
                    if (text.includes('抗') || text.includes('怼')) return '对抗';
                    return '中立';
                };
                const normalizeMood = (attitude: string) => {
                    const moodMap: Record<string, number> = { 支持: 2, 中立: 0, 回避: -2, 对抗: -3 };
                    return moodMap[attitude] ?? 0;
                };
                const normalized = cfg.normalizeKeyOptions
                    ? options.map((opt: any, idx: number) => {
                    const attitude = normalizeAttitude(String(opt?.attitude || '中立'));
                    return {
                        ...opt,
                        id: String(opt?.id || `${String(next.id || 'evt')}_opt_${idx + 1}`),
                        attitude,
                        effects: {
                            ...(opt?.effects || {}),
                            dorm_mood_delta: Number((opt?.effects || {}).dorm_mood_delta ?? normalizeMood(attitude))
                        }
                    };
                })
                    : options;
                while (cfg.fillKeyOptions && normalized.length < 3) {
                    const idx = normalized.length + 1;
                    const attitudes = ['支持', '中立', '回避'];
                    const moodMap: Record<string, number> = { 支持: 2, 中立: 0, 回避: -2 };
                    const attitude = attitudes[Math.min(idx - 1, 2)];
                    normalized.push({
                        id: `${String(next.id || 'evt')}_auto_opt_${idx}`,
                        attitude,
                        effects: { dorm_mood_delta: moodMap[attitude] || 0 },
                        text_hint: `自动补全选项 ${idx}`
                    });
                }
                next.options = normalized;
            }
            if (cfg.resetReviewed) {
                meta.reviewed = false;
            }
            meta.migration_notes = noteList;
            next.meta = meta;
            return next;
        });

        saveSkeletonPayload({
            ...eventSkeletonPayload,
            events: fixedEvents
        });
        setMessage('已执行批量修复（请再次运行校验）');
        setTimeout(() => setMessage(''), 2400);
    };

    const runSkeletonPromote = async () => {
        if (!selectedFile?.name?.includes('event_skeletons')) return;
        if (adminPresetMode) {
            setMessage('预设编辑模式无需发布流程，直接保存 event_skeletons.json 即可');
            setTimeout(() => setMessage(''), 2200);
            return;
        }
        setIsPromotingSkeleton(true);
        try {
            const latestValidationRes = await gameApi.validateEventSkeletons({
                name: selectedFile.name,
                content: fileContent || '',
                rules: skeletonRules || undefined,
            });
            const validationData = latestValidationRes?.data || null;
            setSkeletonValidation(validationData);
            const errors = Number(validationData?.summary?.error_count || 0);
            const warnings = Number(validationData?.summary?.warning_count || 0);
            if (errors > 0) {
                setMessage(`存在 ${errors} 个错误，已阻止发布`);
                return;
            }
            let allowWarnings = true;
            if (warnings > 0) {
                allowWarnings = window.confirm(`当前还有 ${warnings} 个警告，是否继续发布正式骨架？`);
                if (!allowWarnings) {
                    setMessage('已取消发布');
                    return;
                }
            }
            const promoteRes = await gameApi.promoteEventSkeletons({
                source_name: selectedFile.name,
                target_name: 'event_skeletons.json',
                content: fileContent || '',
                allow_warnings: allowWarnings
            });
            const data = promoteRes?.data || {};
            setMessage(data?.message || '发布成功');
            fetchFiles();
        } catch (e: any) {
            const detail = e?.response?.data?.detail || '发布失败';
            setMessage(String(detail));
        } finally {
            setIsPromotingSkeleton(false);
            setTimeout(() => setMessage(''), 2800);
        }
    };

    const applyAutoFixPreset = (presetId: AutoFixPresetId) => {
        const preset = AUTO_FIX_PRESETS[presetId];
        if (!preset) return;
        setSkeletonAutoFixPreset(presetId);
        setSkeletonAutoFixConfig({ ...preset.config });
        setMessage(`已切换修复预设：${preset.label}`);
        setTimeout(() => setMessage(''), 1800);
    };

    const updateCsvRow = (rowIndex: number, field: string, value: string) => {
        if (!parsedCsv) return;
        const newRows = [...parsedCsv.rows];
        newRows[rowIndex] = { ...newRows[rowIndex], [field]: value.replace(/,/g, '，') };
        saveCsv(parsedCsv.headers, newRows);
    };

    const addCsvRow = (data: { [key: string]: string }) => {
        if (!parsedCsv) return;
        const newRow: Record<string, string> = {};
        parsedCsv.headers.forEach(h => {
            newRow[h] = data[h] || '';
        });
        const newRows = [...parsedCsv.rows, newRow];
        saveCsv(parsedCsv.headers, newRows);
        setNewItemModal(null);
    };

    const removeCsvRow = (index: number) => {
        if (!parsedCsv) return;
        const newRows = [...parsedCsv.rows];
        newRows.splice(index, 1);
        saveCsv(parsedCsv.headers, newRows);
        setDeleteConfirm(null);
    };

    const addSkillItem = async (data: { name: string, target: string, content: string }) => {
        const fileName = `skills/${data.name}.md`;
        setIsLoading(true);
        try {
            const fullContent = `---
target: ${data.target}
created_at: ${new Date().toISOString()}
---

${data.content}`;
            await saveFileContent('md', fileName, fullContent);
            fetchFiles();
            setNewItemModal(null);
            setMessage('自定义 Skill 已成功装载');
        } catch (e) {
            setMessage('Skill 部署失败');
        } finally {
            setIsLoading(false);
        }
    };

    const handleGenerateSkillPrompt = async (concept: string) => {
        try {
            const res = await gameApi.generateSkillPrompt(concept);
            if (res.status === 'success') {
                return res.prompt;
            }
            throw new Error(res.message || 'AI generate failed');
        } catch (e: any) {
            setMessage('AI 生成失败，请检查网络或 API 配置');
            throw e;
        }
    };

    const saveCsv = (headers: string[], rows: Record<string, string>[]) => {
        const csvContent = [
            headers.join(','),
            ...rows.map(r => headers.map(h => r[h] || '').join(','))
        ].join('\n');
        handleSave(csvContent);
    };

    const editCharacterSettings = async (char: any) => {
        if (!char.file) {
            setMessage('此角色未关联设定文件');
            return;
        }
        const fileName = char.file.startsWith('characters/') ? char.file : `characters/${char.file}`;
        setIsLoading(true);
        try {
            const res = await readFileContent('md', fileName);
            if (res.status === 'success') {
                // Find ID (the key in the roster object)
                const id = Object.keys(parsedRoster).find(key => parsedRoster[key] === char) || 
                           Object.keys(parsedRoster).find(key => parsedRoster[key].name === char.name) || '';
                
                setEditingCharDetail({
                    id,
                    char: { ...char, id },
                    content: res.content || ''
                });
            }
        } catch (e) {
            setMessage('读取角色设定失败');
        } finally {
            setIsLoading(false);
        }
    };

    const saveCharacterDetail = async (id: string, updates: any, mdContent: string) => {
        if (!parsedRoster || !selectedFile) return;
        setIsLoading(true);
        try {
            // 1. Update Roster
            const newRoster = { ...parsedRoster, [id]: { ...parsedRoster[id], ...updates } };
            await saveFileContent('md', selectedFile.name, JSON.stringify(newRoster, null, 4));
            
            // 2. Update MD file
            const char = parsedRoster[id];
            const fileName = char.file.startsWith('characters/') ? char.file : `characters/${char.file}`;
            await saveFileContent('md', fileName, mdContent);
            
            // 3. Refresh local state
            setFileContent(JSON.stringify(newRoster, null, 4));
            setEditingCharDetail(null);
            setMessage('档案同步成功');
        } catch (e) {
            setMessage('同步失败!');
        } finally {
            setIsLoading(false);
        }
    };

    const backToRoster = () => {
        const roster = files.md.find(f => f.endsWith('roster.json'));
        if (roster) {
            setSelectedFile({ type: 'md', name: roster });
            setEditMode('visual');
            setShowExplorer(false);
        }
    };

    const handleSelectPool = (chapter: string, poolType: string) => {
        setEventFilter({ chapter, type: poolType });
        
        // Determine which file to open based on poolType
        let targetFile = '02_通用随机池.csv';
        if (poolType === 'Boss') targetFile = '01_固定剧情.csv';
        if (poolType === '条件') targetFile = '04_条件触发.csv';
        if (poolType === '专属' || poolType.includes('专属')) targetFile = '03_角色专属.csv';
        if (poolType === '开局') targetFile = '00_开局剧情.csv';
        
        const file = files.csv.find(f => f.includes(targetFile));
        if (file) {
            setSelectedFile({ type: 'csv', name: file });
            setEditMode('visual');
            setShowExplorer(false); // Hide explorer as requested for specific event editing
        } else {
            // If specific file not found, just open the first CSV
            const firstCsv = files.csv.find(f => f.endsWith('.csv'));
            if (firstCsv) {
                setSelectedFile({ type: 'csv', name: firstCsv });
                setShowExplorer(false);
            }
        }
    };

    const backToTimeline = () => {
        const timeline = files.csv.find(f => f === 'timeline.json');
        if (timeline) {
            setSelectedFile({ type: 'csv', name: timeline });
            setEditMode('visual');
            setShowExplorer(false); // Timeline also hides explorer for immersive view
        }
    };

    const handleSelectTopic = (fileName: string) => {
        const file = files.md.find(f => f === fileName || f.endsWith(fileName));
        if (file) {
            setSelectedFile({ type: 'md', name: file });
            setEditMode('code');
            setShowExplorer(false);
        }
    };

    const backToExplorer = () => {
        setSelectedFile(null);
        setEditMode('visual');
        setShowExplorer(false);
    };

    const activeSourceLabel = useMemo(() => {
        if (adminPresetMode) {
            return adminPresetTarget === 'preset' ? '官方预设模组' : '默认模板';
        }
        const source = String(userState?.editor_source || 'default');
        if (source === 'library') return '个人模组库';
        if (source === 'workshop') return '创意工坊';
        return '默认内容';
    }, [adminPresetMode, adminPresetTarget, userState]);

    const activeModLabel = useMemo(() => {
        if (adminPresetMode) {
            return adminPresetTarget === 'preset' ? (adminPresetModId || '未选择预设') : 'default';
        }
        const source = String(userState?.editor_source || 'default');
        const modId = String(userState?.editor_mod_id || 'default');
        if (!modId || modId === 'default') return '默认内容';
        const pool = source === 'workshop' ? workshopMods : libraryMods;
        const matched = pool.find((item: any) => String(item.id) === modId);
        return matched?.name || modId;
    }, [adminPresetMode, adminPresetTarget, adminPresetModId, userState, libraryMods, workshopMods]);

    const contextHint = useMemo(() => {
        if (adminPresetMode) {
            return adminPresetTarget === 'preset'
                ? '当前正在后台直接编辑官方预设模组内容，保存后会立即写入预设包。'
                : '当前正在后台直接编辑默认模板内容，保存后会影响默认模板加载结果。';
        }
        if (String(userState?.editor_source || 'default') !== 'library') {
            return '当前正在查看默认模组。默认模组为只读，若想微调，请先在模组中心另存为本地模组后再进入编辑。';
        }
        return '当前正在编辑本地模组。公开后的模组仍保留在你的本地库中，再次发布会同步更新工坊版本。';
    }, [adminPresetMode, adminPresetTarget, userState]);

    const canEditCurrentMod = useMemo(() => {
        if (adminPresetMode) return true;
        return String(userState?.editor_source || 'default') === 'library';
    }, [adminPresetMode, userState]);

    const isLoggedInAccount = useMemo(() => {
        return String(accountInfo?.auth_mode || 'visitor') === 'account';
    }, [accountInfo]);

    const currentEditingMod = useMemo(() => {
        const modId = String(userState?.editor_mod_id || 'default');
        if (!modId || modId === 'default') return null;
        return libraryMods.find((item: any) => String(item.id) === modId) || null;
    }, [userState, libraryMods]);

    const publishIntent = useMemo<'create' | 'update' | 'fork'>(() => {
        if (!currentEditingMod) return 'create';
        if (currentEditingMod.linked_workshop_id && currentEditingMod.visibility === 'public') {
            return 'update';
        }
        if (currentEditingMod.source_type === 'downloaded') {
            return 'fork';
        }
        return 'create';
    }, [currentEditingMod]);

    const editorStatusNotice = useMemo(() => {
        if (!currentEditingMod) return null;
        if (currentEditingMod.has_update) {
            return `原作已经更新到 v${currentEditingMod.upstream_version || currentEditingMod.version || 1}。你当前编辑的是本地副本 v${currentEditingMod.version || 1}；若想跟进原作者内容，请先回到模组中心同步后再继续改动。`;
        }
        if (publishIntent === 'update') {
            return `这份模组已经公开。你当前正在编辑它的本地源模组；下次发布会把工坊版本更新到 v${Number(currentEditingMod.version || 1) + 1}。`;
        }
        if (publishIntent === 'fork') {
            return `这是一份从工坊下载来的私有副本。你可以继续本地编辑；如果之后公开，会作为新的派生作品发布，不会覆盖原作者模组。`;
        }
        return null;
    }, [currentEditingMod, publishIntent]);

    const editorStatusTone = currentEditingMod?.has_update ? 'warning' : 'info';

    const openPublishModal = () => {
        if (adminPresetMode) return;
        if (!canEditCurrentMod) return;
        setPublishMetadata({
            name: currentEditingMod?.name || '我的自定义模组',
            author: currentEditingMod?.author || '佚名',
            description: currentEditingMod?.description || '包含了我修改过的世界观和角色设定。'
        });
        setShowPublishModal(true);
    };

    const jumpToModLibrary = () => {
        if (adminPresetMode) return;
        window.dispatchEvent(new CustomEvent('changeTab', { detail: 'mods' }));
    };

    const jumpToAccountCenter = () => {
        window.dispatchEvent(new CustomEvent('changeTab', { detail: 'account' }));
    };

    return (
        <>
        <div
            className="flex-1 flex flex-col h-full bg-[var(--color-cyan-light)]/40 backdrop-blur-3xl rounded-3xl border border-white/50 shadow-2xl animate-fade-in relative transition-all duration-700 overflow-hidden"
        >
            <EditorHeader
                sidebarCollapsed={sidebarCollapsed}
                setSidebarCollapsed={setSidebarCollapsed}
                selectedFile={selectedFile}
                activeSourceLabel={activeSourceLabel}
                activeModLabel={activeModLabel}
                contextHint={contextHint}
                statusNotice={editorStatusNotice || undefined}
                statusNoticeTone={editorStatusTone}
                editMode={editMode}
                setEditMode={setEditMode}
                isSaving={isSaving}
                canEdit={canEditCurrentMod}
                canPublish={!adminPresetMode && canEditCurrentMod}
                saveLabel={canEditCurrentMod ? '提交修改' : '前往模组库另存为'}
                onSave={() => (canEditCurrentMod ? handleSave() : jumpToModLibrary())}
                onPublish={openPublishModal}
                onShowGuide={() => setShowGuide(true)}
            />

            <div className="flex flex-1 overflow-hidden bg-white/10">
                <EditorSidebar
                    sidebarCollapsed={sidebarCollapsed}
                    showExplorer={showExplorer}
                    activeCategory={activeCategory}
                    setActiveCategory={setActiveCategory}
                    files={files}
                    selectedFile={selectedFile}
                    setSelectedFile={setSelectedFile}
                    onRefresh={fetchFiles}
                    categories={categories}
                />

                <div className="flex-1 flex flex-col bg-[var(--color-cyan-light)]/10 p-6 md:p-8 overflow-hidden relative">
                    {activeCategory === 'skills' && (
                        <div className="mb-4 rounded-2xl border border-[var(--color-cyan-main)]/15 bg-white px-4 py-3 flex flex-wrap items-center justify-between gap-3">
                            <div>
                                <div className="text-sm font-black text-[var(--color-cyan-dark)]">附加系统开关</div>
                                <div className="text-[10px] font-bold text-slate-500 mt-1">
                                    手机系统关闭后，游戏内不会再生成微信通知，右上角手机按钮会自动隐藏。
                                </div>
                            </div>
                            <button
                                onClick={() => handleTogglePhoneSystem(!(modFeatures?.phone_system_enabled !== false))}
                                disabled={isSavingFeatures}
                                className={`px-3 py-1.5 rounded-lg text-[11px] font-black transition-all ${
                                    modFeatures?.phone_system_enabled !== false
                                        ? 'bg-[var(--color-cyan-main)] text-white'
                                        : 'bg-slate-100 text-slate-600'
                                } ${isSavingFeatures ? 'opacity-60 cursor-not-allowed' : ''}`}
                            >
                                {isSavingFeatures ? '保存中...' : (modFeatures?.phone_system_enabled !== false ? '手机系统：已开启' : '手机系统：已关闭')}
                            </button>
                        </div>
                    )}
                    {activeCategory === 'event' && (
                        <div className="mb-4 rounded-2xl border border-[var(--color-cyan-main)]/15 bg-white px-4 py-3 flex flex-wrap items-center justify-between gap-3">
                            <div>
                                <div className="text-sm font-black text-[var(--color-cyan-dark)]">剧情编排工作台</div>
                                <div className="text-[10px] font-bold text-slate-500 mt-1">
                                    关系说明：先由骨架决定触发什么事件、结算什么结果，再由事件文本负责怎么演出来。
                                </div>
                            </div>
                            <div className="inline-flex items-center rounded-xl border border-[var(--color-cyan-main)]/20 bg-[var(--color-cyan-light)]/30 p-1">
                                <button
                                    onClick={() => setEventWorkbench('story')}
                                    className={`px-3 py-1.5 rounded-lg text-[11px] font-black transition-all ${
                                        eventWorkbench === 'story'
                                            ? 'bg-[var(--color-cyan-main)] text-white'
                                            : 'text-[var(--color-cyan-dark)] hover:bg-white'
                                    }`}
                                >
                                    事件编辑（CSV）
                                </button>
                                <button
                                    onClick={() => setEventWorkbench('skeleton')}
                                    className={`px-3 py-1.5 rounded-lg text-[11px] font-black transition-all ${
                                        eventWorkbench === 'skeleton'
                                            ? 'bg-[var(--color-cyan-main)] text-white'
                                            : 'text-[var(--color-cyan-dark)] hover:bg-white'
                                    }`}
                                >
                                    骨架编辑
                                </button>
                            </div>
                        </div>
                    )}
                    {message && (
                        <div className="fixed top-24 right-10 z-[100] animate-fade-in-up">
                            <div className="bg-[var(--color-cyan-dark)]/90 backdrop-blur-xl text-white px-8 py-5 rounded-[2rem] border border-white/20 shadow-2xl shadow-cyan-900/40 flex items-center">
                                <div className="w-2 h-2 rounded-full bg-[var(--color-yellow-main)] mr-4 animate-pulse shadow-[0_0_10px_var(--color-yellow-main)]" />
                                <span className="text-xs font-black uppercase tracking-widest">{message}</span>
                            </div>
                        </div>
                    )}

                    {(!selectedFile && activeCategory !== 'world' && activeCategory !== 'skills') ? (
                        <div className="flex-1 flex flex-col items-center justify-center opacity-10">
                            <Sparkles size={80} className="text-slate-300 mb-6" />
                            <p className="text-xl font-black text-[var(--color-cyan-main)] uppercase tracking-widest">
                                {activeCategory === 'event'
                                    ? (eventWorkbench === 'skeleton' ? '未找到骨架文件' : '未找到事件文件')
                                    : '请选择操作节点'}
                            </p>
                        </div>
                    ) : (
                        <div className="flex-1 flex flex-col bg-white rounded-2xl shadow-sm border border-[var(--color-cyan-main)]/10 overflow-hidden relative group transition-all">
                            {(activeCategory === 'world' || activeCategory === 'skills') && !selectedFile ? (
                                <TopicExplorer
                                    category={activeCategory as any}
                                    files={files.md}
                                    onSelectTopic={handleSelectTopic}
                                    canEdit={canEditCurrentMod}
                                    onAddNew={activeCategory === 'skills' ? () => setNewItemModal({ type: 'skill', name: '', description: '' }) : undefined}
                                />
                            ) : activeCategory === 'scene' && selectedFile?.name === 'world/scenes.json' && editMode === 'visual' ? (
                                <SceneConfigEditor
                                    config={parsedScenes || { default_image: '/assets/backgrounds/宿舍.jpg', scenes: [] }}
                                    onChange={(next) => setFileContent(JSON.stringify(next, null, 2))}
                                    onSave={() => handleSave()}
                                    canEdit={canEditCurrentMod}
                                />
                            ) : activeCategory === 'char' && selectedFile?.name.endsWith('roster.json') && editMode === 'visual' ? (
                                <CharacterEditor
                                    parsedRoster={parsedRoster}
                                    onUpdateItem={updateRosterItem}
                                    onUploadAvatar={handleAvatarUpload}
                                    onEditSettings={editCharacterSettings}
                                    onAddNew={() => setNewItemModal({ type: 'char', name: '', archetype: '', description: '' })}
                                    onDelete={(id, name) => setDeleteConfirm({ type: 'char', id, name })}
                                    canEdit={canEditCurrentMod}
                                />
                            ) : activeCategory === 'event' && selectedFile?.name?.includes('timeline.json') && editMode === 'visual' ? (
                                <TimelineView
                                    content={fileContent}
                                    onSave={(c) => handleSave(c)}
                                    onSelectPool={handleSelectPool}
                                    canEdit={canEditCurrentMod}
                                />
                            ) : activeCategory === 'event' && selectedFile?.name?.includes('event_skeletons') && editMode === 'visual' ? (
                                <EventSkeletonEditor
                                    payload={eventSkeletonPayload as any}
                                    onSavePayload={saveSkeletonPayload}
                                    onValidate={runSkeletonValidation}
                                    onAutoFix={runSkeletonAutoFix}
                                    autoFixPreset={skeletonAutoFixPreset}
                                    autoFixPresets={AUTO_FIX_PRESETS}
                                    onApplyAutoFixPreset={applyAutoFixPreset}
                                    autoFixConfig={skeletonAutoFixConfig}
                                    onAutoFixConfigChange={(next) => setSkeletonAutoFixConfig((prev) => ({ ...prev, ...next }))}
                                    onPromote={runSkeletonPromote}
                                    validating={isValidatingSkeleton}
                                    promoting={isPromotingSkeleton}
                                    validationResult={skeletonValidation}
                                    canEdit={canEditCurrentMod}
                                />
                            ) : activeCategory === 'event' && selectedFile?.type === 'csv' && editMode === 'visual' ? (
                                <EventEditor
                                    parsedCsv={parsedCsv}
                                    onUpdateRow={updateCsvRow}
                                    onAddNew={() => setNewItemModal({ type: 'event', name: '', description: '' })}
                                    onDeleteRow={(idx, name) => setDeleteConfirm({ type: 'csv-row', id: `${idx}`, index: idx, name })}
                                    onBack={backToTimeline}
                                    filter={eventFilter}
                                    focusMode={selectedFile?.name?.includes('00_开局剧情.csv') ? 'opening' : 'default'}
                                    canEdit={canEditCurrentMod}
                                />
                            ) : activeCategory === 'relation' && selectedFile?.name?.includes('relationship.csv') && editMode === 'visual' ? (
                                <RelationshipMatrix
                                    parsedRoster={parsedRoster}
                                    parsedCsv={relationCsv}
                                    onUpdateRow={(rowIndex, field, value) => {
                                        if (!relationCsv) return;
                                        const newRows = [...relationCsv.rows];
                                        newRows[rowIndex] = { ...newRows[rowIndex], [field]: value.replace(/,/g, '，') };
                                        saveCsv(relationCsv.headers, newRows);
                                    }}
                                    onAddRow={(data) => {
                                        if (!relationCsv) return;
                                        const newRows = [...relationCsv.rows, data];
                                        saveCsv(relationCsv.headers, newRows);
                                    }}
                                    onSaveAll={() => {
                                        if (relationCsv) {
                                            saveCsv(relationCsv.headers, relationCsv.rows);
                                        } else {
                                            handleSave();
                                        }
                                    }}
                                    canEdit={canEditCurrentMod}
                                />
                            ) : (
                                <CodeWorkspace
                                    selectedFile={selectedFile}
                                    fileContent={fileContent}
                                    setFileContent={setFileContent}
                                    isLoading={isLoading}
                                    readOnly={!canEditCurrentMod}
                                    onBack={(activeCategory === 'world' || activeCategory === 'skills') ? backToExplorer : activeCategory === 'char' ? backToRoster : undefined}
                                />
                            )}
                        </div>
                    )}
                </div>
            </div>
        </div>

        <EditorModals
                showPublishModal={showPublishModal}
                setShowPublishModal={setShowPublishModal}
                publishMetadata={publishMetadata}
                setPublishMetadata={setPublishMetadata}
                newItemModal={newItemModal}
                setNewItemModal={setNewItemModal}
                deleteConfirm={deleteConfirm}
                setDeleteConfirm={setDeleteConfirm}
                onAddRosterItem={addRosterItem}
                onAddCsvRow={addCsvRow}
                onAddSkillItem={addSkillItem}
                onRemoveRosterItem={removeRosterItem}
                onRemoveCsvRow={removeCsvRow}
                onGenerateSkillPrompt={handleGenerateSkillPrompt}
                parsedCsvHeaders={parsedCsv?.headers || []}
                publishIntent={publishIntent}
                currentEditingMod={currentEditingMod}
                isLoggedInAccount={isLoggedInAccount}
                onNavigateAccount={jumpToAccountCenter}
            />

            <EditorGuide
                isOpen={showGuide}
                onClose={() => setShowGuide(false)}
            />

            {editingCharDetail && (
                <CharacterDetailModal
                    char={editingCharDetail.char}
                    charContent={editingCharDetail.content}
                    onClose={() => setEditingCharDetail(null)}
                    onSave={saveCharacterDetail}
                    onUploadAvatar={handleAvatarUpload}
                />
            )}
        </>
    );
};
