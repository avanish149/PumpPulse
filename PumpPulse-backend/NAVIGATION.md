# PumpPulse - seven-tab guide

| Main tab | Sections and purpose |
|---|---|
| Overview | Loaded experiment, key metrics, policy summary, daily chart and saved experiments. |
| India Atlas | Map & wells: offline India map, Bengaluru zoom, well search/selection and quick run. Station details: coordinates, coverage and source information. |
| Pump & Setup | Configuration: the shared mechanical form and model specification summary. Pump models: the seven conceptual designs. |
| Simulation | Twin & timeline: shared date/time, policy, playback, 3D/well section and daily chart. Engineering readings: power, head, RPM, flow, energy and stress at that same timestep. |
| Policies & Schedule | Policy comparison: baseline P0-P3 results. Hourly schedule: historical planner, exports and replay of its executed trace. |
| Results & Validation | Water & stress ledger: half-hour rows and shared date/policy selectors. Uncertainty experiments: scenario count, seed and input/stress perturbations. |
| Reports | Saved experiments, CSV/JSON downloads, sources, hashes and model assumptions. |

Start with India Atlas, select a Bengaluru well, configure it in Pump & Setup and run all policies. Explore Simulation, compare Policies & Schedule, inspect Results & Validation and export from Reports.

The same form and saved-run selector move between their destinations without duplicating IDs or resetting values. Changing tabs does not create a new run or change the loaded experiment. Displayed results retain the saved configuration until a new run succeeds. Playback stops when navigating.

Live Monitoring and Bearing Analysis are removed from navigation: there is no physical sensor or bearing-recording connection. Fleet Intelligence is removed from the interface; its backend endpoint remains compatible. Saved runs are available from Overview and Reports. Existing links to the former page hashes still resolve to the appropriate new section.

Direct links: `#home`, `#atlas`, `#setup`, `#simulation`, `#policies`, `#results`, `#reports`. Section links include `#atlas-station`, `#setup-models`, `#simulation-engineering`, `#policies-schedule` and `#results-validation`.
