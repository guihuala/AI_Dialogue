import { useState, useEffect, useMemo } from 'react';
import { Save, FileText, Database, Code, RefreshCw, UploadCloud, Globe, Users, ScrollText, Layers, Terminal, Sparkles, Plus, Trash2, Eye, Layout, Edit3 } from 'lucide-react';
import { gameApi } from '../api/gameApi';

type Category = 'world' | 'char' | 'event' | 'skills' | 'all';

export const PromptEditor = () => {
  const [activeCategory, setActiveCategory] = useState<Category>('char');
  const [files, setFiles] = useState<{md: string[], csv: string[]}>({ md: [], csv: [] });
  const [selectedFile, setSelectedFile] = useState<{type: 'md' | 'csv', name: string} | null>(null);
  const [fileContent, setFileContent] = useState('');
  const [editMode, setEditMode] = useState<'visual' | 'code'>('visual');
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [showExplorer, setShowExplorer] = useState(true);
  
  const [message, setMessage] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [showPublishModal, setShowPublishModal] = useState(false);
  const [publishMetadata, setPublishMetadata] = useState({ 
    name: '我的自定义模组', 
    author: '佚名', 
    description: '包含了我修改过的世界观和角色设定。' 
  });

  // Modals for Create/Delete
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
            // Auto select roster.json if in char category and nothing selected
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
    // When switching to character category, auto-select roster and hide explorer
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

  const categorizedFiles = useMemo(() => {
    const result: Record<Category, {type: 'md' | 'csv', name: string}[]> = {
        world: [], char: [], event: [], skills: [], all: []
    };
    files.md.forEach(f => {
        const item = { type: 'md' as const, name: f };
        result.all.push(item);
        if (f.startsWith('world/') || f === 'main_system.md') result.world.push(item);
        else if (f.startsWith('characters/') || f.endsWith('roster.json')) result.char.push(item);
        else if (f.startsWith('skills/')) result.skills.push(item);
        else result.world.push(item);
    });
    files.csv.forEach(f => {
        const item = { type: 'csv' as const, name: f };
        result.all.push(item);
        result.event.push(item);
    });
    return result;
  }, [files]);

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

  // Visual Roster Editor Logic
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
      // 1. Create the .md file first
      try {
          await gameApi.saveAdminFile('md', fileName, `# ${data.name}\n\n## 身份标签\n${data.archetype}\n\n## 背景设定\n${data.description}\n\n## 性格特征\n请输入性格特征...\n\n## 行为准则\n请输入行为准则...`);
          
          // 2. Then update roster
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
          fetchFiles(); // Refresh file list to see the new .md
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

  // Visual CSV Editor Logic
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
      newRows[rowIndex] = { ...newRows[rowIndex], [field]: value.replace(/,/g, '，') }; // Avoid breaking CSV
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
    <div className="flex-1 flex flex-col h-full bg-[#f0f9ff]/40 backdrop-blur-3xl rounded-3xl border border-white/50 shadow-2xl animate-fade-in relative transition-all duration-700">
      {/* Dynamic Header */}
      <div className="flex items-center justify-between px-8 py-6 bg-white/40 border-b border-white/20 shrink-0">
        <div className="flex items-center space-x-4">
            <button 
                onClick={() => setSidebarCollapsed(!sidebarCollapsed)}
                className="w-10 h-10 rounded-xl bg-slate-100 text-slate-400 flex items-center justify-center hover:bg-slate-200 transition-colors"
                title={sidebarCollapsed ? "展开侧边栏" : "收起侧边栏"}
            >
                <Layout size={20} className={sidebarCollapsed ? "rotate-180" : ""} />
            </button>
            <div>
                <h2 className="text-xl font-black text-slate-800 tracking-tight flex items-center">
                    内容编辑器 <span className="ml-3 px-2 py-0.5 bg-slate-100 rounded-full border border-slate-200 text-[8px] text-slate-400 font-black tracking-widest">v2.1</span>
                </h2>
                <div className="flex items-center mt-1 space-x-2 text-[8px] font-black uppercase tracking-wider text-slate-400">
                    <Sparkles size={10} className="text-[var(--color-yellow-main)]" />
                    <span>内容中枢</span>
                </div>
            </div>
        </div>
        
        <div className="flex space-x-4 items-center scale-90 md:scale-100">
            {(selectedFile?.name.endsWith('json') || selectedFile?.type === 'csv') && (
                <div className="flex bg-slate-100 p-1 rounded-xl border border-slate-200 shadow-inner mr-4">
                    <button 
                        onClick={() => setEditMode('visual')}
                        className={`flex items-center px-4 py-2 rounded-lg text-[10px] font-black transition-all ${editMode === 'visual' ? 'bg-white text-[var(--color-cyan-dark)] shadow-sm' : 'text-slate-400 hover:text-slate-600'}`}
                    >
                        <Eye size={14} className="mr-2" /> 视觉引导
                    </button>
                    <button 
                        onClick={() => setEditMode('code')}
                        className={`flex items-center px-4 py-2 rounded-lg text-[10px] font-black transition-all ${editMode === 'code' ? 'bg-white text-[var(--color-cyan-dark)] shadow-sm' : 'text-slate-400 hover:text-slate-600'}`}
                    >
                        <Code size={14} className="mr-2" /> 代码注入
                    </button>
                </div>
            )}
            <button
                onClick={() => setShowPublishModal(true)}
                className="flex items-center px-8 py-4 bg-[var(--color-yellow-main)] hover:bg-[var(--color-yellow-dark)] text-slate-800 rounded-3xl font-black transition-all text-xs shadow-xl shadow-yellow-900/10 active:scale-95 group"
            >
                <UploadCloud size={20} className="mr-3 group-hover:-translate-y-1 transition-transform" /> 
                部署至工坊
            </button>
            <button
                onClick={() => handleSave()}
                disabled={isSaving || !selectedFile}
                className="flex items-center px-10 py-4 bg-slate-900 hover:bg-black text-white rounded-3xl font-black transition-all shadow-2xl shadow-slate-900/20 text-xs active:scale-95 disabled:opacity-20 flex-shrink-0"
            >
                <Save size={20} className="mr-3 text-[var(--color-cyan-main)]" /> 
                {isSaving ? '同步中...' : '提交修改'}
            </button>
        </div>
      </div>

      <div className="flex flex-1 overflow-hidden bg-white/10">
        {/* Navigation Sidebar */}
        {!sidebarCollapsed && (
            <div className="w-16 md:w-20 border-r border-white/20 flex flex-col py-6 items-center space-y-4 shrink-0 bg-white/5 transition-all animate-in slide-in-from-left fade-in">
                {categories.map(cat => (
                    <button
                        key={cat.id}
                        onClick={() => {
                            setActiveCategory(cat.id as Category);
                            setSelectedFile(null);
                        }}
                        title={cat.name}
                        className={`w-12 h-12 flex items-center justify-center rounded-2xl transition-all group relative ${activeCategory === cat.id ? 'bg-[var(--color-cyan-dark)] text-white shadow-lg shadow-cyan-900/20' : 'text-slate-400 hover:bg-white/60 hover:text-[var(--color-cyan-dark)]'}`}
                    >
                        <cat.icon size={20} className={`shrink-0 transition-transform ${activeCategory === cat.id ? 'scale-110' : 'group-hover:scale-110'}`} />
                        <div className="absolute left-full ml-4 px-3 py-1.5 bg-slate-800 text-white text-[10px] font-black rounded-lg whitespace-nowrap z-50 pointer-events-none opacity-0 group-hover:opacity-100 transition-opacity">
                            {cat.name}
                        </div>
                    </button>
                ))}

                <div className="mt-auto px-2">
                    <button 
                      onClick={fetchFiles}
                      className="w-12 h-12 flex items-center justify-center bg-white/40 border border-slate-200 rounded-2xl text-slate-300 hover:text-[var(--color-cyan-main)] hover:border-[var(--color-cyan-main)]/30 transition-all group"
                      title="刷新列表"
                    >
                        <RefreshCw size={18} className="group-hover:rotate-120 transition-transform" />
                    </button>
                </div>
            </div>
        )}

        {/* Content Explorer Sidebar */}
        {showExplorer && !sidebarCollapsed && (
            <div className="w-56 md:w-64 border-r border-white/10 flex flex-col shrink-0 bg-white/10 animate-in slide-in-from-left fade-in">
            <div className="px-6 py-8 border-b border-white/10">
                <h3 className="text-lg font-black text-slate-800 tracking-tight">资源列表</h3>
            </div>
            <div className="flex-1 overflow-y-auto custom-scrollbar p-4 space-y-1">
                {categorizedFiles[activeCategory].map(f => (
                    <div 
                        key={f.name} 
                        onClick={() => setSelectedFile(f)}
                        className={`px-4 py-3 rounded-xl flex items-center cursor-pointer transition-all border relative group ${selectedFile?.name === f.name ? 'border-[var(--color-cyan-main)]/30 bg-white shadow-md' : 'border-transparent text-slate-500 hover:bg-white/40'}`}
                    >
                        <div className="mr-3">
                            {f.type === 'md' ? <FileText size={14} className="opacity-40" /> : <Database size={14} className="opacity-40" />}
                        </div>
                        <span className="text-xs font-bold truncate">{f.name.split('/').pop()}</span>
                    </div>
                ))}
            </div>
        </div>
        )}

        {/* Main Workspace Canvas */}
        <div className="flex-1 flex flex-col bg-slate-50/20 p-6 md:p-8 overflow-hidden relative">
            {message && (
                <div className="absolute top-10 right-10 z-[100] animate-fade-in-up">
                    <div className="bg-slate-900/90 backdrop-blur-md text-white px-8 py-5 rounded-[2rem] border border-white/10 shadow-2xl shadow-slate-900/40 flex items-center">
                        <div className="w-2 h-2 rounded-full bg-[var(--color-yellow-main)] mr-4 animate-pulse shadow-[0_0_10px_var(--color-yellow-main)]" />
                        <span className="text-xs font-black uppercase tracking-widest">{message}</span>
                    </div>
                </div>
            )}

            {!selectedFile ? (
                <div className="flex-1 flex flex-col items-center justify-center opacity-10">
                    <Sparkles size={80} className="text-slate-300 mb-6" />
                    <p className="text-xl font-black text-slate-400 uppercase tracking-widest">请选择操作节点</p>
                </div>
            ) : (
                <div className="flex-1 flex flex-col bg-white rounded-2xl shadow-sm border border-slate-100 overflow-hidden relative group transition-all">
                    {/* Visual Roster Editor */}
                    {activeCategory === 'char' && selectedFile.name.endsWith('roster.json') && editMode === 'visual' ? (
                        <div className="flex-1 flex flex-col overflow-hidden">
                            <div className="px-12 py-8 border-b border-slate-50 flex items-center justify-between shrink-0 bg-slate-50/30">
                                <div>
                                    <h4 className="text-2xl font-black text-slate-800 tracking-tight">角色名册可视化管理</h4>
                                </div>
                                <button 
                                    onClick={() => setNewItemModal({ type: 'char', name: '', archetype: '', description: '' })}
                                    className="px-6 py-3 bg-[var(--color-cyan-dark)] text-white rounded-2xl font-black text-[10px] uppercase tracking-widest flex items-center hover:bg-[var(--color-cyan-main)] transition-all shadow-xl shadow-cyan-900/20"
                                >
                                    <Plus size={16} className="mr-2" /> 新增角色档案
                                </button>
                            </div>
                            <div className="flex-1 overflow-y-auto custom-scrollbar p-12">
                                <div className="grid grid-cols-1 xl:grid-cols-2 gap-8">
                                    {parsedRoster && Object.entries(parsedRoster).map(([id, char]: [string, any]) => (
                                        <div key={id} className="bg-white/50 backdrop-blur-sm rounded-[2rem] p-6 border border-slate-100 hover:border-[var(--color-cyan-main)]/30 transition-all group/card relative shadow-sm hover:shadow-xl hover:-translate-y-1">
                                            <button 
                                                onClick={() => setDeleteConfirm({ type: 'char', id, name: char.name })}
                                                className="absolute top-4 right-4 p-2.5 bg-rose-50 text-rose-400 rounded-xl opacity-0 group-hover/card:opacity-100 transition-all hover:bg-rose-100"
                                                title="删除角色"
                                            >
                                                <Trash2 size={14} />
                                            </button>
                                            
                                            <div className="flex flex-col md:flex-row gap-6">
                                                <div className="flex flex-col items-center space-y-3 shrink-0">
                                                    <div 
                                                        className="w-24 h-24 rounded-2xl overflow-hidden bg-slate-100 border-2 border-white shadow-md relative group/avatar cursor-pointer"
                                                        onClick={() => document.getElementById(`avatar-input-${id}`)?.click()}
                                                    >
                                                        <img src={char.avatar} className="w-full h-full object-cover" />
                                                        <div className="absolute inset-0 bg-black/40 flex items-center justify-center opacity-0 group-hover/avatar:opacity-100 transition-all">
                                                            <UploadCloud className="text-white" size={20} />
                                                        </div>
                                                        <input 
                                                            id={`avatar-input-${id}`}
                                                            type="file" 
                                                            className="hidden" 
                                                            accept="image/*"
                                                            onChange={(e) => {
                                                                const file = e.target.files?.[0];
                                                                if (file) handleAvatarUpload(id, file);
                                                            }}
                                                        />
                                                    </div>
                                                    <div className="px-3 py-1 bg-slate-100 rounded-lg text-[8px] font-black text-slate-400 uppercase tracking-widest">
                                                        {id.slice(0, 8)}
                                                    </div>
                                                </div>
                                                
                                                <div className="flex-1 space-y-4">
                                                    <div className="grid grid-cols-2 gap-4">
                                                        <div className="space-y-1">
                                                            <label className="text-[10px] font-bold text-slate-500 ml-1">角色姓名</label>
                                                            <input 
                                                                value={char.name} 
                                                                onChange={(e) => updateRosterItem(id, 'name', e.target.value)}
                                                                className="w-full px-4 py-2.5 bg-white/80 rounded-xl border border-slate-100 text-sm font-bold focus:ring-2 focus:ring-[var(--color-cyan-main)]/20 focus:border-[var(--color-cyan-main)] outline-none transition-all"
                                                                placeholder="例: 林飒"
                                                            />
                                                        </div>
                                                        <div className="space-y-1">
                                                            <label className="text-[10px] font-bold text-slate-500 ml-1">身份标签</label>
                                                            <input 
                                                                value={char.archetype} 
                                                                onChange={(e) => updateRosterItem(id, 'archetype', e.target.value)}
                                                                className="w-full px-4 py-2.5 bg-white/80 rounded-xl border border-slate-100 text-sm font-bold focus:ring-2 focus:ring-[var(--color-cyan-main)]/20 focus:border-[var(--color-cyan-main)] outline-none transition-all"
                                                                placeholder="例: 高冷学姐"
                                                            />
                                                        </div>
                                                    </div>
                                                    <div className="space-y-1">
                                                        <label className="text-[10px] font-bold text-slate-500 ml-1">立绘资源路径</label>
                                                        <input 
                                                            value={char.avatar} 
                                                            onChange={(e) => updateRosterItem(id, 'avatar', e.target.value)}
                                                            className="w-full px-4 py-2.5 bg-slate-50/50 rounded-xl border border-slate-100 text-[10px] font-mono focus:bg-white focus:border-[var(--color-cyan-main)] outline-none transition-all"
                                                        />
                                                    </div>
                                                    <div className="pt-4">
                                                        <button 
                                                            onClick={() => editCharacterSettings(char)}
                                                            className="w-full py-3 bg-slate-900 text-white rounded-xl font-black text-[10px] uppercase tracking-widest flex items-center justify-center hover:bg-black transition-all shadow-lg shadow-slate-900/10 active:scale-[0.98]"
                                                        >
                                                            <Edit3 size={14} className="mr-2 text-[var(--color-yellow-main)]" /> 编辑角色设定
                                                        </button>
                                                    </div>
                                                </div>
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            </div>
                        </div>
                    ) : activeCategory === 'event' && selectedFile.type === 'csv' && editMode === 'visual' ? (
                        <div className="flex-1 flex flex-col overflow-hidden">
                            <div className="px-8 py-6 border-b border-slate-50 flex items-center justify-between shrink-0 bg-slate-50/30">
                                <div>
                                    <h4 className="text-xl font-black text-slate-800 tracking-tight">剧情事件管理</h4>
                                </div>
                                <button 
                                    onClick={() => setNewItemModal({ type: 'event', name: '', description: '' })}
                                    className="px-6 py-3 bg-[var(--color-cyan-dark)] text-white rounded-xl font-black text-[10px] uppercase tracking-widest flex items-center hover:bg-[var(--color-cyan-main)] transition-all shadow-xl shadow-cyan-900/20"
                                >
                                    <Plus size={16} className="mr-2" /> 新增剧情事件
                                </button>
                            </div>
                            <div className="flex-1 overflow-y-auto custom-scrollbar p-8">
                                <div className="grid grid-cols-1 gap-6">
                                    {parsedCsv?.rows.map((row, idx) => (
                                        <div key={idx} className="bg-white/50 backdrop-blur-sm rounded-2xl p-6 border border-slate-100 hover:border-[var(--color-cyan-main)]/30 transition-all group/card relative shadow-sm hover:shadow-md">
                                            <button 
                                                onClick={() => setDeleteConfirm({ type: 'csv-row', id: `${idx}`, index: idx, name: row[parsedCsv.headers[0]] || `行 ${idx + 1}` })}
                                                className="absolute top-4 right-4 p-2 text-rose-300 hover:text-rose-500 opacity-0 group-hover/card:opacity-100 transition-all"
                                            >
                                                <Trash2 size={14} />
                                            </button>
                                            
                                            <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
                                                {parsedCsv.headers.map((h, hIdx) => (
                                                    <div key={h} className={hIdx === parsedCsv.headers.length - 1 ? "md:col-span-3 space-y-1" : "space-y-1"}>
                                                        <label className="text-[10px] font-bold text-slate-400 ml-1 uppercase">{h}</label>
                                                        <textarea 
                                                            value={row[h]}
                                                            onChange={(e) => updateCsvRow(idx, h, e.target.value)}
                                                            className="w-full px-4 py-2 bg-white/80 rounded-xl border border-slate-50 text-sm font-medium text-slate-700 focus:border-[var(--color-cyan-main)] outline-none transition-all resize-none overflow-hidden"
                                                            rows={1}
                                                            onInput={(e) => {
                                                                const target = e.target as HTMLTextAreaElement;
                                                                target.style.height = 'auto';
                                                                target.style.height = target.scrollHeight + 'px';
                                                            }}
                                                        />
                                                    </div>
                                                ))}
                                            </div>
                                        </div>
                                    ))}
                                    {parsedCsv?.rows.length === 0 && (
                                        <div className="flex flex-col items-center justify-center py-20 opacity-20">
                                            <ScrollText size={48} className="mb-4" />
                                            <p className="text-sm font-black uppercase tracking-widest">暂无事件数据</p>
                                        </div>
                                    )}
                                </div>
                            </div>
                        </div>
                    ) : (
                        /* Standard Code Editor */
                        <div className="flex-1 flex flex-col h-full overflow-hidden">
                            <div className="px-8 py-6 border-b border-slate-50 flex items-center justify-between shrink-0 bg-slate-50/20">
                                <div className="flex items-center overflow-hidden">
                                    <div className="w-10 h-10 rounded-xl bg-white border border-slate-100 flex items-center justify-center mr-4 text-slate-300 shrink-0 shadow-sm">
                                        {selectedFile.type === 'md' ? <FileText size={18} /> : <Database size={18} />}
                                    </div>
                                    <div className="flex-1 min-w-0">
                                        <h4 className="text-base font-black text-slate-800 truncate tracking-tight">{selectedFile.name}</h4>
                                        <p className="text-[10px] font-black text-slate-400 uppercase tracking-widest mt-0.5 whitespace-nowrap overflow-hidden opacity-60">物理链接 // 节点编辑模式</p>
                                    </div>
                                </div>
                                {isLoading && <span className="text-[8px] font-black text-[var(--color-cyan-main)] animate-pulse px-3 py-1.5 bg-cyan-50 rounded-full uppercase tracking-widest border border-cyan-100">正在同步...</span>}
                            </div>

                            <textarea 
                                value={fileContent}
                                onChange={(e) => setFileContent(e.target.value)}
                                disabled={isLoading}
                                spellCheck={false}
                                className="flex-1 w-full p-10 font-mono text-sm leading-8 text-slate-600 outline-none resize-none bg-transparent custom-scrollbar transition-opacity duration-300"
                                style={{ 
                                    whiteSpace: selectedFile.type === 'csv' || selectedFile.name.endsWith('.json') ? 'pre' : 'pre-wrap',
                                    opacity: isLoading ? 0.3 : 1
                                }}
                                placeholder="输入源代码或文本指令..."
                            />
                            
                            <div className="px-8 py-4 border-t border-slate-50 text-[10px] font-black text-slate-300 uppercase tracking-widest items-center justify-between flex bg-slate-50/30">
                                <div className="flex items-center space-x-10">
                                    <span className="flex items-center"><div className="w-2.5 h-2.5 mr-3 rounded-full bg-[var(--color-cyan-main)]" /> 安全同步</span>
                                    <span>体积: {fileContent.length} 字节</span>
                                    <span>类型: {selectedFile.type.toUpperCase()}</span>
                                </div>
                                <span>物理原始数据</span>
                            </div>
                        </div>
                    )}
                </div>
            )}
        </div>
      </div>

      {/* Modern Publish Modal */}
      {showPublishModal && (
          <div className="fixed inset-0 z-[500] flex items-center justify-center bg-slate-900/60 backdrop-blur-2xl animate-in fade-in duration-500 p-10">
              <div className="bg-white rounded-3xl p-12 w-full max-w-2xl shadow-2xl border border-white animate-in zoom-in-95 duration-500 relative overflow-hidden">
                  <div className="absolute top-0 left-0 w-full h-3 bg-gradient-to-r from-[var(--color-cyan-main)] via-[var(--color-yellow-main)] to-[var(--color-cyan-dark)]" />
                  
                  <div className="flex items-center mb-10">
                    <div className="w-16 h-16 rounded-2xl bg-[var(--color-cyan-light)] text-[var(--color-cyan-main)] flex items-center justify-center mr-6 shrink-0 shadow-lg border-2 border-white">
                        <UploadCloud size={36} />
                    </div>
                    <div>
                        <h3 className="text-4xl font-black text-slate-800 tracking-tighter leading-none">发布至多元宇宙</h3>
                    </div>
                  </div>
                  
                  <div className="space-y-10">
                      <div>
                          <label className="block text-[10px] font-black text-slate-400 uppercase mb-4 tracking-[0.4em] ml-2">模组别名</label>
                          <input 
                              type="text"
                              value={publishMetadata.name}
                              onChange={(e) => setPublishMetadata({...publishMetadata, name: e.target.value})}
                              className="w-full px-10 py-6 rounded-[2.5rem] border-2 border-slate-100 bg-slate-50 focus:bg-white focus:border-[var(--color-cyan-main)] outline-none font-black text-slate-800 transition-all shadow-inner text-lg"
                              placeholder="模组名称"
                          />
                      </div>
                      <div className="grid grid-cols-2 gap-8">
                        <div>
                            <label className="block text-[10px] font-black text-slate-400 uppercase mb-4 tracking-[0.4em] ml-2">总架构师</label>
                            <input 
                                type="text"
                                value={publishMetadata.author}
                                onChange={(e) => setPublishMetadata({...publishMetadata, author: e.target.value})}
                                className="w-full px-10 py-6 rounded-[2.5rem] border-2 border-slate-100 bg-slate-50 focus:bg-white focus:border-[var(--color-cyan-main)] outline-none font-black text-slate-800 transition-all shadow-inner"
                            />
                        </div>
                        <div className="flex flex-col justify-end">
                            <div className="px-10 py-6 bg-emerald-50 rounded-[2.5rem] border-2 border-dashed border-emerald-100 text-emerald-600 font-black text-[10px] tracking-widest flex items-center justify-center">
                                已验证本地权限
                            </div>
                        </div>
                      </div>
                      <div>
                          <label className="block text-[10px] font-black text-slate-400 uppercase mb-4 tracking-[0.4em] ml-2">项目概览</label>
                          <textarea 
                              value={publishMetadata.description}
                              onChange={(e) => setPublishMetadata({...publishMetadata, description: e.target.value})}
                              className="w-full px-10 py-6 rounded-[2.5rem] border-2 border-slate-100 bg-slate-50 focus:bg-white focus:border-[var(--color-cyan-main)] outline-none font-black text-slate-800 h-48 resize-none transition-all shadow-inner leading-loose text-base"
                          />
                      </div>
                  </div>

                  <div className="flex space-x-6 mt-16">
                      <button 
                         onClick={() => setShowPublishModal(false)}
                         className="flex-1 py-6 bg-slate-100 text-slate-400 rounded-[2.5rem] font-black hover:bg-slate-200 transition-all uppercase tracking-widest text-xs border border-transparent"
                      >
                          取消
                      </button>
                      <button 
                         onClick={() => {}} // Handle publish
                         className="flex-[1.5] py-6 bg-slate-900 text-white rounded-[2.5rem] font-black hover:bg-black transition-all shadow-2xl shadow-slate-900/40 uppercase tracking-widest text-xs border border-transparent"
                      >
                          确认上线
                      </button>
                  </div>
              </div>
          </div>
      )}

      {/* New Item Modal */}
      {newItemModal && (
          <div className="fixed inset-0 z-[250] flex items-center justify-center bg-slate-900/60 backdrop-blur-xl animate-in fade-in duration-300 p-6">
              <div className="bg-white rounded-[2.5rem] p-10 w-full max-w-xl shadow-2xl border border-white animate-in zoom-in-95 duration-300 relative overflow-hidden">
                  <div className="flex items-center mb-8">
                      <div className="w-14 h-14 rounded-2xl bg-[var(--color-cyan-light)] text-[var(--color-cyan-main)] flex items-center justify-center mr-5 shadow-lg">
                          <Plus size={28} />
                      </div>
                      <div>
                          <h3 className="text-2xl font-black text-slate-800 tracking-tight">
                              {newItemModal.type === 'char' ? '创建新角色档案' : '新增剧情事件项'}
                          </h3>
                          <p className="text-[10px] font-black text-slate-400 uppercase tracking-widest mt-1">创建 // 数据库记录</p>
                      </div>
                  </div>

                  <div className="space-y-6">
                      {newItemModal.type === 'char' ? (
                          <>
                              <div className="space-y-2">
                                  <label className="text-[10px] font-black text-slate-400 uppercase ml-2 tracking-widest">角色名称</label>
                                  <input 
                                      value={newItemModal.name}
                                      onChange={(e) => setNewItemModal({...newItemModal, name: e.target.value})}
                                      className="w-full px-6 py-4 rounded-2xl border-2 border-slate-100 bg-slate-50 focus:bg-white focus:border-[var(--color-cyan-main)] outline-none font-bold text-slate-700 transition-all"
                                      placeholder="输入姓名..."
                                  />
                              </div>
                              <div className="space-y-2">
                                  <label className="text-[10px] font-black text-slate-400 uppercase ml-2 tracking-widest">核心身份标签</label>
                                  <input 
                                      value={newItemModal.archetype}
                                      onChange={(e) => setNewItemModal({...newItemModal, archetype: e.target.value})}
                                      className="w-full px-6 py-4 rounded-2xl border-2 border-slate-100 bg-slate-50 focus:bg-white focus:border-[var(--color-cyan-main)] outline-none font-bold text-slate-700 transition-all"
                                      placeholder="例: 高冷学姐 / 阳光僚机 / 毒舌教授"
                                  />
                              </div>
                          </>
                      ) : (
                          <div className="space-y-4 max-h-[40vh] overflow-y-auto pr-2 custom-scrollbar">
                              {parsedCsv?.headers.map(h => (
                                  <div key={h} className="space-y-2">
                                      <label className="text-[10px] font-black text-slate-400 uppercase ml-2 tracking-widest">{h}</label>
                                      <input 
                                          onChange={(e) => {
                                              const newDesc = newItemModal.description || '{}';
                                              let data = {};
                                              try { data = JSON.parse(newDesc); } catch(e) {}
                                              // @ts-ignore
                                              data[h] = e.target.value;
                                              setNewItemModal({...newItemModal, description: JSON.stringify(data)});
                                          }}
                                          className="w-full px-6 py-4 rounded-2xl border-2 border-slate-100 bg-slate-50 focus:bg-white focus:border-[var(--color-cyan-main)] outline-none font-bold text-slate-700 transition-all"
                                          placeholder={`输入 ${h}...`}
                                      />
                                  </div>
                              ))}
                          </div>
                      )}
                      
                      <div className="space-y-2">
                          <label className="text-[10px] font-black text-slate-400 uppercase ml-2 tracking-widest">简介/备注</label>
                          <textarea 
                              value={newItemModal.type === 'char' ? newItemModal.description : ''}
                              onChange={(e) => {
                                  if (newItemModal.type === 'char') {
                                      setNewItemModal({...newItemModal, description: e.target.value});
                                  }
                              }}
                              className={`w-full px-6 py-4 rounded-2xl border-2 border-slate-100 bg-slate-50 focus:bg-white focus:border-[var(--color-cyan-main)] outline-none font-bold text-slate-700 transition-all h-32 resize-none ${newItemModal.type === 'event' ? 'hidden' : ''}`}
                              placeholder="简单描述一下..."
                          />
                      </div>
                  </div>

                  <div className="flex space-x-4 mt-10">
                      <button 
                          onClick={() => setNewItemModal(null)}
                          className="flex-1 py-4 bg-slate-100 text-slate-500 rounded-2xl font-black text-xs uppercase tracking-widest hover:bg-slate-200 transition-all"
                      >
                          丢弃
                      </button>
                      <button 
                          onClick={() => {
                              if (newItemModal.type === 'char') {
                                  addRosterItem({ name: newItemModal.name || '新角色', archetype: newItemModal.archetype || '普通人', description: newItemModal.description || '无描述' });
                              } else {
                                  let data = {};
                                  try { data = JSON.parse(newItemModal.description || '{}'); } catch(e) {}
                                  addCsvRow(data);
                              }
                          }}
                          className="flex-1 py-4 bg-slate-900 text-white rounded-2xl font-black text-xs uppercase tracking-widest hover:bg-black transition-all shadow-lg"
                      >
                          确认建立
                      </button>
                  </div>
              </div>
          </div>
      )}

      {/* Delete Confirmation Modal */}
      {deleteConfirm && (
          <div className="fixed inset-0 z-[300] flex items-center justify-center bg-slate-900/60 backdrop-blur-md animate-in fade-in duration-300 p-6">
              <div className="bg-white rounded-[2rem] p-10 w-full max-w-sm shadow-2xl border border-rose-100 animate-in zoom-in-95 duration-300 relative overflow-hidden">
                  <div className="absolute top-0 left-0 w-full h-1 bg-rose-500" />
                  <div className="flex flex-col items-center text-center">
                      <div className="w-20 h-20 rounded-full bg-rose-50 text-rose-500 flex items-center justify-center mb-6 shadow-inner">
                          <Trash2 size={40} />
                      </div>
                      <h3 className="text-xl font-black text-slate-800 tracking-tight">确认移除此档案？</h3>
                      <p className="text-sm font-medium text-slate-400 mt-2 mb-8 leading-relaxed">
                          您正在尝试移除 <span className="text-rose-500 font-black">"{deleteConfirm.name}"</span>。<br/>
                          此操作将同步至物理文件，不可撤销。
                      </p>
                      
                      <div className="flex space-x-3 w-full">
                        <button 
                            onClick={() => setDeleteConfirm(null)}
                            className="flex-1 py-4 bg-slate-50 text-slate-400 rounded-2xl font-black text-[10px] uppercase tracking-widest hover:bg-slate-100 transition-all border border-slate-100"
                        >
                            跳过且保留
                        </button>
                        <button 
                            onClick={() => {
                                if (deleteConfirm.type === 'char') removeRosterItem(deleteConfirm.id);
                                else if (deleteConfirm.index !== undefined) removeCsvRow(deleteConfirm.index);
                            }}
                            className="flex-1 py-4 bg-rose-500 text-white rounded-2xl font-black text-[10px] uppercase tracking-widest hover:bg-rose-600 transition-all shadow-lg shadow-rose-900/20"
                        >
                            确认清除
                        </button>
                      </div>
                  </div>
              </div>
          </div>
      )}
    </div>
  );
};


