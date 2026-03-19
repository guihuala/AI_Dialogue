interface ActionOptionsProps {
  options: string[];
  onSelect: (option: string) => void;
  onHover?: (option: string) => void;
  disabled: boolean;
}

export const ActionOptions = ({ options, onSelect, onHover, disabled }: ActionOptionsProps) => {
  if (options.length === 0) return null;

  return (
    <div className="absolute left-10 bottom-[28vh] w-96 flex flex-col space-y-4 pointer-events-auto z-30">
      {options.map((opt, idx) => (
        <button
          key={idx}
          disabled={disabled}
          onClick={() => onSelect(opt)}
          onMouseEnter={() => !disabled && onHover && onHover(opt)}
          className="p-4 bg-white/95 backdrop-blur-xl border-2 border-[var(--color-cyan-main)]/30 rounded-2xl shadow-2xl hover:border-[var(--color-yellow-main)] hover:bg-white hover:-translate-x-2 transition-all duration-300 disabled:opacity-50 font-black text-[var(--color-cyan-dark)] flex items-center group relative overflow-hidden text-left active:scale-95"
        >
          <div className="absolute inset-0 bg-gradient-to-r from-[var(--color-cyan-light)]/0 via-[var(--color-cyan-light)]/50 to-[var(--color-cyan-light)]/0 -translate-x-full group-hover:translate-x-full transition-transform duration-1000" />
          <div className="w-10 h-10 rounded-xl bg-[var(--color-cyan-light)] text-[var(--color-cyan-dark)] flex items-center justify-center text-sm font-black mr-4 group-hover:bg-[var(--color-yellow-main)] transition-all shrink-0 border border-[var(--color-cyan-main)]/20 shadow-sm">
            {String.fromCharCode(65 + idx)}
          </div>
          <span className="leading-snug text-sm relative z-10">{opt}</span>
        </button>
      ))}
    </div>
  );
};
