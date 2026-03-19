import { useEffect, useRef, useState } from 'react';
import { useGameStore } from '../store/gameStore';
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
import { ConfirmDialog } from './common/ConfirmDialog';

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
        typewriterSpeed,
        saveGame,
        loadSave,
        prefetch,
        pendingChoice,
        current_evt_id,
        current_scene,
        resetGame
    } = useGameStore();

    const scrollRef = useRef<HTMLDivElement>(null);
    const historyScrollRef = useRef<HTMLDivElement>(null);

    const [typedText, setTypedText] = useState('');
    const [isTyping, setIsTyping] = useState(false);
    const [showHistory, setShowHistory] = useState(false);
    const [showSceneTransition, setShowSceneTransition] = useState(false);
    const [showBackConfirm, setShowBackConfirm] = useState(false);
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
        if (isLoading && (pendingChoice === "继续剧情..." || isEnd)) {
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

    if (phase === 'title') {
        return <TitleMenu onStart={() => setPhase('save_select')} onWorkshop={() => onTabChange('workshop')} onEditor={() => onTabChange('editor')} onSettings={() => onTabChange('settings')} />;
    }

    if (phase === 'save_select') {
        return <SaveSelection onBack={() => setPhase('title')} onNewGame={() => setPhase('setup')} onLoadGame={loadSave} />;
    }

    if (phase === 'setup') {
        return <GameSetup onBack={() => setPhase('save_select')} onStartGame={startGame} onTabChange={onTabChange} />;
    }

    const determineCharactersInScene = () => {
        if (!displayText) return [];
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
            { id: '安然', names: ['陆陈安然', '安然', '陆陈'] },
        ];

        let presentChars: any[] = [];
        for (const c of portraitMapping) {
            let isPresent = false;
            let isSpeaking = false;
            let highestMentionIdx = -1;
            for (const name of c.names) {
                const dialogIdx = Math.max(recentContext.lastIndexOf(`${name}：`), recentContext.lastIndexOf(`${name}:`));
                if (dialogIdx > -1) { isPresent = true; isSpeaking = true; highestMentionIdx = Math.max(highestMentionIdx, dialogIdx); }
                const sceneIdx = sceneContext.lastIndexOf(name);
                if (sceneIdx > -1) { isPresent = true; highestMentionIdx = Math.max(highestMentionIdx, sceneIdx); }
            }
            if (isPresent) {
                // If this character is the current speaker, force isSpeaking to true
                if (currentSpeaker && c.names.includes(currentSpeaker)) {
                    isSpeaking = true;
                }
                presentChars.push({ id: c.id, isSpeaking, lastMentionIdx: highestMentionIdx });
            }
        }

        const actualSpeaker = [...presentChars].filter(c => c.isSpeaking).sort((a, b) => b.lastMentionIdx - a.lastMentionIdx)[0];
        if (actualSpeaker) presentChars.forEach(c => { if (c.id !== actualSpeaker.id) c.isSpeaking = false; });
        return presentChars.sort((a, b) => b.lastMentionIdx - a.lastMentionIdx).slice(0, 3);
    };

    const parseMarktext = (text: string) => {
        const parts = text.split(/\*\*/g);
        return parts.map((part, i) => (i % 2 === 1 ? <strong key={i} className="font-black drop-shadow-sm font-bold tracking-widest">{part}</strong> : <span key={i}>{part}</span>));
    };

    const getSceneBackground = (scene?: string) => {
        const normalized = (scene || '').trim();
        if (normalized.includes('宿舍') || normalized.includes('寝室')) return '/assets/backgrounds/宿舍.jpg';
        if (normalized.includes('教室')) return '/assets/backgrounds/教室.jpg';
        if (normalized.includes('图书馆')) return '/assets/backgrounds/图书馆.jpg';
        if (normalized.includes('食堂')) return '/assets/backgrounds/食堂.jpg';
        if (normalized.includes('商业街')) return '/assets/backgrounds/商业街.jpg';
        if (normalized.includes('办公室')) return '/assets/backgrounds/办公室.jpg';
        if (normalized.includes('未知')) return '/assets/backgrounds/未知.jpg';
        return '/assets/backgrounds/宿舍.jpg';
    };

    return (
        <div className="flex-1 flex flex-col h-full rounded-2xl border-2 border-[var(--color-cyan-main)]/20 shadow-xl overflow-hidden relative bg-black">
            <div className="absolute inset-0 bg-cover bg-center opacity-70" style={{ backgroundImage: `url('${getSceneBackground(current_scene)}')` }} />
            <div
                className={`absolute inset-0 z-40 pointer-events-none transition-opacity duration-500 ${
                    showSceneTransition ? 'opacity-100' : 'opacity-0'
                }`}
            >
                <div className="absolute inset-0 bg-black/95" />
            </div>

            <AttributeNotifications notifications={notifications} />
            
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
            />

            <div className="absolute inset-0 pointer-events-none flex flex-col justify-end z-20">
                {!isTyping && !isLoading && isDialogFinished && (!isEnd || nextOptions.includes("继续剧情...")) && (
                    <ActionOptions 
                        options={nextOptions} 
                        onSelect={performTurn} 
                        onHover={prefetch}
                        disabled={isLoading || isTyping} 
                    />
                )}

                {isEnd && !nextOptions.includes("继续剧情...") && <EndOverlay isLoading={isLoading} onRestart={() => startGame()} />}

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
