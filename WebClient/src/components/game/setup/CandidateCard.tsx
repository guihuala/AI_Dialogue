import { UserCheck } from 'lucide-react';

interface CandidateCardProps {
  char: any;
  isSelected: boolean;
  onToggle: (id: string) => void;
}

export const CandidateCard = ({ char, isSelected, onToggle }: CandidateCardProps) => {
  return (
    <div
      onClick={() => onToggle(char.id)}
      className={`group rounded-[1.75rem] border cursor-pointer transition-all duration-500 relative overflow-hidden flex flex-col h-64 ${isSelected ? 'border-[var(--color-cyan-main)] bg-white shadow-[0_0_30px_rgba(0,188,212,0.12)] -translate-y-1' : 'border-[var(--color-cyan-main)]/10 bg-white/55 hover:border-[var(--color-cyan-main)]/30 hover:bg-white/70'}`}
    >
      <div className="relative flex-1 overflow-hidden bg-slate-100/50">
        <div className="absolute inset-0 bg-gradient-to-t from-black/60 via-transparent to-transparent z-10 opacity-60 group-hover:opacity-80 transition-opacity" />
        {char.avatar ? (
          <img
            src={char.avatar}
            alt={char.name}
            className={`w-full h-full object-cover transition-transform duration-700 ${isSelected ? 'scale-110' : 'group-hover:scale-105'}`}
          />
        ) : (
          <div className="w-full h-full flex items-center justify-center bg-[var(--color-cyan-light)] text-[var(--color-cyan-main)]">
            <UserCheck size={48} opacity={0.2} />
          </div>
        )}
        <div className="absolute bottom-0 left-0 right-0 p-5 z-20">
          <div className="flex flex-wrap gap-1 mb-2">
            {char.tags.map((t: string) => (
              <span key={t} className="text-[11px] bg-white/20 backdrop-blur-md text-white px-2 py-0.5 rounded-full font-black border border-white/10">{t}</span>
            ))}
          </div>
          <h4 className="text-xl font-black text-white tracking-tight drop-shadow-md">{char.name}</h4>
        </div>
        {isSelected && (
          <div className="absolute top-4 right-4 w-8 h-8 bg-[var(--color-cyan-main)] text-white rounded-full flex items-center justify-center shadow-lg border-2 border-white z-30 animate-in zoom-in-50 duration-300">
            <UserCheck size={16} />
          </div>
        )}
      </div>
      <div className="p-5 px-6 shrink-0 bg-white/88">
        <p className={`text-sm font-bold leading-relaxed line-clamp-2 transition-colors ${isSelected ? 'text-[var(--color-cyan-dark)]' : 'text-slate-500'}`}>
          {char.description}
        </p>
      </div>
    </div>
  );
};
