# Technical Decisions

This document records the major implementation decisions made while building SC2 Replay Viewer. It explains why the current architecture looks the way it does, which tradeoffs were accepted, and which boundaries are intentionally temporary.

## 1. Keep replay analysis independent from ML inference

**Decision:** Replay decoding and reconstruction remain independent of model inference. The
`backend/app/ml/` package loads a separately supplied XGBoost model and metadata, and a dedicated
endpoint returns probabilities for the reconstructed timeline. Model training stays outside the viewer.

**Why:** Replay parsing and model development have different lifecycles. Keeping them separate lets the replay pipeline produce stable training and inference inputs without coupling the website to a particular model framework or model version.

**Consequence:** Inference dependencies are optional and the model is loaded once, on demand.
The UI fetches predictions separately, so model failures do not prevent replay playback. Inputs match
the export's player ordering, opening initialization, and supply-cap normalization; outcomes are
excluded. Feature recipes and order are validated against the saved model before inference.

## 2. Normalize `s2protocol` output behind an adapter

**Decision:** All raw replay decoding is contained in `S2ProtocolAdapter`. The rest of the application works with typed, normalized dataclasses rather than raw protocol dictionaries.

**Why:** StarCraft II replay data is versioned, deeply nested, and uses internal field names. Allowing those structures to leak into the analysis layer would make every feature dependent on protocol details and harder to test.

The adapter:

- selects the protocol definition that matches the replay's base build;
- decodes metadata, tracker events, and game events;
- converts bytes and encoded text into normal strings;
- translates raw events into the application's event models;
- raises a single `ReplayDecodeError` boundary for invalid or unsupported files.

**Consequence:** Supporting a new replay field normally requires changing the adapter or normalizer once instead of changing the API, analysis, and frontend independently.

## 3. Load protocol modules without the removed `imp` module

**Decision:** Protocol definitions shipped by `s2protocol` are loaded with `importlib` and cached by replay build.

**Why:** Current `s2protocol` releases still use the `imp` module in part of their loading path, but `imp` was removed from Python 3.12. The project targets Python 3.12, so relying on that path would prevent real replay decoding.

**Consequence:** The project keeps using upstream protocol definitions while owning a small compatibility layer. This workaround should be revisited if upstream provides a Python 3.12-compatible loader.

## 4. Use canonical one-based player IDs

**Decision:** A player's canonical ID is their one-based position in `m_playerList`, not the replay's working-set or lobby slot ID.

**Why:** Real replay validation showed that metadata could identify players as slots such as 11 and 12 while tracker events referred to them as players 1 and 2. Using the metadata slot directly caused otherwise valid build-order and timeline events not to match either player.

**Consequence:** Player metadata, tracker events, timeline samples, build orders, API responses, and frontend views now share the same ID domain. If team, observer, or unusual arcade replays require additional identifiers later, those identifiers should be stored separately rather than replacing the canonical analysis ID.

## 5. Reconstruct state as deterministic timeline snapshots

**Decision:** Unit and economy events are applied in game-loop order to a mutable reconstruction state, which is then copied into immutable snapshots at a configurable interval. Website uploads use one-second samples; the reusable analysis and CLI defaults remain five seconds for compact offline output.

**Why:** Replay events describe changes, while charts, minimap playback, and ML feature rows need the state of the game at a point in time. Reconstructing once creates a common source for all three consumers.

StarCraft II time is converted using 22.4 game loops per second. Unit events are applied before economy events when both occur on the same loop, and the exact final replay loop is always included even when it does not fall on a sampling boundary.

**Consequences:**

- A smaller interval provides smoother playback and denser ML rows but increases memory and response size.
- The snapshots are deterministic for the same normalized event stream and interval.
- The timeline is sampled rather than frame-perfect; consumers that need every game loop should use a separate extraction mode.

## 6. Derive army and worker values from tracker economy data

**Decision:** Economy values such as minerals, vespene, supply, army supply, and worker count come from tracker player-statistics events rather than being inferred solely from visible unit objects.

**Why:** Unit-event counting is vulnerable to morphs, temporary units, deaths, ownership changes, and incomplete visibility. Tracker statistics more closely represent the authoritative totals shown by the game and fixed the initial issue where army supply was always zero.

**Consequence:** Unit positions and unit lists are still reconstructed from unit events, while aggregate economy values use their dedicated event source. These values can therefore update at different frequencies.

## 7. Treat build order as a curated analysis view

**Decision:** Build order includes workers, meaningful units, structures, structure/unit morphs, and researched upgrades. Temporary, automatically spawned, cosmetic, and internal entities are filtered out.

**Why:** A raw tracker-event list includes Larvae, Creep Tumors, cocoons, temporary spell entities, and other implementation details that players do not normally consider part of a build order. Displaying everything made the result noisy and misleading.

Additional rules prevent duplicate entries when a started unit later emits a born event, suppress spray upgrades, humanize protocol names, and attach the nearest known supply value at or before the event.

**Consequences:**

- The filter sets are explicit and reviewable, but may need updates when new units or balance patches introduce new protocol names.
- Supply is sampled from the most recent tracker statistic and may not represent the exact fractional instant of production.
- Build-order entries are revealed according to replay time in the frontend instead of showing future actions from the start.

## 8. Use one analysis pipeline for CLI and API consumers

**Decision:** `analyze_replay` performs decoding, timeline reconstruction, build-order extraction, and feature-row extraction and returns one `ReplayAnalysis` object.

**Why:** The command-line inspector, web API, tests, and future dataset exporter should not implement subtly different analysis paths.

**Consequence:** Adding a mandatory analysis stage affects every consumer consistently. Optional or expensive outputs may eventually need lazy evaluation if replay volume grows significantly.

## 9. Keep FastAPI endpoints thin and typed

**Decision:** API routes validate transport concerns, call the shared analysis pipeline, and convert domain objects to Pydantic response schemas. Blocking replay and map work runs in a thread pool.

**Why:** Replay decoding and archive processing are synchronous and CPU/file intensive. Running them directly in an async endpoint would block the event loop. Explicit response schemas also keep the external API documented and independent from internal dataclass implementation details.

Uploaded files are streamed to a temporary file in 1 MB chunks, limited to 100 MB, and deleted after analysis.

**Consequence:** The API can remain responsive to other requests during decoding, but a production deployment may still need job queues or worker limits for high concurrency.

## 10. Use process-local storage until the persistent model is defined

**Decision:** Completed analyses are currently stored in an `InMemoryReplayStore` under generated UUIDs.

**Why:** This enabled upload, list, summary, timeline, and build-order workflows without prematurely committing to a database schema while the replay model was still changing.

**Consequences:**

- Analyses disappear when the server restarts.
- Multiple API processes do not share analyses.
- Memory usage grows with each uploaded replay.

SQLite persistence remains the next planned milestone. The store is accessed through FastAPI dependencies so it can be replaced with a SQLAlchemy implementation without rewriting route behavior.

## 11. Resolve the exact replay map by content hash

**Decision:** The decoder extracts the final `s2ma` cache handle from replay details. The map resolver downloads that exact archive from Blizzard's regional content depot and keys its cache by the archive's SHA-256 hash.

**Why:** A map name is not a stable asset identifier: different versions can share a name, names can be localized, and local map files may not exist. The replay's content-addressed reference identifies the version actually played.

Before processing an archive, the resolver verifies its downloaded SHA-256 against the replay reference and rejects archives over 100 MB.

**Consequences:**

- The first request for a map requires network access to Blizzard's depot.
- Subsequent requests reuse immutable cached assets.
- Region aliases used by older replay handles are normalized when constructing depot URLs.

## 12. Convert and cache map assets atomically

**Decision:** `Minimap.tga` is extracted from the map archive, converted to PNG with Pillow, and cached alongside parsed map bounds. Cache writes use temporary files followed by atomic replacement.

**Why:** Browsers do not reliably display TGA files, and repeatedly downloading and converting the same content-addressed map is wasteful. Atomic writes prevent interrupted requests from leaving apparently valid but partial cache entries.

**Consequence:** Cached PNG and JSON metadata are safe to serve with long-lived immutable cache headers. A corrupted metadata entry is discarded and rebuilt.

## 13. Parse playable bounds instead of estimating coordinates

**Decision:** Map width, height, and playable bounds are parsed from the versioned `MapInfo` binary structure. Unit positions are projected against those bounds.

**Why:** Estimating the coordinate range from observed units caused markers to shift and scale differently as the replay progressed, and map artwork can include non-playable borders. Authoritative bounds keep the minimap stable and align markers with the map image.

The frontend also flips the vertical axis because game coordinates increase upward while canvas pixels increase downward. If map metadata cannot be loaded, it falls back to bounds inferred from all observed unit positions.

**Consequence:** Exact alignment depends on recognizing the `MapInfo` version. Unsupported versions fail explicitly instead of silently drawing incorrect positions.

## 14. Render the minimap with Canvas

**Decision:** React owns playback state and data loading, while a Canvas component draws the map image and unit markers for the current snapshot.

**Why:** Unit markers change frequently during playback and are naturally expressed as a lightweight drawing pass. Canvas avoids creating and reconciling a large DOM tree of marker elements and makes coordinate projection explicit.

**Consequence:** Canvas content is visual rather than semantic. Any future interactive unit inspection will require hit testing and an accessible companion representation.

## 15. Keep frontend playback client-side

**Decision:** The frontend fetches the complete sampled timeline and build order after selecting a replay, then advances through snapshots locally.

**Why:** For the current single-replay workflow, local playback gives immediate scrubbing and synchronized charts, statistics, minimap markers, and build-order revelation without repeated server requests.

The build-order columns only contain events at or before the selected replay time. They retain a fixed height, hide their scrollbar visually, and automatically follow newly revealed events while respecting reduced-motion preferences.

**Consequence:** Initial timeline responses can become large for long replays or very small sample intervals. Pagination, binary transfer, or streamed playback may be necessary at dataset scale.

## 16. Keep ML handoff formats separate from application storage

**Decision:** The website keeps replay analyses only for the current process, while offline ML data is exported as Zstandard-compressed Parquet. Detailed JSON remains a single-replay debugging format and is not used as the training dataset.

**Why:** Website snapshots contain repeated unit positions and nested display data that are useful for replay playback but highly redundant for model training. Parquet provides typed columns, sparse nested unit-count maps, dictionary encoding, and column compression without forcing website persistence.

Each ML row represents both players at one five-second timestamp and includes economy values, completed and in-progress unit counts, unit modes, gameplay upgrades, the winner label, and an equal-per-match sample weight. Cosmetic unlocks are excluded, localized races are canonicalized, and opening frames are omitted until both players have authoritative economy data. Maps use their content hash as a stable identifier when available. Replay SHA-256 values provide stable match grouping so train and validation data can be split without placing states from the same match in both sets.

Dataset schema version 5 exports `supply_used`, `supply_cap`, and `army_supply` as Int32, discarding fractional tracker precision in the parser with integer division by 4096. This whole-point representation is intentional and differs from the fractional supply retained by schema version 4. The current in-game supply limit, `supply_cap`, is capped at 200; current supply used is not clamped. Uncapped `supply_capacity` fields are omitted. The export accepts any replay directory without storing a batch label in the dataset or manifest. Unit-name normalization similarly separates stable identity from temporary mode, such as `SiegeTank` plus `SiegeTank:sieged`. Exact raw-to-canonical mappings are versioned and recorded by base build in each manifest. Unknown future names are retained unchanged so cross-patch data is never lost through speculative normalization. Regenerate existing exports to adopt the integer supply schema.

**Consequence:** Model training can scale independently from the website representation. Only completed 1v1 matches with an unambiguous winner are exported; skipped files and reasons are recorded in a versioned manifest.

## Deferred decisions

The following choices are intentionally not final:

- the SQLAlchemy schema and migration strategy;
- whether raw uploaded replay files should ever be retained;
- retention and eviction policies for analyses and cached map assets;
- probability caching and model versioning beyond one local model bundle per process;
- large-scale timeline transport and background processing;
- dataset partitioning and Parquet schema evolution.

These should be decided using real replay volume and ML-consumer requirements rather than assumed in advance.
