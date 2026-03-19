interface CharacterInScene {
  id: string;
  isSpeaking: boolean;
  lastMentionIdx: number;
}

interface ScenePortraitsProps {
  charactersInScene: CharacterInScene[];
}

export const ScenePortraits = ({ charactersInScene }: ScenePortraitsProps) => {
  return (
    <div className="absolute inset-0 flex items-end justify-center pointer-events-none z-10 overflow-hidden pb-[15vh] px-10">
      {charactersInScene.length > 0 && charactersInScene.map((char, index) => {
        const count = charactersInScene.length;

        let positionClass = "left-1/2 -translate-x-1/2";
        if (count === 2) {
          positionClass = index === 0 ? "left-[35%] -translate-x-1/2" : "right-[35%] translate-x-1/2";
        } else if (count === 3) {
          if (index === 0) positionClass = "left-[20%] -translate-x-1/2";
          else if (index === 1) positionClass = "left-1/2 -translate-x-1/2";
          else positionClass = "right-[20%] translate-x-1/2";
        }

        return (
          <div key={char.id} className={`absolute bottom-0 ${positionClass} transition-all duration-700 ease-in-out`}>
            <img
              src={`/assets/portraits/${char.id}.webp`}
              alt={char.id}
              className={`max-h-[105vh] max-w-none w-auto transform transition-all duration-700 origin-bottom object-contain ${
                char.isSpeaking || charactersInScene.length === 1
                ? 'scale-95 drop-shadow-[0_0_30px_rgba(255,255,255,0.2)] translate-y-24 z-20 brightness-110 blur-none'
                : 'scale-[0.85] opacity-60 translate-y-36 z-10 brightness-50 blur-[2px]'
              }`}
              style={{ height: 'auto' }}
            />
          </div>
        );
      })}
    </div>
  );
};
