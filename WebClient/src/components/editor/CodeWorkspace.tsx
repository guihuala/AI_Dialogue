import { FileText, Database, ArrowLeft } from 'lucide-react';

interface CodeWorkspaceProps {
    selectedFile: { type: 'md' | 'csv', name: string } | null;
    fileContent: string;
    setFileContent: (content: string) => void;
    isLoading: boolean;
    readOnly?: boolean;
    onBack?: () => void;
}

export const CodeWorkspace = ({
    selectedFile,
    fileContent,
    setFileContent,
    isLoading,
    readOnly = false,
    onBack
}: CodeWorkspaceProps) => {
    return (
        <div className="flex-1 flex flex-col h-full overflow-hidden bg-[var(--color-warm-bg)]">
            <div className="px-8 py-6 border-b border-[var(--color-soft-border)] flex items-center justify-between shrink-0 bg-white shadow-sm">
                <div className="flex items-center overflow-hidden">
                    {onBack && (
                        <button 
                            onClick={onBack}
                            className="p-2 mr-4 hover:bg-[var(--color-cyan-light)] rounded-xl text-[var(--color-cyan-main)] transition-all border border-[var(--color-soft-border)]"
                        >
                            <ArrowLeft size={18} />
                        </button>
                    )}
                    <div className="w-10 h-10 rounded-xl bg-white border border-[var(--color-soft-border)] flex items-center justify-center mr-4 text-[var(--color-cyan-main)]/30 shrink-0 shadow-sm">
                        {selectedFile?.type === 'md' ? <FileText size={18} /> : <Database size={18} />}
                    </div>
                    <div className="flex-1 min-w-0">
                        <h4 className="text-base font-black text-[var(--color-cyan-dark)] truncate tracking-tight">{selectedFile?.name?.split('/').pop()}</h4>
                        <p className="text-[10px] font-black text-[var(--color-life-text)]/40 uppercase tracking-widest mt-0.5 whitespace-nowrap overflow-hidden">
                            底层数据 // {onBack ? '专注编辑' : '全局同步模式'}
                        </p>
                    </div>
                </div>
                {isLoading && (
                    <span className="text-[8px] font-black text-[var(--color-cyan-main)] animate-pulse px-3 py-1.5 bg-[var(--color-cyan-light)] rounded-full uppercase tracking-widest border border-[var(--color-cyan-main)]/10">
                        正在同步...
                    </span>
                )}
            </div>

            <textarea
                value={fileContent}
                onChange={(e) => setFileContent(e.target.value)}
                disabled={isLoading || readOnly}
                spellCheck={false}
                className="flex-1 w-full p-10 font-mono text-sm leading-8 text-[var(--color-cyan-dark)] outline-none resize-none bg-transparent custom-scrollbar transition-opacity duration-300"
                style={{
                    whiteSpace: selectedFile?.type === 'csv' || selectedFile?.name.endsWith('.json') ? 'pre' : 'pre-wrap',
                    opacity: isLoading ? 0.3 : 1
                }}
                placeholder={readOnly ? '默认模板为只读，请先另存为你的模组后再编辑。' : '输入源代码或文本指令...'}
            />

            <div className="px-8 py-4 border-t border-[var(--color-soft-border)] text-[10px] font-black text-[var(--color-life-text)]/30 uppercase tracking-widest items-center justify-between flex bg-white/50">
                <div className="flex items-center space-x-10 text-left">
                    <span className="flex items-center"><div className="w-2.5 h-2.5 mr-3 rounded-full bg-[var(--color-cyan-main)]" /> 安全同步</span>
                    <span>体积: {fileContent.length} 字节</span>
                    <span>类型: {selectedFile?.type.toUpperCase()}</span>
                </div>
                <span>物理原始数据</span>
            </div>
        </div>
    );
};
