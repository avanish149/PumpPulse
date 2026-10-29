# PumpPulse local project

Start **start.cmd**, then open **http://127.0.0.1:8765/**. Keep the server terminal open; Ctrl+C stops it. The repository launcher uses the root .venv environment when available, otherwise the Python launcher. Alternatively install requirements.txt into a separate Python environment and run python server.py. Use --port 8766 to change the port.

## Unified original application

The main application is driven by one saved backend experiment. It combines:

- All 36 Bengaluru well IDs, date coverage and observed-anchor counts.
- Four operating policies, daily delivery, energy, relative stress and shortfall exports.
- Date/time selection, half-hour slider, playback and policy switching.
- A dataset-linked 3D pump with external, X-ray, exploded, orbit, zoom and component inspection. If WebGL is unavailable, the well section remains usable.
- An aligned well section, modelled operating values and a half-hour ledger. Ledger selections update the timeline; selecting a date on the daily chart updates the same replay state.
- Seeded, paired uncertainty experiments for a selected day, with feasibility and win frequencies.
- Persistent experiment storage and CSV/JSON exports. URL experiment links reopen saved runs; optional date, time and policy parameters select a timeline step.

The seven original conceptual pump designs are now available to the backend, including the default 3 HP submersible. None have manufacturer-verified curves. Select a model in Shared experiment settings or Pump Model Explorer. Surface designs enforce the assumed suction-lift limit. The local Three.js library was reused from the supplied HTML; no external CDN is required. Geometry is conceptual.

Both **/** and **/demo** serve the same integrated dashboard. All original sidebar pages share the backend experiment and timeline; no embedded dashboard or separate client-side simulator is loaded.

## Data and source assumptions

Reads these included files from the repository root (or PUMPPULSE_DATA_DIR):

- bengaluru_urban_groundwater_hourly_interpolated.csv
- POWER_Point_Hourly_20240101_20251201_013d01N_077d62E_LST.csv

Set PUMPPULSE_DATA_DIR to another directory before startup if needed. Restart to load source changes. Simulation runs locally. The repository includes the project source datasets; SHA-256 hashes are saved with experiments.

Groundwater timestamps are assumed IST and positive values are provisionally interpreted as metres below ground. Confirm these source conventions before field conclusions. Hourly source statuses are preserved; half-hour groundwater values are interpolated only between adjacent supplied hours. Upstream hourly reconstructions may contain long original measurement gaps, which this loader cannot audit without original readings. Interpolated-only stations are labelled.

NASA POWER longitude 77.617 belongs to the UTC+5 LST swath. Solar labels shift +30 minutes to IST. Hourly Wh/m2 divided by one hour gives mean W/m2; each value is held for two half-hour bins, assuming labels mark interval beginnings. Horizontal irradiance is a regional proxy for array-plane irradiance. Date coverage, missing/invalid values and extrapolation are checked. Runs are limited to 90 complete days.

Reference: https://power.larc.nasa.gov/docs/services/api/temporal/hourly/

## Model

Pump: 2,200 W input ceiling, nominal flow bound 100 L/min, maximum 150 L/min, assumed maximum head 110 m, supported speed fractions 0, 0.4, 0.7 and 1. Default array 3,600 Wp; target 36,000 L/day; motor/hydraulic efficiency 85%/60%; pipe diameter 50 mm, length 60 m, Darcy factor 0.025; drawdown baseline 2 m; minimum submergence 5 m. All configuration values are exported.

Automatic intake is maximum groundwater depth over the selected replay plus 10.5 m. This chooses a hypothetical installation with hindsight. Enter a fixed measured intake depth when available. The pump stays fixed in the visual; the water level moves.

Hydraulic power is rho*g*Q*H. Total head includes dataset depth, baseline and additional drawdown, and Darcy-Weisbach pipe loss. Binary flow search enforces available energy and a speed-scaled maximum-head limit. Additional drawdown follows dr_next = dr*0.8^0.5 + 6*speed*(1-0.8^0.5) per half-hour. It persists across midnight; every requested replay starts at rest. Relative stress includes speed-cubed and low-water rate terms, integrated over the step, plus a per-start term.

### Policies

P0 requests full operation in the chosen schedule. P1 additionally stops at the minimum-submergence threshold. P2 requests 70% above minimum + 1 m, 40% above minimum, otherwise OFF. These three original policies do not stop at the water target.

P3 uses remaining daily demand and remaining scheduled hours, with a 40% planning reserve. It selects the lowest currently feasible supported speed that meets this rate, otherwise the highest feasible speed. It protects minimum submergence and stops after reaching the target. Demand resets at midnight; physical drawdown state does not. It uses no future sunlight records. It can oversupply by its final half-hour step. This is a hand-written feedback rule, not a proven optimum or trained AI.

### Uncertainty experiments

Select a saved replay day. Each isolated day starts at rest. All four policies share each scenario's groundwater shift and sunlight multiplier. Speed, low-water and start coefficients are independently perturbed. A fixed seed reproduces the sampled scenarios. Feasibility requires 100% of the daily target and zero low-water-risk hours. The feasible policy with least relative stress wins; exact ties use policy ID. Cases with no feasible policy are counted explicitly.

The uniform ranges are assumed, not calibrated distributions. Frequencies describe tested scenarios; they are not confidence intervals, real failure probabilities or safety certificates. Isolated-day results should not be presented as a full-season validation. Trials, source hashes, settings and method are saved to SQLite and downloadable as JSON.

## API

- GET /api/health, /api/stations, /api/config
- POST /api/simulations with station_id, start, end and optional config object
- GET /api/experiments (latest 50), /api/experiments/{id}
- GET /api/experiments/{id}/{summary,daily,half_hourly,inputs}.csv
- GET /api/experiments/{id}/state?timestamp=2025-01-01T19%3A00&policy=P3
- POST /api/robustness with experiment_id, date, scenarios, seed, solar_pct, groundwater_m, wear_pct
- GET /api/robustness/{id}

Dates are inclusive. Timestamp steps are exactly 00 or 30 minutes; timezone-naive timestamp queries mean IST. Invalid requests return 422. Server binds to 127.0.0.1, checks local Host/Origin, and permits at most two concurrent calculations. It is a local development server with no accounts or public deployment setup.

Old three-policy saved runs remain readable; run a new experiment to include P3. Historical saved numbers are not silently recomputed.

## Architecture and verification

server.py: HTTP and local static serving. data.py: source validation and alignment. engine.py: pump dynamics and four policies. service.py: validation, aggregation, persistence and exact-time lookup. robustness.py: paired uncertainty trials and storage. static/: connected UI, shared timeline, 3D twin and legacy copy. experiments.sqlite3: locally saved runs.

Run python -m unittest test_backend test_unified_frontend -v for model regression, time alignment, energy limits, validation, target stopping, daily reset, no future-solar dependence, reproducible uncertainty and persistence. Run python test_http.py with the server running for HTTP and export checks. Browser verification covers timeline/3D synchronisation, view modes, uncertainty execution and old-run compatibility.

## Remaining validation

A documented manufacturer curve and installation geometry, confirmed groundwater datum/timezone, independently checked flow/power and calibrated drawdown are still needed. Stress coefficients require condition data before being interpreted as damage or life. The current results support reproducible model comparisons, not actual pump-life extension or field control certification.

## Hour-by-hour recommendations

The recommendation panel automatically plans the selected replay day when a saved experiment opens. Change the timeline day and click Recommend for selected day to update it. The table shows one decision per hour, separate speeds for :00 and :30, expected delivery, depth, minimum submergence and reasons.

This is historical look-ahead planning: known future sunlight within the recorded day is used to compare four rest-of-day rollouts. Each candidate starts from the same current state. Execute the next hour and replan, preserving drawdown, previous speed, starts and delivered water across policy switches. Feasibility requires the full water target with zero modelled low-water-risk hours. Among feasible rollouts choose least remaining stress; if none qualify, prioritise protection then shortfall. Stop after reaching demand. It is a heuristic, not a proven global optimum or a future weather forecast.

Each day begins with the saved P3 midnight state (P1 for old three-policy experiments), or at rest at the experiment start. A recommendation for another day is therefore a separate day plan, not a stitched multi-day strategy. JSON includes this initial state, all 24 decisions, four alternatives per decision and the executed 48-step trajectory.

POST /api/recommendations with experiment_id and date. GET /api/recommendations/{id} returns the saved plan. GET /api/recommendations/{id}/schedule.csv exports the hourly table.

## Fully unified version 1.0

All original sidebar pages share the backend experiment; no iframe or old demo simulator is loaded. GET /api/models supplies the original seven conceptual models; model_id selects one in simulation config. GET /api/capabilities explicitly reports absent sensors/forecast/bearing data. GET /api/fleet supplies actual stations and latest saved experiments. Recommended schedule can drive the original twin and ledger. See INTEGRATION.md.
