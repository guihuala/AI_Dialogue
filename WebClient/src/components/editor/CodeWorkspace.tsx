import { FileText, Database } from 'lucide-react';

interface CodeWorkspaceProps {
    selectedFile: { type: 'md' | 'csv', name: string } | null;
    fileContent: string;
    setFileContent: (content: string) => void;
    isLoading: boolean;
}

export const CodeWorkspace = ({
    selectedFile,
    fileContent,
    setFileContent,
    isLoading
}: CodeWorkspaceProps) => {
    return (
        <div className="flex-1 flex flex-col h-full overflow-hidden">
            <div className="px-8 py-6 border-b border-slate-50 flex items-center justify-between shrink-0 bg-slate-50/20">
                <div className="flex items-center overflow-hidden">
                    <div className="w-10 h-10 rounded-xl bg-white border border-slate-100 flex items-center justify-center mr-4 text-slate-300 shrink-0 shadow-sm">
                        {selectedFile?.type === 'md' ? <FileText size={18} /> : <Database size={18} />}
                    </div>
                    <div className="flex-1 min-w-0">
                        <h4 className="text-base font-black text-[var(--color-cyan-dark)] truncate tracking-tight">{selectedFile?.name}</h4>
                        <p className="text-[10px] font-black text-slate-400 uppercase tracking-widest mt-0.5 whitespace-nowrap overflow-hidden opacity-60">物理链接 // 节点编辑模式</p>
                    </div>
                </div>
                {isLoading && (
                    <span className="text-[8px] font-black text-[var(--color-cyan-main)] animate-pulse px-3 py-1.5 bg-cyan-50 rounded-full uppercase tracking-widest border border-cyan-100">
                        正在同步...
                    </span>
                )}
            </div>

            <textarea
                value={fileContent}
                onChange={(e) => setFileContent(e.target.value)}
                disabled={isLoading}
                spellCheck={false}
                className="flex-1 w-full p-10 font-mono text-sm leading-8 text-[var(--color-cyan-dark)] outline-none resize-none bg-transparent custom-scrollbar transition-opacity duration-300"
                style={{
                    whiteSpace: selectedFile?.type === 'csv' || selectedFile?.name.endsWith('.json') ? 'pre' : 'pre-wrap',
                    opacity: isLoading ? 0.3 : 1
                }}
                placeholder="输入源代码或文本指令..."
            />

            <div className="px-8 py-4 border-t border-slate-50 text-[10px] font-black text-slate-300 uppercase tracking-widest items-center justify-between flex bg-slate-50/30">
                <div className="flex items-center space-x-10">
                    <span className="flex items-center"><div className="w-2.5 h-2.5 mr-3 rounded-full bg-[var(--color-cyan-main)]" /> 安全同步</span>
                    <span>体积: {fileContent.length} 字节</span>
                    <span>类型: {selectedFile?.type.toUpperCase()}</span>
                </div>
                <span>物理原始数据</span>
            </div>
        </div>
    );
};
