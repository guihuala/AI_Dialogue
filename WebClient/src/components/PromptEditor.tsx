import { useState, useEffect, useMemo } from 'react';
import { Globe, Users, ScrollText, Layers, Terminal, Sparkles } from 'lucide-react';
import { gameApi } from '../api/gameApi';

import { EditorHeader } from './editor/EditorHeader';
import { EditorSidebar } from './editor/EditorSidebar';
import { CharacterEditor } from './editor/CharacterEditor';
import { EventEditor } from './editor/EventEditor';
import { CodeWorkspace } from './editor/CodeWorkspace';
import { EditorModals } from './editor/EditorModals';

import { Category } from './editor/types';

export const PromptEditor = () => {
    const [activeCategory, setActiveCategory] = useState<Category>('char');
    const [files, setFiles] = useState<{ md: string[], csv: string[] }>({ md: [], csv: [] });
    const [selectedFile, setSelectedFile] = useState<{ type: 'md' | 'csv', name: string } | null>(null);
    const [fileContent, setFileContent] = useState('');
    const [editMode, setEditMode] = useState<'visual' | 'code'>('visual');
    const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
    const [showExplorer, setShowExplorer] = useState(true);
    const [contextMenu, setContextMenu] = useState<{ x: number, y: number } | null>(null);

    const [message, setMessage] = useState('');
    const [isLoading, setIsLoading] = useState(false);
    const [isSaving, setIsSaving] = useState(false);
    const [showPublishModal, setShowPublishModal] = useState(false);
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
        type: 'char' | 'event',
        name: string,
        archetype?: string,
        description: string
    } | null>(null);

    const fetchFiles = async () => {
        try {
            const res = await gameApi.getAdminFiles();
            if (res.status === 'success') {
                setFiles({ md: res.md || [], csv: res.csv || [] });
                if (activeCategory === 'char' && !selectedFile) {
                    const roster = res.md.find((f: string) => f.endsWith('roster.json'));
                    if (roster) {
                        setSelectedFile({ type: 'md', name: roster });
                        setShowExplorer(false);
                    }
                }
            }
        } catch (e) {
            setMessage('无法获取文件列表');
        }
    };

    useEffect(() => {
        if (activeCategory === 'char') {
            const roster = files.md.find(f => f.endsWith('roster.json'));
            if (roster) {
                setSelectedFile({ type: 'md', name: roster });
                setShowExplorer(false);
                setEditMode('visual');
            }
        } else {
            setShowExplorer(true);
        }
    }, [activeCategory, files.md]);

    useEffect(() => {
        fetchFiles();
    }, []);

    useEffect(() => {
        if (!selectedFile) return;
        const loadContent = async () => {
            setIsLoading(true);
            setFileContent('Loading...');
            try {
                const res = await gameApi.getAdminFile(selectedFile.type, selectedFile.name);
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

    const handleSave = async (contentToSave = fileContent) => {
        if (!selectedFile) return;
        setIsSaving(true);
        try {
            await gameApi.saveAdminFile(selectedFile.type, selectedFile.name, contentToSave);
            setMessage('同步成功');
            setFileContent(contentToSave);
        } catch (e) {
            setMessage('保存失败!');
        } finally {
            setIsSaving(false);
            setTimeout(() => setMessage(''), 3000);
        }
    };

    const categories = [
        { id: 'world', name: '世界设定', icon: Globe },
        { id: 'char', name: '角色管理', icon: Users },
        { id: 'event', name: '剧情编排', icon: ScrollText },
        { id: 'skills', name: '系统逻辑', icon: Layers },
        { id: 'all', name: '底层文件', icon: Terminal },
    ];

    const parsedRoster = useMemo(() => {
        if (selectedFile?.name.endsWith('roster.json')) {
            try { return JSON.parse(fileContent); } catch (e) { return null; }
        }
        return null;
    }, [fileContent, selectedFile]);

    const updateRosterItem = (id: string, field: string, value: any) => {
        if (!parsedRoster) return;
        const newRoster = { ...parsedRoster, [id]: { ...parsedRoster[id], [field]: value } };
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
            await gameApi.saveAdminFile('md', fileName, `# ${data.name}\n\n## 身份标签\n${data.archetype}\n\n## 背景设定\n${data.description}\n\n## 性格特征\n请输入性格特征...\n\n## 行为准则\n请输入行为准则...`);
            const newRoster = {
                ...parsedRoster,
                [id]: {
                    name: data.name,
                    avatar: "/assets/portraits/default.webp",
                    archetype: data.archetype,
                    tags: ["待补完"],
                    description: data.description.slice(0, 50) + "...",
                    file: fileName
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
        if (selectedFile?.type === 'csv' || selectedFile?.name.endsWith('.csv')) {
            const lines = fileContent.split('\n').filter(l => l.trim());
            if (lines.length === 0) return { headers: [], rows: [] };
            const headers = lines[0].split(',');
            const rows = lines.slice(1).map(line => {
                const values = line.split(',');
                const row: Record<string, string> = {};
                headers.forEach((h, i) => row[h] = values[i] || '');
                return row;
            });
            return { headers, rows };
        }
        return null;
    }, [fileContent, selectedFile]);

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
        const newRows = parsedCsv.rows.filter((_, i) => i !== index);
        saveCsv(parsedCsv.headers, newRows);
        setDeleteConfirm(null);
    };

    const saveCsv = (headers: string[], rows: Record<string, string>[]) => {
        const csvContent = [
            headers.join(','),
            ...rows.map(r => headers.map(h => r[h] || '').join(','))
        ].join('\n');
        handleSave(csvContent);
    };

    const editCharacterSettings = (char: any) => {
        if (!char.file) {
            setMessage('此角色未关联设定文件');
            return;
        }
        const fileName = char.file.startsWith('characters/') ? char.file : `characters/${char.file}`;
        const mdFile = files.md.find(f => f === fileName || f.endsWith(fileName));
        if (mdFile) {
            setSelectedFile({ type: 'md', name: mdFile });
            setEditMode('code');
            setShowExplorer(true);
        } else {
            setMessage(`未找到文件: ${fileName}`);
        }
    };

    return (
        <div
            onContextMenu={(e) => { e.preventDefault(); setContextMenu({ x: e.clientX, y: e.clientY }); }}
            className="flex-1 flex flex-col h-full bg-[var(--color-cyan-light)]/40 backdrop-blur-3xl rounded-3xl border border-white/50 shadow-2xl animate-fade-in relative transition-all duration-700 overflow-hidden"
        >
            {/* Context Menu */}
            {contextMenu && (
                <div
                    className="fixed z-[1000] bg-white/95 backdrop-blur-md border-2 border-[var(--color-cyan-main)]/30 rounded-2xl shadow-2xl p-2 w-56 animate-in zoom-in-95 duration-150"
                    style={{ top: contextMenu.y, left: contextMenu.x }}
                    onClick={() => setContextMenu(null)}
                >
                    <div className="flex flex-col space-y-1">
                        <div className="px-3 py-1.5 text-[10px] font-black text-[var(--color-cyan-main)] uppercase tracking-[0.2em]">编辑器功能</div>
                        <button
                            onClick={() => handleSave()}
                            className="flex items-center px-3 py-2 text-xs font-black text-[var(--color-cyan-dark)] hover:bg-[var(--color-cyan-main)] hover:text-white rounded-xl transition-colors"
                        >
                            <span className="mr-3">💾</span> 保存当前修改
                        </button>
                        <button
                            onClick={() => fetchFiles()}
                            className="flex items-center px-3 py-2 text-xs font-black text-[var(--color-cyan-dark)] hover:bg-[var(--color-cyan-main)] hover:text-white rounded-xl transition-colors"
                        >
                            <span className="mr-3">🔄</span> 刷新资源列表
                        </button>
                        <button
                            onClick={() => setEditMode(editMode === 'visual' ? 'code' : 'visual')}
                            className="flex items-center px-3 py-2 text-xs font-black text-[var(--color-cyan-dark)] hover:bg-[var(--color-cyan-main)] hover:text-white rounded-xl transition-colors"
                        >
                            <span className="mr-3">💻</span> 切换编辑模式
                        </button>

                        <div className="h-px bg-[var(--color-cyan-main)]/10 my-2 mx-2" />
                        <div className="px-3 py-1.5 text-[10px] font-black text-[var(--color-cyan-main)] uppercase tracking-[0.2em]">游戏快捷操作</div>

                        <button
                            onClick={() => window.dispatchEvent(new CustomEvent('changeTab', { detail: 'game' }))}
                            className="flex items-center px-3 py-2 text-xs font-black text-[var(--color-cyan-dark)] hover:bg-[var(--color-cyan-main)] hover:text-white rounded-xl transition-colors"
                        >
                            <span className="mr-3">🌍</span> 返回游戏对局
                        </button>
                        <button
                            onClick={() => setShowPublishModal(true)}
                            className="flex items-center px-3 py-2 text-xs font-black text-[var(--color-cyan-dark)] hover:bg-[var(--color-cyan-main)] hover:text-white rounded-xl transition-colors"
                        >
                            <span className="mr-3">☁️</span> 发布此模组
                        </button>
                    </div>
                </div>
            )}
            <EditorHeader
                sidebarCollapsed={sidebarCollapsed}
                setSidebarCollapsed={setSidebarCollapsed}
                selectedFile={selectedFile}
                editMode={editMode}
                setEditMode={setEditMode}
                isSaving={isSaving}
                onSave={() => handleSave()}
                onPublish={() => setShowPublishModal(true)}
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
                    {message && (
                        <div className="fixed top-24 right-10 z-[100] animate-fade-in-up">
                            <div className="bg-[var(--color-cyan-dark)]/90 backdrop-blur-xl text-white px-8 py-5 rounded-[2rem] border border-white/20 shadow-2xl shadow-cyan-900/40 flex items-center">
                                <div className="w-2 h-2 rounded-full bg-[var(--color-yellow-main)] mr-4 animate-pulse shadow-[0_0_10px_var(--color-yellow-main)]" />
                                <span className="text-xs font-black uppercase tracking-widest">{message}</span>
                            </div>
                        </div>
                    )}

                    {!selectedFile ? (
                        <div className="flex-1 flex flex-col items-center justify-center opacity-10">
                            <Sparkles size={80} className="text-slate-300 mb-6" />
                            <p className="text-xl font-black text-[var(--color-cyan-main)] uppercase tracking-widest">请选择操作节点</p>
                        </div>
                    ) : (
                        <div className="flex-1 flex flex-col bg-white rounded-2xl shadow-sm border border-[var(--color-cyan-main)]/10 overflow-hidden relative group transition-all">
                            {activeCategory === 'char' && selectedFile?.name.endsWith('roster.json') && editMode === 'visual' ? (
                                <CharacterEditor
                                    parsedRoster={parsedRoster}
                                    onUpdateItem={updateRosterItem}
                                    onUploadAvatar={handleAvatarUpload}
                                    onEditSettings={editCharacterSettings}
                                    onAddNew={() => setNewItemModal({ type: 'char', name: '', archetype: '', description: '' })}
                                    onDelete={(id, name) => setDeleteConfirm({ type: 'char', id, name })}
                                />
                            ) : activeCategory === 'event' && selectedFile?.type === 'csv' && editMode === 'visual' ? (
                                <EventEditor
                                    parsedCsv={parsedCsv}
                                    onUpdateRow={updateCsvRow}
                                    onAddNew={() => setNewItemModal({ type: 'event', name: '', description: '' })}
                                    onDeleteRow={(idx, name) => setDeleteConfirm({ type: 'csv-row', id: `${idx}`, index: idx, name })}
                                />
                            ) : (
                                <CodeWorkspace
                                    selectedFile={selectedFile}
                                    fileContent={fileContent}
                                    setFileContent={setFileContent}
                                    isLoading={isLoading}
                                />
                            )}
                        </div>
                    )}
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
                onRemoveRosterItem={removeRosterItem}
                onRemoveCsvRow={removeCsvRow}
                parsedCsvHeaders={parsedCsv?.headers || []}
            />
        </div>
    );
};
