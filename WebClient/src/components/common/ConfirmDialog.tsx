import { AlertTriangle } from 'lucide-react';

interface ConfirmDialogProps {
  open: boolean;
  title: string;
  message: string;
  confirmText?: string;
  cancelText?: string;
  danger?: boolean;
  onConfirm: () => void;
  onCancel: () => void;
}

export const ConfirmDialog = ({
  open,
  title,
  message,
  confirmText = '确认',
  cancelText = '取消',
  danger = false,
  onConfirm,
  onCancel
}: ConfirmDialogProps) => {
  if (!open) return null;

  return (
    <div className="fixed inset-0 z-[1500] bg-black/60 backdrop-blur-sm flex items-center justify-center p-6">
      <div className="w-full max-w-lg bg-white rounded-3xl border-2 border-[var(--color-cyan-main)]/20 shadow-2xl p-6">
        <div className="flex items-start space-x-4">
          <div className={`p-3 rounded-2xl ${danger ? 'bg-red-100 text-red-500' : 'bg-[var(--color-cyan-light)] text-[var(--color-cyan-main)]'}`}>
            <AlertTriangle size={20} />
          </div>
          <div className="flex-1 min-w-0">
            <h3 className="text-lg font-black text-[var(--color-cyan-dark)]">{title}</h3>
            <p className="mt-2 text-sm font-bold text-[var(--color-cyan-dark)]/70 whitespace-pre-wrap leading-relaxed">
              {message}
            </p>
          </div>
        </div>

        <div className="mt-6 flex justify-end space-x-3">
          <button
            onClick={onCancel}
            className="px-5 py-2.5 rounded-xl border-2 border-[var(--color-cyan-main)]/20 text-[var(--color-cyan-main)] bg-white hover:bg-[var(--color-cyan-light)] font-black text-xs uppercase tracking-widest transition-all"
          >
            {cancelText}
          </button>
          <button
            onClick={onConfirm}
            className={`px-5 py-2.5 rounded-xl text-white font-black text-xs uppercase tracking-widest transition-all ${
              danger
                ? 'bg-red-500 hover:bg-red-600'
                : 'bg-[var(--color-cyan-main)] hover:bg-[var(--color-cyan-dark)]'
            }`}
          >
            {confirmText}
          </button>
        </div>
      </div>
    </div>
  );
};
