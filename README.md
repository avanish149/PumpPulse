# PumpPulse

A local, data-driven educational simulator for solar-powered irrigation pumps. Compare water delivery, electrical energy and relative operating stress using Bengaluru groundwater records and historical solar inputs.

## Features

- Python backend with validated dataset loading and half-hour timeline alignment.
- Dataset-linked 3D pump and well section with date/time playback.
- Four operating policies, including demand-aware control.
- Hour-by-hour policy recommendations with a continuous simulated pump state.
- Paired, seeded uncertainty experiments.
- Saved local experiments and CSV/JSON exports.
- Unified original dashboard: 16 pages share the backend, with seven conceptual pump models.

## Run locally

Requires Python 3.12 or later. From the repository root:

~~~sh
python -m venv .venv
~~~

Activate the environment (Windows: .venv\Scripts\activate; macOS/Linux: source .venv/bin/activate), then:

~~~sh
python -m pip install -r PumpPulse-backend/requirements.txt
python PumpPulse-backend/server.py
~~~

Open http://127.0.0.1:8765/demo#home for the integrated original dashboard. The root URL serves the same application. On Windows, after dependencies are installed, Start PumpPulse.cmd starts the backend and opens the original entry.

Select a well and dates, run all policies, and explore the timeline. The pilot request in examples/bengaluru-pilot.json reproduces the first Bengaluru study. A new SQLite database is created locally; personal saved experiments are not distributed.

## Data

The original CSV files are included beside the backend. Bengaluru groundwater and the matching NASA POWER solar file are currently connected. Other regional datasets are retained as project inputs; Nashik is excluded from the active simulation and its supplied file identifies its records as synthetic.

Groundwater timestamps are assumed IST and positive values are provisionally interpreted as depth below ground. Original observed/interpolated labels are preserved. Confirm source conventions before field conclusions. Solar local-solar-time labels are aligned to IST. Source hashes are recorded with runs.

The report PDF describes the original educational dashboard and predates the backend additions. PumpPulse-backend/README.md documents the current equations, API, policies, time alignment and model limits.

## Tests

~~~sh
cd PumpPulse-backend
python -m unittest test_backend test_unified_frontend -v
~~~

HTTP checks additionally require a running server and at least one completed experiment:

~~~sh
python test_http.py
~~~

## Interpretation

Pump specifications, drawdown response and stress coefficients are illustrative. No manufacturer-calibrated head-flow curve or field-validated pump-life model is supplied. Hourly recommendations use historical look-ahead and are not weather forecasts or proven global optima. All original navigation pages now use the unified backend. Live weather forecasts, physical sensor feeds and bearing recordings are explicitly unavailable. See [the integration map](PumpPulse-backend/INTEGRATION.md) for the page-by-page connections.

The server binds to localhost and is intended for local presentation and experimentation. It is not a public production deployment.
