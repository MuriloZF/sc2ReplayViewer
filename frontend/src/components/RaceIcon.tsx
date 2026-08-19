import protossIcon from "../../races/protoss.png";
import terranIcon from "../../races/terran.png";
import zergIcon from "../../races/zerg.png";

const RACE_ICONS: Record<string, string> = {
  protoss: protossIcon,
  terran: terranIcon,
  zerg: zergIcon,
};

interface RaceIconProps {
  race: string;
}

export function RaceIcon({ race }: RaceIconProps) {
  const normalizedRace = race.toLowerCase();
  const source = RACE_ICONS[normalizedRace];

  if (!source) {
    return <span className="race-icon-fallback" aria-label={`${race} icon`}>?</span>;
  }

  return (
    <img
      className={`race-icon race-icon-${normalizedRace}`}
      src={source}
      alt={`${race} icon`}
    />
  );
}
