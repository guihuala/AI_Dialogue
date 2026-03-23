import { useEffect, useRef, useState, type PointerEvent as ReactPointerEvent } from 'react';
import { useGameStore } from '../store/gameStore';
import { gameApi } from '../api/gameApi';
import { TitleMenu } from './TitleMenu';
import { GameSetup } from './GameSetup';
import { SaveSelection } from './SaveSelection';

import { AttributeNotifications } from './game/AttributeNotifications';
import { ScenePortraits } from './game/ScenePortraits';
import { HistoryPanel } from './game/HistoryPanel';
import { GameUIControls } from './game/GameUIControls';
import { ActionOptions } from './game/ActionOptions';
import { EndOverlay } from './game/EndOverlay';
import { DialogBox } from './game/DialogBox';
import { AnnouncementPanel } from './common/AnnouncementPanel';
import { ConfirmDialog } from './common/ConfirmDialog';

const isTransitionChoice = (choice?: string): boolean => {
    const text = String(choice || '');
    return /继续剧情|进入下一幕|下一幕|转场|进入下一事件|继续前进/.test(text);
};

export const GameView = ({ onTabChange }: { onTabChange: (tab: any) => void }) => {
    const {
        displayText,
        nextOptions,
        isEnd,
        isLoading,
        performTurn,
        startGame,
        isPlaying,
        history,
        togglePhone,
        wechatNotifications,
        phoneSystemEnabled,
        typewriterSpeed,
        saveGame,
        loadSave,
        prefetch,
        pendingChoice,
        current_evt_id,
        current_scene,
        resetGame,
        active_roommates,
        narrativeState,
        turnDebug,
        systemState,
        systemDailyPlan,
        systemKeyResolution,
        weeklySummary
    } = useGameStore();

    const scrollRef = useRef<HTMLDivElement>(null);
    const historyScrollRef = useRef<HTMLDivElement>(null);
    const gameRootRef = useRef<HTMLDivElement>(null);
    const debugPanelRef = useRef<HTMLDivElement>(null);
    const relationPanelRef = useRef<HTMLDivElement>(null);

    const [typedText, setTypedText] = useState('');
    const [isTyping, setIsTyping] = useState(false);
    const [showHistory, setShowHistory] = useState(false);
    const [showSceneTransition, setShowSceneTransition] = useState(false);
    const [showBackConfirm, setShowBackConfirm] = useState(false);
    const [showAnnouncement, setShowAnnouncement] = useState(false);
    const [showDebugPanel, setShowDebugPanel] = useState(true);
    const [showRelationPanel, setShowRelationPanel] = useState(true);
    const [panelPosReady, setPanelPosReady] = useState(false);
    const [panelPos, setPanelPos] = useState({
        debug: { x: 0, y: 20 },
        relation: { x: 0, y: 220 },
    });
    const [draggingPanel, setDraggingPanel] = useState<'debug' | 'relation' | null>(null);
    const [sceneCatalog, setSceneCatalog] = useState<any>({ default_image: '/assets/backgrounds/宿舍.jpg', scenes: [] });
    const dragMetaRef = useRef<{ panel: 'debug' | 'relation'; dx: number; dy: number } | null>(null);
    const prevEventIdRef = useRef<string>('');

    // Notifications system
    const [notifications, setNotifications] = useState<{ msg: string; id: number }[]>([]);
    const [currentSpeaker, setCurrentSpeaker] = useState<string | undefined>(undefined);

    // Dialog pacing state
    const [dialogSegments, setDialogSegments] = useState<string[]>([]);
    const [currentSegmentIndex, setCurrentSegmentIndex] = useState(0);

    // Auto-scroll story text
    useEffect(() => {
        if (scrollRef.current) {
            scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
        }
    }, [typedText]);

    // Auto-scroll history overlay
    useEffect(() => {
        if (showHistory && historyScrollRef.current) {
            historyScrollRef.current.scrollTop = historyScrollRef.current.scrollHeight;
        }
    }, [showHistory, history]);

    useEffect(() => {
        if (isLoading && (isTransitionChoice(pendingChoice || '') || isEnd)) {
            setShowSceneTransition(true);
        }
    }, [isLoading, pendingChoice, isEnd]);

    useEffect(() => {
        const prev = prevEventIdRef.current;
        const changed = !!prev && !!current_evt_id && prev !== current_evt_id;
        prevEventIdRef.current = current_evt_id || '';
        if (!changed) return;

        setShowSceneTransition(true);
        const timer = setTimeout(() => setShowSceneTransition(false), 700);
        return () => clearTimeout(timer);
    }, [current_evt_id]);

    useEffect(() => {
        if (!isLoading && !showSceneTransition) return;
        if (isLoading) return;
        const timer = setTimeout(() => setShowSceneTransition(false), 200);
        return () => clearTimeout(timer);
    }, [isLoading, showSceneTransition]);

    // Extract notifications and split text
    useEffect(() => {
        if (!displayText) {
            setDialogSegments([]);
            setCurrentSegmentIndex(0);
            setTypedText('');
            return;
        }

        let cleanedText = displayText;
        const attrChanges: string[] = [];
        const regex = /[【\[\(]\s*(.*?)\s*[】\]\)]/g;
        
        cleanedText = cleanedText.replace(regex, (match, content) => {
            if (/好感|理智|声望|财产|资产|系统|Gpa|增加|减少|加|减|\+|-/i.test(content)) {
                attrChanges.push(content);
                return '';
            }
            return match;
        });

        if (attrChanges.length > 0) {
            const newNotifs = attrChanges.map((msg, i) => ({ msg, id: Date.now() + i }));
            setNotifications(prev => [...prev, ...newNotifs]);
            setTimeout(() => {
                setNotifications(prev => prev.filter(n => !newNotifs.find(x => x.id === n.id)));
            }, 5000);
        }

        const segments = cleanedText
            .split(/(?<=\n|”)/g)
            .map(s => s.trim())
            .filter(s => s.length > 0);

        setDialogSegments(segments.length > 0 ? segments : [cleanedText]);
        setCurrentSegmentIndex(0);
    }, [displayText]);

    // Typewriter effect
    useEffect(() => {
        if (dialogSegments.length === 0 || currentSegmentIndex >= dialogSegments.length) {
            setTypedText('');
            setIsTyping(false);
            setCurrentSpeaker(undefined); // Clear speaker when dialog ends
            return;
        }

        const currentText = dialogSegments[currentSegmentIndex];
        
        // --- [SPEAKER & PREFIX EXTRACTION] ---
        let displayStr = currentText;
        let speaker: string | undefined = undefined;

        if (currentText.startsWith("[暗场动态]")) {
            displayStr = currentText.replace("[暗场动态]", "").trim();
            speaker = undefined;
        } else {
            const speakerMatch = currentText.match(/^\*\*\[(.*?)\]\*\*/);
            if (speakerMatch) {
                speaker = speakerMatch[1];
                displayStr = currentText.replace(/^\*\*\[(.*?)\]\*\*\s*/, "");
            } else {
                const simpleSpeakerMatch = currentText.match(/^([^：:]{1,10})[：:]/);
                if (simpleSpeakerMatch) {
                    speaker = simpleSpeakerMatch[1];
                    displayStr = currentText.replace(/^([^：:]{1,10})[：:]\s*/, "");
                }
            }
        }
        
        setCurrentSpeaker(speaker);

        setIsTyping(true);
        let i = 0;
        const interval = setInterval(() => {
            setTypedText(displayStr.slice(0, i + 1));
            i++;
            if (i >= displayStr.length) {
                clearInterval(interval);
                setIsTyping(false);
            }
        }, typewriterSpeed);

        return () => clearInterval(interval);
    }, [currentSegmentIndex, dialogSegments, typewriterSpeed]);

    const handleTextClick = () => {
        if (dialogSegments.length === 0) return;
        if (isTyping) {
            setTypedText(dialogSegments[currentSegmentIndex]);
            setIsTyping(false);
        } else if (currentSegmentIndex < dialogSegments.length - 1) {
            setCurrentSegmentIndex(prev => prev + 1);
        }
    };

    const isDialogFinished = dialogSegments.length > 0 && currentSegmentIndex === dialogSegments.length - 1 && !isTyping;

    const [phase, setPhase] = useState<'title' | 'save_select' | 'setup' | 'playing'>(isPlaying ? 'playing' : 'title');

    useEffect(() => {
        if (isPlaying) setPhase('playing');
    }, [isPlaying]);

    useEffect(() => {
        if (!isPlaying) return;
        const loadScenes = async () => {
            try {
                const res = await gameApi.getAdminFile('md', 'world/scenes.json');
                if (res?.status === 'success' && res.content) {
                    const parsed = JSON.parse(res.content);
                    if (parsed && typeof parsed === 'object') {
                        setSceneCatalog({
                            default_image: parsed.default_image || '/assets/backgrounds/宿舍.jpg',
                            scenes: Array.isArray(parsed.scenes) ? parsed.scenes : []
                        });
                    }
                }
            } catch {
                // ignore and keep fallback mapping
            }
        };
        loadScenes();
    }, [isPlaying]);

    const PANEL_SAFE_TOP = 96;

    const clampPanelPosition = (panel: 'debug' | 'relation', x: number, y: number) => {
        const root = gameRootRef.current;
        const panelEl = panel === 'debug' ? debugPanelRef.current : relationPanelRef.current;
        if (!root) return { x, y };

        const rootRect = root.getBoundingClientRect();
        const panelWidth = panelEl?.offsetWidth || 340;
        const panelHeight = panelEl?.offsetHeight || 220;
        const min = 8;
        const minY = PANEL_SAFE_TOP;
        const maxX = Math.max(min, rootRect.width - panelWidth - 8);
        const maxY = Math.max(minY, rootRect.height - panelHeight - 8);
        return {
            x: Math.max(min, Math.min(maxX, x)),
            y: Math.max(minY, Math.min(maxY, y)),
        };
    };

    useEffect(() => {
        const root = gameRootRef.current;
        if (!root || panelPosReady) return;

        const rootWidth = root.clientWidth || 1200;
        const savedRaw = localStorage.getItem('game_overlay_panel_pos_v1');
        if (savedRaw) {
            try {
                const saved = JSON.parse(savedRaw);
                const debug = clampPanelPosition('debug', Number(saved?.debug?.x || 0), Number(saved?.debug?.y || 20));
                const relation = clampPanelPosition('relation', Number(saved?.relation?.x || 0), Number(saved?.relation?.y || 220));
                setPanelPos({ debug, relation });
                setPanelPosReady(true);
                return;
            } catch {
                // ignore broken localStorage
            }
        }

        const debugDefault = clampPanelPosition('debug', rootWidth - 360, 20);
        const relationDefault = clampPanelPosition('relation', rootWidth - 360, 220);
        setPanelPos({ debug: debugDefault, relation: relationDefault });
        setPanelPosReady(true);
    }, [panelPosReady]);

    useEffect(() => {
        if (!panelPosReady) return;
        localStorage.setItem('game_overlay_panel_pos_v1', JSON.stringify(panelPos));
    }, [panelPos, panelPosReady]);

    useEffect(() => {
        const onResize = () => {
            setPanelPos((prev) => ({
                debug: clampPanelPosition('debug', prev.debug.x, prev.debug.y),
                relation: clampPanelPosition('relation', prev.relation.x, prev.relation.y),
            }));
        };
        window.addEventListener('resize', onResize);
        return () => window.removeEventListener('resize', onResize);
    }, []);

    useEffect(() => {
        if (!draggingPanel) return;
        const onPointerMove = (ev: PointerEvent) => {
            const root = gameRootRef.current;
            const meta = dragMetaRef.current;
            if (!root || !meta) return;
            const rootRect = root.getBoundingClientRect();
            const nextX = ev.clientX - rootRect.left - meta.dx;
            const nextY = ev.clientY - rootRect.top - meta.dy;
            const clamped = clampPanelPosition(meta.panel, nextX, nextY);
            setPanelPos((prev) => ({ ...prev, [meta.panel]: clamped }));
        };
        const onPointerUp = () => {
            dragMetaRef.current = null;
            setDraggingPanel(null);
        };

        window.addEventListener('pointermove', onPointerMove);
        window.addEventListener('pointerup', onPointerUp);
        return () => {
            window.removeEventListener('pointermove', onPointerMove);
            window.removeEventListener('pointerup', onPointerUp);
        };
    }, [draggingPanel]);

    const handlePanelDragStart = (panel: 'debug' | 'relation', ev: ReactPointerEvent<HTMLButtonElement>) => {
        const root = gameRootRef.current;
        if (!root) return;
        const rootRect = root.getBoundingClientRect();
        const pos = panelPos[panel];
        dragMetaRef.current = {
            panel,
            dx: ev.clientX - rootRect.left - pos.x,
            dy: ev.clientY - rootRect.top - pos.y,
        };
        setDraggingPanel(panel);
        ev.preventDefault();
    };

    if (phase === 'title') {
        return (
            <>
                <TitleMenu
                    onStart={() => setPhase('save_select')}
                    onWorkshop={() => onTabChange('workshop')}
                    onEditor={() => onTabChange('editor')}
                    onSettings={() => onTabChange('settings')}
                    onAnnouncement={() => setShowAnnouncement(true)}
                />
                <AnnouncementPanel isOpen={showAnnouncement} onClose={() => setShowAnnouncement(false)} />
            </>
        );
    }

    if (phase === 'save_select') {
        return <SaveSelection onBack={() => setPhase('title')} onNewGame={() => setPhase('setup')} onLoadGame={loadSave} />;
    }

    if (phase === 'setup') {
        return <GameSetup onBack={() => setPhase('save_select')} onStartGame={startGame} onTabChange={onTabChange} />;
    }

    const determineCharactersInScene = () => {
        const selectedRoommates = Array.isArray(active_roommates) ? active_roommates : [];
        if (selectedRoommates.length === 0) return [];
        const lines = displayText.split('\n').filter(l => l.trim().length > 0);
        const sceneContext = lines.slice(-10).join('\n');
        const recentContext = lines.slice(-3).join('\n');
        const portraitMapping = [
            { id: '唐', names: ['唐梦琪', '梦琪', '唐'] },
            { id: '李', names: ['李一诺', '一诺', '李'] },
            { id: '赵', names: ['赵鑫', '鑫鑫', '赵'] },
            { id: '林', names: ['林飒', '飒飒', '林'] },
            { id: '陈', names: ['陈雨婷', '雨婷', '陈'] },
            { id: '苏', names: ['苏浅', '浅浅', '苏'] },
        ];

        let presentChars: any[] = [];
        for (const c of portraitMapping.filter((item) =>
            item.names.some((name) => selectedRoommates.includes(name))
        )) {
            let isPresent = false;
            let isSpeaking = false;
            let highestMentionIdx = -1;
            for (const name of c.names) {
                const dialogIdx = Math.max(recentContext.lastIndexOf(`${name}：`), recentContext.lastIndexOf(`${name}:`));
                if (dialogIdx > -1) { isPresent = true; isSpeaking = true; highestMentionIdx = Math.max(highestMentionIdx, dialogIdx); }
                const sceneIdx = sceneContext.lastIndexOf(name);
                if (sceneIdx > -1) { isPresent = true; highestMentionIdx = Math.max(highestMentionIdx, sceneIdx); }
            }
            // 已选室友默认都显示；最近文本只用于排序和高亮发言者。
            if (currentSpeaker && c.names.includes(currentSpeaker)) {
                isSpeaking = true;
                highestMentionIdx = Math.max(highestMentionIdx, Number.MAX_SAFE_INTEGER);
            }
            presentChars.push({ id: c.id, isSpeaking, lastMentionIdx: isPresent ? highestMentionIdx : -1 });
        }

        const actualSpeaker = [...presentChars].filter(c => c.isSpeaking).sort((a, b) => b.lastMentionIdx - a.lastMentionIdx)[0];
        if (actualSpeaker) presentChars.forEach(c => { if (c.id !== actualSpeaker.id) c.isSpeaking = false; });
        return presentChars.sort((a, b) => b.lastMentionIdx - a.lastMentionIdx).slice(0, 4);
    };

    const parseMarktext = (text: string) => {
        const parts = text.split(/\*\*/g);
        return parts.map((part, i) => (i % 2 === 1 ? <strong key={i} className="font-black drop-shadow-sm font-bold tracking-widest">{part}</strong> : <span key={i}>{part}</span>));
    };

    const getSceneBackground = (scene?: string) => {
        const normalized = (scene || '').trim();
        const configuredScenes = Array.isArray(sceneCatalog?.scenes) ? sceneCatalog.scenes : [];
        for (const item of configuredScenes) {
            const image = String(item?.image || '').trim();
            if (!image) continue;
            const name = String(item?.name || '').trim();
            const keywords = Array.isArray(item?.keywords) ? item.keywords.map((k: any) => String(k || '').trim()).filter(Boolean) : [];
            if ((name && normalized.includes(name)) || keywords.some((kw: string) => normalized.includes(kw))) {
                return image;
            }
        }

        if (normalized.includes('宿舍') || normalized.includes('寝室')) return '/assets/backgrounds/宿舍.jpg';
        if (normalized.includes('教室')) return '/assets/backgrounds/教室.jpg';
        if (normalized.includes('图书馆')) return '/assets/backgrounds/图书馆.jpg';
        if (normalized.includes('食堂')) return '/assets/backgrounds/食堂.jpg';
        if (normalized.includes('商业街')) return '/assets/backgrounds/商业街.jpg';
        if (normalized.includes('办公室')) return '/assets/backgrounds/办公室.jpg';
        if (normalized.includes('未知')) return '/assets/backgrounds/未知.jpg';
        return String(sceneCatalog?.default_image || '/assets/backgrounds/宿舍.jpg');
    };

    const relationItems = Object.entries((narrativeState as any)?.relationship_state || {})
        .filter(([name]) => (active_roommates || []).includes(name))
        .slice(0, 4);
    const longTermMilestones: string[] = Array.isArray((narrativeState as any)?.long_term_milestones)
        ? (narrativeState as any).long_term_milestones.slice(0, 3)
        : [];

    return (
        <div ref={gameRootRef} className="flex-1 flex flex-col h-full rounded-2xl border-2 border-[var(--color-cyan-main)]/20 shadow-xl overflow-hidden relative bg-black">
            <div className="absolute inset-0 bg-cover bg-center opacity-70" style={{ backgroundImage: `url('${getSceneBackground(current_scene)}')` }} />
            <div
                className={`absolute inset-0 z-40 pointer-events-none transition-opacity duration-500 ${
                    showSceneTransition ? 'opacity-100' : 'opacity-0'
                }`}
            >
                <div className="absolute inset-0 bg-black/95" />
            </div>

            <AttributeNotifications notifications={notifications} />

            {!!turnDebug && (
                <div
                    ref={debugPanelRef}
                    className="absolute z-30 w-[340px] max-w-[calc(100%-16px)]"
                    style={{
                        left: panelPos.debug.x,
                        top: panelPos.debug.y,
                        visibility: panelPosReady ? 'visible' : 'hidden',
                    }}
                >
                    <div className="rounded-2xl border border-[var(--color-cyan-main)]/20 bg-white/90 backdrop-blur-md shadow-lg overflow-hidden">
                        <div className="flex items-center bg-[var(--color-cyan-light)]/40 hover:bg-[var(--color-cyan-light)]/60 transition">
                            <button
                                type="button"
                                onClick={() => setShowDebugPanel((v) => !v)}
                                className="flex-1 px-3 py-2 text-left text-[10px] font-black tracking-widest uppercase text-[var(--color-cyan-main)]"
                            >
                                Turn Debug {showDebugPanel ? '▲' : '▼'}
                            </button>
                            <button
                                type="button"
                                onPointerDown={(ev) => handlePanelDragStart('debug', ev)}
                                className={`px-2.5 py-2 text-[11px] font-black text-[var(--color-cyan-main)]/80 hover:text-[var(--color-cyan-main)] ${draggingPanel === 'debug' ? 'cursor-grabbing' : 'cursor-grab'}`}
                                title="拖拽面板"
                                aria-label="拖拽 Turn Debug 面板"
                            >
                                ⠿
                            </button>
                        </div>
                        {showDebugPanel && (
                            <div className="p-3 space-y-2 text-[11px] text-[var(--color-cyan-dark)]">
                                {turnDebug.timings && (
                                    <div className="rounded-xl border border-[var(--color-cyan-main)]/10 bg-white p-2">
                                        <div className="font-black text-[10px] uppercase tracking-wider text-[var(--color-cyan-main)] mb-1">Timings (s)</div>
                                        <div className="grid grid-cols-2 gap-x-2 gap-y-1">
                                            {Object.entries(turnDebug.timings).map(([k, v]) => (
                                                <div key={k} className="flex items-center justify-between gap-2">
                                                    <span className="font-bold text-slate-500">{k}</span>
                                                    <span className="font-black tabular-nums">{Number(v).toFixed(3)}</span>
                                                </div>
                                            ))}
                                        </div>
                                    </div>
                                )}
                                {turnDebug.prompt_diagnostics && (
                                    <div className="rounded-xl border border-[var(--color-cyan-main)]/10 bg-white p-2">
                                        <div className="font-black text-[10px] uppercase tracking-wider text-[var(--color-cyan-main)] mb-1">Prompt Size</div>
                                        <div className="flex items-center justify-between">
                                            <span className="font-bold text-slate-500">system chars</span>
                                            <span className="font-black tabular-nums">{turnDebug.prompt_diagnostics?.system?.total_chars || 0}</span>
                                        </div>
                                        <div className="flex items-center justify-between mt-1">
                                            <span className="font-bold text-slate-500">user chars</span>
                                            <span className="font-black tabular-nums">{turnDebug.prompt_diagnostics?.user?.total_chars || 0}</span>
                                        </div>
                                    </div>
                                )}
                                {turnDebug?.prompt_payload && (
                                    <div className="rounded-xl border border-[var(--color-cyan-main)]/10 bg-white p-2">
                                        <div className="font-black text-[10px] uppercase tracking-wider text-[var(--color-cyan-main)] mb-1">Prompt Payload</div>
                                        <div className="text-[10px] text-slate-600">
                                            truncated {turnDebug.prompt_payload?.truncated ? 'yes' : 'no'}
                                            {" · "}
                                            chars s/u {turnDebug.prompt_payload?.system_chars ?? 0} / {turnDebug.prompt_payload?.user_chars ?? 0}
                                        </div>
                                        <div className="mt-1 text-[10px] text-slate-500">system prompt</div>
                                        <pre className="mt-0.5 max-h-28 overflow-auto rounded-lg border border-[var(--color-cyan-main)]/10 bg-slate-50 p-2 text-[10px] leading-relaxed text-slate-700 whitespace-pre-wrap break-words">
{String(turnDebug.prompt_payload?.system_prompt || '')}
                                        </pre>
                                        <div className="mt-1 text-[10px] text-slate-500">user prompt</div>
                                        <pre className="mt-0.5 max-h-28 overflow-auto rounded-lg border border-[var(--color-cyan-main)]/10 bg-slate-50 p-2 text-[10px] leading-relaxed text-slate-700 whitespace-pre-wrap break-words">
{String(turnDebug.prompt_payload?.user_prompt || '')}
                                        </pre>
                                    </div>
                                )}
                                {turnDebug?.render_source && (
                                    <div className="rounded-xl border border-[var(--color-cyan-main)]/10 bg-white p-2">
                                        <div className="font-black text-[10px] uppercase tracking-wider text-[var(--color-cyan-main)] mb-1">Render Source</div>
                                        <div className="text-[10px] text-slate-600">{turnDebug.render_source}</div>
                                    </div>
                                )}
                                {turnDebug?.ai_usage && (
                                    <div className="rounded-xl border border-[var(--color-cyan-main)]/10 bg-white p-2">
                                        <div className="font-black text-[10px] uppercase tracking-wider text-[var(--color-cyan-main)] mb-1">AI Usage</div>
                                        <div className="text-[10px] text-slate-600">
                                            model {turnDebug.ai_usage?.model || '-'}
                                        </div>
                                        <div className="text-[10px] text-slate-600">
                                            tokens p/c/t {turnDebug.ai_usage?.prompt_tokens ?? '-'} / {turnDebug.ai_usage?.completion_tokens ?? '-'} / {turnDebug.ai_usage?.total_tokens ?? '-'}
                                        </div>
                                    </div>
                                )}
                                {turnDebug?.state_delta && (
                                    <div className="rounded-xl border border-[var(--color-cyan-main)]/10 bg-white p-2">
                                        <div className="font-black text-[10px] uppercase tracking-wider text-[var(--color-cyan-main)] mb-1">State Delta</div>
                                        <div className="text-[10px] text-slate-600">
                                            day {turnDebug.state_delta?.time?.day_from ?? '-'} → {turnDebug.state_delta?.time?.day_to ?? '-'}
                                            {" / "}
                                            week {turnDebug.state_delta?.time?.week_from ?? '-'} → {turnDebug.state_delta?.time?.week_to ?? '-'}
                                        </div>
                                        <div className="text-[10px] text-slate-600">
                                            dorm mood Δ {turnDebug.state_delta?.dorm_mood_delta ?? 0}
                                        </div>
                                    </div>
                                )}
                                {Array.isArray(active_roommates) && active_roommates.length > 0 && (
                                    <div className="rounded-xl border border-[var(--color-cyan-main)]/10 bg-white p-2">
                                        <div className="font-black text-[10px] uppercase tracking-wider text-[var(--color-cyan-main)] mb-1">Roommates</div>
                                        <div className="flex flex-wrap gap-1.5">
                                            {active_roommates.map((name) => (
                                                <span
                                                    key={name}
                                                    className="px-2 py-0.5 rounded-full bg-[var(--color-cyan-light)] text-[var(--color-cyan-dark)] text-[10px] font-black border border-[var(--color-cyan-main)]/20"
                                                >
                                                    {name}
                                                </span>
                                            ))}
                                        </div>
                                    </div>
                                )}
                                {(systemState?.time || systemDailyPlan || systemKeyResolution) && (
                                    <div className="rounded-xl border border-[var(--color-cyan-main)]/10 bg-white p-2 space-y-1.5">
                                        <div className="font-black text-[10px] uppercase tracking-wider text-[var(--color-cyan-main)] mb-1">System Loop</div>
                                        {systemState?.time && (
                                            <div className="text-[10px] text-slate-600">
                                                day {systemState.time?.day || 1} / week {systemState.time?.week || 1} / chapter {systemState.time?.chapter || 1}
                                            </div>
                                        )}
                                        {systemDailyPlan && (
                                            <div className="text-[10px] text-slate-600">
                                                daily {Array.isArray(systemDailyPlan?.daily_events) ? systemDailyPlan.daily_events.length : 0}
                                                {" / "}
                                                key {systemDailyPlan?.key_event ? 'pending' : (systemDailyPlan?.key_event_resolved ? 'resolved' : 'none')}
                                            </div>
                                        )}
                                        {systemDailyPlan?.key_event?.source && (
                                            <div className="text-[10px] text-slate-500">
                                                source {systemDailyPlan.key_event.source}
                                            </div>
                                        )}
                                        {systemDailyPlan?.key_event?.trigger_debug && (
                                            <div className="text-[10px] text-slate-500">
                                                trigger {systemDailyPlan.key_event.trigger_debug?.hit ? 'hit' : 'miss'}
                                            </div>
                                        )}
                                        {systemDailyPlan?.key_event?.meta && (
                                            <div className="text-[10px] text-slate-500">
                                                {systemDailyPlan?.key_event?.meta?.kind ? `kind ${systemDailyPlan.key_event.meta.kind}` : 'kind -'}
                                                {" / "}
                                                {systemDailyPlan?.key_event?.meta?.initiator ? `from ${systemDailyPlan.key_event.meta.initiator}` : 'from -'}
                                            </div>
                                        )}
                                        {systemDailyPlan?.debug && (
                                            <div className="text-[10px] text-slate-500">
                                                pool d{systemDailyPlan.debug?.daily_pool_size ?? 0} / k{systemDailyPlan.debug?.key_pool_size ?? 0}
                                                {" · "}
                                                roll {systemDailyPlan.debug?.key_roll ?? "-"}
                                                {" · "}
                                                p {systemDailyPlan.debug?.key_trigger_probability ?? 0}
                                            </div>
                                        )}
                                        {systemKeyResolution?.ok && (
                                            <div className="text-[10px] text-emerald-700">
                                                key settled: {systemKeyResolution?.event_id} / {systemKeyResolution?.choice_id}
                                            </div>
                                        )}
                                        {systemKeyResolution?.ok && (systemKeyResolution?.is_irreversible || systemKeyResolution?.has_stage_transition) && (
                                            <div className="text-[10px] text-amber-700">
                                                {systemKeyResolution?.is_irreversible ? 'irreversible ' : ''}
                                                {systemKeyResolution?.has_stage_transition ? 'stage-shift' : ''}
                                            </div>
                                        )}
                                    </div>
                                )}
                                {weeklySummary && (
                                    <div className="rounded-xl border border-amber-200/80 bg-amber-50 p-2 space-y-1">
                                        <div className="font-black text-[10px] uppercase tracking-wider text-amber-700">{weeklySummary?.title || 'Weekly Summary'}</div>
                                        {Array.isArray(weeklySummary?.highlights) && weeklySummary.highlights.slice(0, 3).map((item: any, idx: number) => (
                                            <div key={idx} className="text-[10px] text-amber-800">
                                                - {String(item || '')}
                                            </div>
                                        ))}
                                    </div>
                                )}
                            </div>
                        )}
                    </div>
                </div>
            )}
            {!!narrativeState && (relationItems.length > 0 || longTermMilestones.length > 0) && (
                <div
                    ref={relationPanelRef}
                    className="absolute z-30 w-[340px] max-w-[calc(100%-16px)]"
                    style={{
                        left: panelPos.relation.x,
                        top: panelPos.relation.y,
                        visibility: panelPosReady ? 'visible' : 'hidden',
                    }}
                >
                    <div className="rounded-2xl border border-[var(--color-cyan-main)]/20 bg-white/90 backdrop-blur-md shadow-lg overflow-hidden">
                        <div className="flex items-center bg-[var(--color-cyan-light)]/40 hover:bg-[var(--color-cyan-light)]/60 transition">
                            <button
                                type="button"
                                onClick={() => setShowRelationPanel((v) => !v)}
                                className="flex-1 px-3 py-2 text-left text-[10px] font-black tracking-widest uppercase text-[var(--color-cyan-main)]"
                            >
                                关系追踪 {showRelationPanel ? '▲' : '▼'}
                            </button>
                            <button
                                type="button"
                                onPointerDown={(ev) => handlePanelDragStart('relation', ev)}
                                className={`px-2.5 py-2 text-[11px] font-black text-[var(--color-cyan-main)]/80 hover:text-[var(--color-cyan-main)] ${draggingPanel === 'relation' ? 'cursor-grabbing' : 'cursor-grab'}`}
                                title="拖拽面板"
                                aria-label="拖拽关系追踪面板"
                            >
                                ⠿
                            </button>
                        </div>
                        {showRelationPanel && (
                            <div className="p-3 space-y-2 text-[11px] text-[var(--color-cyan-dark)]">
                                {relationItems.length > 0 && (
                                    <div className="rounded-xl border border-[var(--color-cyan-main)]/10 bg-white p-2">
                                        <div className="font-black text-[10px] uppercase tracking-wider text-[var(--color-cyan-main)] mb-1">Roommates</div>
                                        <div className="space-y-1.5">
                                            {relationItems.map(([name, rel]: any) => (
                                                <div key={name} className="text-[11px]">
                                                    <div className="flex items-center justify-between">
                                                        <span className="font-black text-slate-700">{name}</span>
                                                        <span className="text-[10px] px-2 py-0.5 rounded-full bg-[var(--color-cyan-light)] text-[var(--color-cyan-main)] font-black">
                                                            {rel?.relationship_stage || '熟悉'}
                                                        </span>
                                                    </div>
                                                    <div className="text-[10px] text-slate-500">
                                                        信任 {Math.round(Number(rel?.trust || 0))} / 紧张 {Math.round(Number(rel?.tension || 0))} / 亲密 {Math.round(Number(rel?.intimacy || 0))}
                                                    </div>
                                                </div>
                                            ))}
                                        </div>
                                    </div>
                                )}
                                {longTermMilestones.length > 0 && (
                                    <div className="rounded-xl border border-[var(--color-cyan-main)]/10 bg-white p-2">
                                        <div className="font-black text-[10px] uppercase tracking-wider text-[var(--color-cyan-main)] mb-1">Milestones</div>
                                        <div className="space-y-1">
                                            {longTermMilestones.map((item, idx) => (
                                                <div key={idx} className="text-[10px] text-slate-600 leading-relaxed">- {item}</div>
                                            ))}
                                        </div>
                                    </div>
                                )}
                            </div>
                        )}
                    </div>
                </div>
            )}
            
            <ScenePortraits charactersInScene={determineCharactersInScene()} />

            <HistoryPanel 
                history={history} 
                showHistory={showHistory} 
                setShowHistory={setShowHistory} 
                historyScrollRef={historyScrollRef} 
                parseMarktext={parseMarktext} 
            />

            <GameUIControls 
                onTogglePhone={togglePhone} 
                onSaveGame={() => {
                    const slot = prompt('请输入保存槽位 (1-3):', '1');
                    if (slot && ['1', '2', '3'].includes(slot)) {
                        saveGame(parseInt(slot));
                        alert(`进度已保存至槽位 ${slot}`);
                    }
                }} 
                onShowHistory={() => setShowHistory(true)} 
                onBackToMenu={async () => {
                    setShowBackConfirm(true);
                }}
                wechatNotificationCount={wechatNotifications?.length || 0} 
                phoneSystemEnabled={phoneSystemEnabled}
            />

            <div className="absolute inset-0 pointer-events-none flex flex-col justify-end z-20">
                {!isTyping && !isLoading && isDialogFinished && (!isEnd || nextOptions.some((opt) => isTransitionChoice(opt))) && (
                    <ActionOptions 
                        options={nextOptions} 
                        onSelect={performTurn} 
                        onHover={prefetch}
                        disabled={isLoading || isTyping} 
                    />
                )}

                {isEnd && !nextOptions.some((opt) => isTransitionChoice(opt)) && <EndOverlay isLoading={isLoading} onRestart={() => startGame()} />}

                <DialogBox 
                    typedText={typedText}
                    isTyping={isTyping}
                    isLoading={isLoading}
                    isDialogFinished={isDialogFinished}
                    onTextClick={handleTextClick}
                    scrollRef={scrollRef}
                    parseMarktext={parseMarktext}
                    speakerName={currentSpeaker}
                    pendingChoice={pendingChoice}
                />
            </div>

            <ConfirmDialog
                open={showBackConfirm}
                title="返回主菜单"
                message="当前未保存进度将丢失，确认返回吗？"
                confirmText="确认返回"
                cancelText="继续游戏"
                danger
                onCancel={() => setShowBackConfirm(false)}
                onConfirm={async () => {
                    setShowBackConfirm(false);
                    await resetGame();
                    setPhase('title');
                }}
            />
        </div>
    );
};
