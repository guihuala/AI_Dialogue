interface Notification {
  msg: string;
  id: number;
}

interface AttributeNotificationsProps {
  notifications: Notification[];
}

export const AttributeNotifications = ({ notifications }: AttributeNotificationsProps) => {
  return (
    <div className="absolute top-20 left-10 z-[60] flex flex-col space-y-3 pointer-events-none">
      {notifications.map(n => (
        <div 
          key={n.id} 
          className="animate-in slide-in-from-left-8 fade-in duration-500 bg-white/95 backdrop-blur-md border border-[var(--color-yellow-main)]/30 px-6 py-3 rounded-full shadow-[0_10px_30px_-5px_var(--color-yellow-main)] flex items-center"
        >
          <span className="w-2 h-2 rounded-full bg-[var(--color-yellow-main)] mr-3 animate-ping" />
          <span className="font-black text-[var(--color-cyan-dark)] text-sm tracking-widest">{n.msg}</span>
        </div>
      ))}
    </div>
  );
};
