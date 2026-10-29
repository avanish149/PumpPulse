# Functional verification - 29 October 2026

## Findings

The reported uncertainty screenshot is reproducible and mathematically consistent with its saved configuration. The run used a 3,600 Wp array, controller efficiency 0.50, a 36,000 L/day target, intake depth 21.305 m and the conceptual 2,200 W submersible. The default controller efficiency is 0.95, but saved runs retain their own settings.

All 30 original scenario traces were independently replayed. For every policy and scenario, water, stress and low-water risk matched the saved output. The four policy trajectories also matched each other in speed, flow, submergence, water and stress. Delivery ranged from 30,624.79 to 32,845.55 L, below target throughout. Low-water risk was zero. Peak available power across these scenarios was 1,437.22 W, below the 2,200 W full-speed requirement; the highest used speed was 70%. The policy rules therefore converged under this power-limited, adequately submerged configuration. No qualified winner is the correct result.

The Run all policies button was creating and saving experiments, but left the user on the configuration page. Its completion message was above the form, outside the viewport when clicking the bottom button. This made a successful run appear ineffective.

## Corrections

- Run all policies now shows a busy label and local status beside the button, then opens the new policy comparison. Map quick-run continues to open the simulation.
- Fields and Run/Open controls stay disabled until saved-link initialization completes. This fixes a startup race that could otherwise submit defaults before the linked configuration finished loading. Browser verification restored the saved 0.50 controller efficiency and 21.305 m intake before accepting a new run.
- Native input validation and backend configuration errors are shown beside the run button. Invalid advanced fields are exposed.
- Uncertainty results show the saved model, array, controller efficiency, target and intake depth.
- No-winner explanations distinguish demand failure from low-water risk. Each policy has failure counts and a delivered-water range.
- Every individual scenario outcome can be inspected. A qualified winner is never invented when requirements are unmet.
- Existing saved uncertainty results gain explanatory diagnostics when retrieved, without rewriting their simulated values or stored experiment.

## Controlled cases

Inputs are the unchanged Bengaluru and solar datasets. The following are one-day tests on 1 January 2025, well 010203, with the default conceptual model and other defaults unless overridden. These use automatic intake for the selected one-day replay; the exact screenshot replay above uses its saved 21.305 m intake. Results can differ with period and installation because state and automatic intake depend on the selected replay.

| Case | Verified response |
|---|---|
| Defaults | P0: 40,204 L; P1: 37,239 L; P2: 28,923 L; P3: 36,373 L. Policies differ. P0 incurs 3.5 low-water-risk hours; protected policies have zero. |
| Controller efficiency 0.50 | P0 delivery falls to 32,537 L. All 10 sampled scenarios lack a qualified winner. |
| Target 1,000 L/day | P3 delivers about 1,200 L and stops; P3 wins all 10 sampled scenarios. Half-hour control can overshoot the exact target. |
| Target 200,000 L/day | All 10 sampled scenarios lack a qualified winner. |
| Array 400 Wp | P0 delivers about 13,405 L; all policies coincide under the restricted power. |
| Array 6,000 Wp | P0 delivers about 48,220 L; protected policies constrain risk. P3 wins 6/10 sampled scenarios. |
| Pipe diameter 0.01 m | P0 delivery falls to about 6,244 L because friction restricts flow. |
| Schedule 19:00-24:00 | Zero water and zero electrical energy on the tested date. |
| Borewell model | P0 delivers about 28,320 L; catalogue limits change the result. |

Uncertainty cases use seed 42, sunlight +/-15%, groundwater +/-1 m and stress coefficients +/-30%. Results describe sampled assumptions, not confidence levels or field safety.

## Interface and API verification

- Overview: actual saved-run totals and history retrieval.
- India Atlas: India/Bengaluru views, zoom, ID search, marker selection and station coverage. Draft selection remains distinct from the loaded experiment.
- Pump & Setup: seven-model catalogue, native invalid efficiency rejection, backend intake rejection, successful run, new experiment ID and automatic comparison navigation.
- Simulation: 19:00 OFF state, midday operating values, policy changes, shared engineering readings and recommended-trace replay.
- Policies & Schedule: four distinct baseline outputs, generated 24-hour plan and shared 3D playback.
- Results & Validation: 48-row ledger, exact screenshot failure reproduction, demand/risk counts, all 120 outcome rows for 30 scenarios, and qualified winners under low demand.
- Reports: five experiment export links, source hashes, saved-run retrieval; HTTP checks parse and verify CSV/JSON output and persisted planner/uncertainty results.

29 automated tests pass, including three new tests covering exact screenshot reproduction, achievable-demand winners and separate demand/risk failure classification. HTTP checks and browser workflows pass.

## Remaining scope

This verifies software behavior within the stated model. Manufacturer pump curves, drawdown calibration and stress/life relationships remain assumptions. No physical pump, live sensor, forecast service or vibration classifier has been validated. Passing tests do not establish field accuracy or universal feasibility.
