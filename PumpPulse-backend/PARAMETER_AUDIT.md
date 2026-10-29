# PumpPulse parameter audit — 29 October 2026

26 automated tests pass, plus HTTP checks and browser exercises. This verifies software behavior and arithmetic within the conceptual model; it does not validate the assumptions against a physical pump.

## All 18 editable numeric simulation parameters

Each field was checked at both permitted bounds, with invalid types/non-finite/out-of-range values rejected. A targeted low/high comparison demonstrates a response below. The example is a single affected half-hour record; it is not a whole-run total. Scenarios use a three-day Bengaluru replay, with suitable installation settings for the parameter under test.

| Parameter | Allowed range | Exercised values | Affected output | Example low → high |
|---|---|---|---|---|
| `array_Wp` | 400–20000 | 800 / 6000 | `energy_kWh` | 0 → 0.3773 (P0, 08:00) |
| `daily_target_L` | 100–200000 | 1000 / 36000 | `water_L` | 0 → 2100 (P3, 08:30) |
| `drawdown_m` | 0–40 | 0 / 5 | `head_m` | 8.557 → 13.557 (P0, 00:00) |
| `intake_depth_m` | 1–500 | 80 / 100 | `submergence_m` | 69.443 → 89.443 (P0, 00:00) |
| `min_submergence_m` | 0.1–30 | 1 / 8 | `water_L` | 2100 → 0 (P1, 09:30) |
| `pipe_diameter_m` | 0.01–0.2 | 0.02 / 0.1 | `water_L` | 755.686 → 1200 (P0, 08:00) |
| `pipe_length_m` | 1–1000 | 10 / 600 | `water_L` | 1200 → 1091.78 (P0, 08:00) |
| `darcy_factor` | 0.008–0.08 | 0.008 / 0.08 | `water_L` | 1200 → 1181.11 (P0, 08:00) |
| `motor_eff` | 0.1–0.98 | 0.2 / 0.95 | `water_L` | 291.935 → 1200 (P0, 08:00) |
| `hydraulic_eff` | 0.1–0.9 | 0.15 / 0.85 | `water_L` | 310.142 → 1200 (P0, 08:00) |
| `temperature_retention` | 0.4–1 | 0.4 / 1 | `energy_kWh` | 0.0704 → 0.3773 (P0, 08:30) |
| `controller_eff` | 0.5–1 | 0.5 / 1 | `energy_kWh` | 0.0704 → 0.3773 (P0, 08:30) |
| `wiring_retention` | 0.5–1 | 0.5 / 1 | `energy_kWh` | 0.0704 → 0.3773 (P0, 08:30) |
| `speed_wear` | 0.01–5 | 0.1 / 2 | `speed_wear_u` | 0.0032 → 0.064 (P0, 08:00) |
| `dry_wear` | 0.01–10 | 0.1 / 5 | `dry_wear_u` | 0.035 → 1.75 (P0, 09:30) |
| `start_wear` | 0.01–5 | 0.1 / 2 | `start_wear_u` | 0.1 → 2 (P0, 08:00) |
| `start_hour` | 0–23 | 6 / 12 | `water_L` | 1200 → 0 (P0, 07:30) |
| `end_hour` | 1–24 | 12 / 20 | `water_L` | 0 → 3000 (P0, 12:00) |

An increased minimum submergence may reduce pumping or reject an inadequate installation. A changed intake depth changes immersion/protection; it does not add lift to the water surface. Daily target directly controls P3 and shortfall reporting; P0–P2 intentionally ignore delivery demand. Stress coefficients change their corresponding stress terms and can affect planner rankings; they do not directly change baseline P0–P3 speeds. Low-water stress is zero until a running pump is below the configured minimum, and start stress is charged only on off-to-running transitions. Array and retention changes need not change flow while the same supported speed remains selected.

## Dataset, model and timeline selectors

| Parameter or control | Result |
|---|---|
| Station ID | All 36 source wells inspected; 35 simulate complete days. 010317 has only six hourly records, so replay selection is disabled with an explanation. IDs preserve leading zeros. |
| Start/end dates | Change input interval and row count; invalid/incomplete/out-of-coverage ranges and periods over 90 days are rejected. Direct well selection clamps draft dates to complete-day coverage. |
| Pump model | All seven models checked for all four policies using a controlled shallow/high-sun fixture. Five submerged designs also run against actual source data; surface designs correctly reject excessive suction lift. |
| Intake automatic mode | Blank/null chooses maximum replay depth + 10.5 m. It uses historical hindsight, not a measured installation. |
| Replay date/time | Selected row matches the source depth. Exact :00/:30 steps only; 19:00 is OFF for the tested daytime window and :15 is rejected. |
| Replay policy | P0/P1/P2/P3 update twin, engineering and ledger from the same saved trajectory. |
| Recommended schedule | Uses the planner's executed trace across switches, including cumulative water and drawdown. |
| Slider / previous / next / playback rate | Change record position or wall-clock playback rate only, not simulation equations. Playback advances records; changing pages stops playback. |
| 3D external / X-ray / exploded / reset / section | Display controls operate on the shared timestep. Geometry/animation remain conceptual. |
| Saved experiment / fleet open | Retrieve saved configuration and outputs. Fleet opens by experiment ID even when outside the latest-50 dropdown. Saved results are not silently recalculated. |

Browser round-trip: every editable simulation setting was filled with non-default values, submitted, and verified against the persisted backend configuration. Saved-link reload restored the model/settings. Date clamping, policy/time controls, playback, views, recommendations and uncertainty were exercised in the UI. HTTP checks verify all four CSV exports, full experiment retrieval, plan CSV/JSON and uncertainty persistence.

## Uncertainty parameters

| Field | Valid range | Verification |
|---|---|---|
| Scenarios | 10–100 whole numbers | Controls trial count; invalid counts rejected. |
| Seed | 0–2147483647 whole numbers | Repeated seeds reproduce trials; changed seeds change nonzero perturbations. |
| Sunlight ±% | 0–50 | Changes solar multiplier; zero produces none. |
| Groundwater ±m | 0–4 | Changes input depths; ranges crossing ground level rejected. |
| Stress coefficients ±% | 0–50 | Changes sampled coefficient multipliers; zero produces none. |

## Fixed model specifications and reported outputs

Rated power, maximum head, nominal flow, maximum flow, voltage, current limit, nominal/minimum RPM and supported speed levels are fixed by the catalogue/default model, not editable mechanical inputs. Their limits were exercised independently. Voltage × current is an electrical ceiling, not a simulated voltage/current waveform. The current ceilings and maximum-flow ceilings do not normally bind with the supplied nominal ratings; they are not evidence of manufacturer calibration. Nominal head in catalogue metadata is descriptive and is not used as a fitted head–flow curve. Model name/type/source/geometry are metadata or presentation choices; type additionally selects suction/geometry rules.

Independent arithmetic checks cover available solar power, electrical/hydraulic power bounds, friction head, flow-to-half-hour litres, kWh, pumping depth/submergence, all three stress terms, starts, daily sums and shortfall. Source timestamps/provenance and SHA-256 hashes are retained. Relative stress has arbitrary units and is not remaining bearing or pump life.

## Issues corrected during this audit

- P2 now uses full speed with its extra submergence guard on fixed-speed pumps, rather than remaining permanently off because 70% is unsupported.
- All policies stop delivering water and drawing modelled motor power when the intake is uncovered.
- Incomplete well 010317 is explicitly unavailable; complete-day date bounds are used and draft dates follow well changes.
- Catalogue loading completes before running/opening saved-link experiments.
- Fleet opening no longer depends on an experiment being present in the latest-50 selector.
- HTTP tests create their own known-date experiment and do not execute during unit-test discovery.

## Deliberate limits

Live sensor monitoring, future weather forecasts and bearing vibration/fault/life analysis are unavailable. Other regions remain disconnected. Supported speed levels, pump specifications, submergence/suction thresholds, drawdown response and stress coefficients are assumptions. P0 can accumulate low-submergence risk while water remains above intake; this demonstrates an unprotected baseline. A 30-minute timestep can overshoot a water target before the next stop. Existing saved experiments preserve their original engine version and require a new run to apply fixes. Hourly planning uses historical look-ahead, not a proven global optimum or an operational recommendation validated in the field.
