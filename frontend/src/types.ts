export interface Player {
  player_id: number;
  name: string;
  race: string;
  result: "win" | "loss" | "tie" | "unknown";
  win_probability: number | null;
}

export interface ReplayCounts {
  unit_events: number;
  economy_events: number;
  game_events: number;
  timeline_samples: number;
  build_order_entries: number;
  feature_rows: number;
}

export interface ReplaySummary {
  replay_id: string;
  filename: string;
  created_at: string;
  map_name: string;
  map_reference: {
    region: string;
    archive_type: string;
    content_hash: string;
  } | null;
  base_build: number;
  elapsed_game_loops: number;
  duration_seconds: number;
  players: Player[];
  counts: ReplayCounts;
}

export interface UnitPosition {
  x: number;
  y: number;
}

export interface UnitState {
  unit_tag: number;
  unit_type: string;
  player_id: number | null;
  position: UnitPosition | null;
  completed: boolean;
}

export interface PlayerSnapshot {
  player_id: number;
  minerals: number;
  vespene: number;
  supply_used: number;
  supply_cap: number;
  army_supply: number;
  workers: number;
  units: UnitState[];
}

export interface FrameSnapshot {
  game_loop: number;
  game_time_seconds: number;
  players: PlayerSnapshot[];
}

export interface TimelineResponse {
  replay_id: string;
  samples: FrameSnapshot[];
}

export interface BuildOrderEntry {
  player_id: number;
  game_loop: number;
  game_time_seconds: number;
  supply: number | null;
  item_name: string;
  category: "worker" | "structure" | "unit" | "upgrade";
  action: string;
}

export interface BuildOrderResponse {
  replay_id: string;
  entries: BuildOrderEntry[];
}
