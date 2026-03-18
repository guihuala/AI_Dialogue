import { MessageCircle, Calendar, ClipboardList, GraduationCap, Wallet, Brain } from 'lucide-react';

interface AppIconProps {
  id: string;
  name: string;
  icon: any;
  color: string;
  notifications?: number;
  onClick: (id: string) => void;
}

const AppIcon = ({ id, name, icon, color, notifications, onClick }: AppIconProps) => (
  <div 
    onClick={() => onClick(id)}
    className="flex flex-col items-center gap-3 group cursor-pointer transition-all active:scale-90"
  >
    <div className={`w-[72px] h-[72px] rounded-[1.8rem] ${color} flex items-center justify-center text-white shadow-2xl relative group-hover:shadow-[0_0_30px_rgba(255,255,255,0.3)] group-hover:-translate-y-1 duration-300 overflow-hidden`}>
      <div className="absolute inset-0 bg-gradient-to-tr from-black/10 via-white/20 to-transparent opacity-50" />
      <div className="relative z-10 transition-transform group-hover:scale-110">
        {icon}
      </div>
      
      {notifications !== undefined && notifications > 0 && (
        <div className="absolute top-1 right-1 min-w-[24px] h-6 bg-rose-500 rounded-full border-[3px] border-white/20 flex items-center justify-center text-[10px] font-black text-white px-1 shadow-lg animate-in zoom-in-50 duration-300">
          {notifications}
        </div>
      )}
    </div>
    <span className="text-[11px] font-black text-white/90 tracking-tighter uppercase drop-shadow-md">{name}</span>
  </div>
);

interface HomeViewProps {
  onAppClick: (id: string) => void;
  wechatNotificationsCount: number;
}

export const HomeView = ({ onAppClick, wechatNotificationsCount }: HomeViewProps) => {
  return (
    <div className="flex-1 flex flex-col p-10 pt-28 animate-in fade-in zoom-in-95 duration-700">
      <div className="mb-14 h-40 w-full bg-white/10 backdrop-blur-xl rounded-[3rem] border border-white/10 p-8 flex flex-col justify-end">
        <div className="text-white/60 text-[10px] font-black tracking-[0.4em] uppercase mb-1">Dorm Diary OS</div>
        <div className="text-white text-3xl font-black tracking-tighter">Life. Sorted.</div>
      </div>

      <div className="grid grid-cols-3 gap-y-12 gap-x-6 justify-items-center">
        <AppIcon 
          id="wechat" 
          name="微信" 
          icon={<MessageCircle size={36} fill="white" fillOpacity={0.2} />} 
          color="bg-gradient-to-br from-emerald-400 to-emerald-600" 
          notifications={wechatNotificationsCount}
          onClick={onAppClick} 
        />
        <AppIcon 
          id="calendar" 
          name="行程" 
          icon={<Calendar size={36} />} 
          color="bg-gradient-to-br from-orange-400 to-pink-500" 
          onClick={onAppClick} 
        />
        <AppIcon 
          id="jmu" 
          name="JMU学工" 
          icon={<GraduationCap size={36} />} 
          color="bg-gradient-to-br from-blue-600 to-indigo-800" 
          onClick={onAppClick} 
        />
        <AppIcon 
          id="alipay" 
          name="支付宝" 
          icon={<Wallet size={36} />} 
          color="bg-gradient-to-br from-[#1677FF] to-blue-400" 
          onClick={onAppClick} 
        />
        <AppIcon 
          id="wellness" 
          name="身心健康" 
          icon={<Brain size={36} />} 
          color="bg-gradient-to-br from-indigo-500 to-purple-600" 
          onClick={onAppClick} 
        />
      </div>
    </div>
  );
};
