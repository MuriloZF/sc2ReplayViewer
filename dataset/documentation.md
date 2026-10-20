# Dataset Documentation

## 1. Origin

The dataset was provided by Spawning Tool and consisted of `.SC2Replay` files, which were processed by my parser. The parser successfully converted most of the replays, resulting in a dataset with 16,858 replays in a single `.parquet` file.

The exported replays contain completed 1v1 games with all three races and different maps. Player skill ratings are not included in this dataset.

## 2. Columns

The types below describe the existing `datasetSC2.parquet` file (schema version 4). Parser outputs now truncate supply to whole points using integer division of raw tracker values by 4096: for example, 61.5 becomes 61. New exports use schema version 5 and Int32 for all six supply columns. Regenerate existing exports to adopt this behavior; the current file retains its original Double supply values.

Snapshots are sampled every 5 seconds, with a final snapshot that may fall between intervals. `game_time_seconds = game_loop / 22.4`.

| Column | Meaning | Type |
|---|---|---|
| `match_id` | SHA-256 hash of the replay file | String |
| `map_name` | Map name | String |
| `map_id` | Map ID | String |
| `base_build` | Protocol base-build identifier | Int32 |
| `game_loop` | Simulation loop at the snapshot | Int64 |
| `game_time_seconds` | In-game time | Double |
| `p1_race` | Player 1 race | String |
| `p2_race` | Player 2 race | String |
| `p1_won` | Who won (from Player 1's perspective) | Boolean |
| `sample_weight` | 1 / snapshots in this replay; weights sum to approximately 1 per replay | Double |
| `p1_minerals` | Player 1 minerals | Int32 |
| `p1_vespene` | Player 1 vespene | Int32 |
| `p1_supply_used` | Player 1 supply | Double |
| `p1_supply_cap` | Player 1 supply limit | Double |
| `p1_army_supply` | Player 1 army supply | Double |
| `p1_workers` | Player 1 active worker count | Int32 |
| `p1_unit_counts` | Player 1 completed units/buildings counted by canonical type | Map<String, Int32> |
| `p1_in_progress_counts` | Player 1 unfinished units/buildings counted by canonical type | Map<String, Int32> |
| `p1_unit_modes` | Player 1 counts by mode, e.g. SiegeTank:sieged; overlaps with unit counts | Map<String, Int32> |
| `p1_upgrades` | Player 1 upgrades | List<String> |
| `p2_minerals` | Player 2 minerals | Int32 |
| `p2_vespene` | Player 2 vespene | Int32 |
| `p2_supply_used` | Player 2 supply | Double |
| `p2_supply_cap` | Player 2 supply limit | Double |
| `p2_army_supply` | Player 2 army supply | Double |
| `p2_workers` | Player 2 active worker count | Int32 |
| `p2_unit_counts` | Player 2 completed units/buildings counted by canonical type | Map<String, Int32> |
| `p2_in_progress_counts` | Player 2 unfinished units/buildings counted by canonical type | Map<String, Int32> |
| `p2_unit_modes` | Player 2 counts by mode, e.g. SiegeTank:sieged; overlaps with unit counts | Map<String, Int32> |
| `p2_upgrades` | Player 2 upgrades | List<String> |

Supply caps are limited to 200 during export; supply used is not clamped. Army supply uses the explicit tracker statistic when available, otherwise `max(supply_used - workers, 0)`.

## 3. Dataset Statistics

| Metric | Value |
|---|---:|
| Rows (snapshots) | 2,462,472 |
| Top-level columns | 30 |
| Physical Parquet fields | 36 |
| Unique replays | 16,858 |

The six map columns each store separate key and value fields, explaining the physical field count of 36. The manifest records 5,952 skipped replay files and names the output `states.parquet`; the supplied file is named `datasetSC2.parquet`.
