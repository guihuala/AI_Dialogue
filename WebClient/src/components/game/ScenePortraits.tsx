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
        } else if (count >= 4) {
          if (index === 0) positionClass = "left-[12%] -translate-x-1/2";
          else if (index === 1) positionClass = "left-[37%] -translate-x-1/2";
          else if (index === 2) positionClass = "right-[37%] translate-x-1/2";
          else positionClass = "right-[12%] translate-x-1/2";
        }

        return (
          <div key={char.id} className={`absolute bottom-0 ${positionClass} transition-all duration-700 ease-in-out`}>
            <img
              src={`/assets/portraits/${char.id}.webp`}
              alt={char.id}
              className={`max-h-[105vh] max-w-none w-auto transform transition-all duration-700 origin-bottom object-contain ${
                char.isSpeaking || charactersInScene.length === 1
                ? 'scale-[0.87] translate-y-32 z-20 brightness-100 saturate-100 blur-none drop-shadow-[0_0_28px_rgba(255,255,255,0.28)]'
                : 'scale-[0.87] translate-y-32 z-10 brightness-[0.58] saturate-[0.8] blur-[1px]'
              }`}
              style={{ height: 'auto' }}
            />
          </div>
        );
      })}
    </div>
  );
};
