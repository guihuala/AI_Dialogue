import { UserCheck } from 'lucide-react';
import { CandidateCard } from './CandidateCard';

interface RoommateSelectorProps {
  candidates: any[];
  selectedRoommates: string[];
  onToggleRoommate: (id: string) => void;
}

export const RoommateSelector = ({
  candidates,
  selectedRoommates,
  onToggleRoommate
}: RoommateSelectorProps) => {
  return (
    <div className="flex-1 p-5 md:p-7 overflow-y-auto custom-scrollbar flex flex-col">
      <div className="flex flex-col md:flex-row md:items-end justify-between gap-4 mb-6">
        <div>
          <h3 className="text-sm font-black text-[var(--color-cyan-main)] flex items-center mb-2">
            <UserCheck size={14} className="mr-2" /> 选择舍友
          </h3>
        </div>
        <div className="flex items-center gap-3 rounded-full bg-white/82 border border-[var(--color-cyan-main)]/10 px-4 py-2 self-start md:self-auto">
          <div className="text-2xl font-black text-[var(--color-cyan-dark)] leading-none">{selectedRoommates.length}<span className="text-[var(--color-cyan-main)]/30">/3</span></div>
          <div className="text-xs font-black text-[var(--color-cyan-dark)]/45">已选</div>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4 md:gap-5">
        {candidates.map(char => (
          <CandidateCard 
            key={char.id} 
            char={char} 
            isSelected={selectedRoommates.includes(char.id)} 
            onToggle={onToggleRoommate} 
          />
        ))}
      </div>
    </div>
  );
};
