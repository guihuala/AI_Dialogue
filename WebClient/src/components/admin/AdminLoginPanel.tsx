import { Shield } from 'lucide-react';

interface AdminLoginPanelProps {
    password: string;
    authError: string | null;
    onChangePassword: (value: string) => void;
    onSubmit: (e: React.FormEvent) => void;
}

export const AdminLoginPanel = ({ password, authError, onChangePassword, onSubmit }: AdminLoginPanelProps) => {
    return (
        <div className="flex-1 flex items-center justify-center p-8">
            <div className="w-full max-w-md bg-white/90 backdrop-blur-xl p-8 rounded-[2.5rem] border-2 border-[var(--color-cyan-main)]/20 shadow-2xl animate-fade-in">
                <div className="flex flex-col items-center mb-8">
                    <div className="w-16 h-16 bg-[var(--color-cyan-main)]/10 rounded-2xl flex items-center justify-center mb-4">
                        <Shield size={32} className="text-[var(--color-cyan-main)]" />
                    </div>
                    <h2 className="text-2xl font-black text-[var(--color-cyan-dark)] uppercase tracking-widest">管理员验证</h2>
                    <p className="text-[10px] font-black text-[var(--color-cyan-main)]/60 mt-2 uppercase tracking-[0.3em]">Access Restricted</p>
                </div>

                <form onSubmit={onSubmit} className="space-y-6">
                    <div className="relative">
                        <input
                            type="password"
                            placeholder="输入管理口令..."
                            value={password}
                            onChange={(e) => onChangePassword(e.target.value)}
                            className="w-full px-6 py-4 bg-[var(--color-cyan-light)]/30 border-2 border-[var(--color-cyan-main)]/10 rounded-2xl focus:border-[var(--color-cyan-main)] focus:outline-none font-bold text-center transition-all"
                            autoFocus
                        />
                    </div>
                    <button
                        type="submit"
                        className="w-full py-4 bg-[var(--color-cyan-dark)] text-white rounded-2xl font-black uppercase tracking-[0.2em] hover:bg-[var(--color-cyan-main)] transition-all shadow-lg active:scale-[0.98]"
                    >
                        登陆
                    </button>
                    {authError && (
                        <div className="text-center text-sm font-bold text-rose-500">
                            {authError}
                        </div>
                    )}
                </form>

                <p className="mt-8 text-center text-[10px] text-slate-400 font-bold uppercase tracking-widest">
                    Unauthorized access is monitored.
                </p>
            </div>
        </div>
    );
};

