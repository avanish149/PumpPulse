# Full original-dashboard backend integration

The original sidebar and the main entry now render the same application. There is no embedded second dashboard and no original client-side pump simulator loaded by either entry.

| Original page | Integrated data path |
|---|---|
| Mission Control | Backend station metadata and the loaded experiment summary |
| India Atlas | Actual Bengaluru dataset coordinates, search and shared draft well selection |
| Station Details | Source coverage, coordinates and observation counts from the backend |
| Pump Model Explorer | Seven original conceptual models from /api/models; selection changes backend configuration |
| Mechanical Parameters Lab | Shared settings submitted to /api/simulations; invalid installations rejected |
| 3D Pump Twin | Shared backend timestep or the executed recommended schedule trace |
| Engineering Performance | Electrical/hydraulic power, head, flow and efficiencies from that same timestep |
| Live Monitoring | Same historical virtual state; no physical sensor feed is claimed |
| Forecast & Schedule | Backend hourly planner; unavailable live weather forecasts are clearly identified |
| Season Time Machine | Saved backend replay with daily chart and continuous timeline |
| Water-Life Ledger | Same trajectory, including policy switches, energy, stress components and reasons |
| Policy Arena | Four backend policy results from identical inputs |
| Trust Lab | Paired backend uncertainty trials and persisted results |
| Fleet Intelligence | Actual dataset stations and latest saved experiments; missing results remain empty |
| Bearing Analysis | Backend capability explicitly unavailable; synthetic fault traces removed |
| Evidence & Reports | Saved experiment settings, source hashes, provenance and CSV/JSON exports |

## Shared state

Navigating pages does not rerun the simulator or reset the selected experiment, model, timestamp or policy. Draft well/model changes require a new run. Outputs retain their saved configuration until that run succeeds.

Generate a recommendation on Forecast & Schedule and select **View recommended schedule in 3D**, or choose **Recommended schedule** in the twin. The pump, numeric state and ledger use the planner's executed trace, including cumulative water and drawdown across policy switches. A recommended day is distinct from the fixed-policy baseline comparison.

## Scope

The seven original designs have backend calculations but retain assumed specifications and conceptual geometry, not manufacturer curves. Surface designs reject groundwater lifts beyond the assumed 7 m suction limit. Actual forecast, IoT and vibration data remain unavailable. 35 wells have complete-day coverage; well 010317 has only six records and is disabled for replay. All active groundwater/solar simulation inputs are from the connected Bengaluru datasets; Nashik and other regions are not activated.

## Verification

26 unit/contract/parameter tests pass. Original P0-P2 pilot results are unchanged. HTTP checks cover both identical entry pages, seven-model metadata, compatibility rejection, source capability reporting, fleet data, saved experiments, timeline state, recommendations and uncertainty exports. Browser verification confirmed the original sidebar routes, model changes reaching the twin and engineering page, and recommended P2-to-P3 transitions in both 3D and the ledger.

The repository distribution excludes local saved experiments, databases, installation records and environment files. New saved experiments are created locally.
