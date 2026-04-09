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
    <div className="flex-1 p-8 overflow-y-auto custom-scrollbar flex flex-col">
      <div className="flex flex-col md:flex-row md:items-end justify-between gap-4 mb-8">
        <div>
          <h3 className="text-sm font-black text-[var(--color-cyan-main)] flex items-center mb-2">
            <UserCheck size={14} className="mr-2" /> 选定舍友
          </h3>
          <p className="text-2xl font-black text-[var(--color-cyan-dark)] tracking-tight">
            404 寝室需要 <span className="text-[var(--color-cyan-main)]">3</span> 位性格迥异的舍友
          </p>
        </div>
        <div className="text-right">
          <div className="text-3xl font-black text-[var(--color-cyan-dark)]">{selectedRoommates.length}<span className="text-[var(--color-cyan-main)]/30">/3</span></div>
          <div className="mt-1 text-sm text-[var(--color-cyan-dark)]/50">已选择</div>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 mb-12">
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
