# Implementation Tasks

## 1. Configuration Setup
- [x] 1.1 Update `dataset/config.yaml` with `analog_df` section (path, top_n)
- [x] 1.2 Add `model.permanent_water_path` to config.yaml
- [x] 1.3 Verify CSV file exists at configured path
- [x] 1.4 Verify permanent water COG exists at configured path
- [x] 1.5 Test config loading with `load_yaml_config()`

## 2. Backend Utilities (`src/step2/utils.py`)
- [x] 2.1 Modify `find_event_input()` to strictly require S2 files (remove fallback)
- [x] 2.2 Modify `find_event_output()` to use wildcard prefix pattern `*{event_date}*_EDL.tif`
- [x] 2.3 Add `find_event_preview()` function to locate PNG files `*{event_date}*_EDL_prediction.png`
- [x] 2.4 Add `load_analog_catalog()` function to read and filter CSV
- [x] 2.5 Add docstrings and type hints to new functions
- [x] 2.6 Test utility functions with sample data paths

## 3. Permanent Water Layer (`src/step2/app.py`)
- [x] 3.1 Add port constant `PERMANENT_WATER_PORT = 9102` to `src/config.py`
- [x] 3.2 Create `_create_permanent_water_client()` function with singleton pattern
- [x] 3.3 Update `_tile_clients_cache` to include 'water' key
- [x] 3.4 Modify `update_layers()` to add permanent water overlay in Classification mode
- [x] 3.5 Set permanent water layer properties: palette=['transparent', '#0000FF'], opacity=0.5
- [x] 3.6 Test layer z-index ordering (water should appear above classification)
- [x] 3.7 Verify graceful fallback if permanent water file is missing

## 4. Event Selection State (`src/step2/app.py`)
- [x] 4.1 Add reactive state `analog_events_df = solara.reactive(None)` for CSV data
- [x] 4.2 Add reactive state `selected_event_date = solara.reactive(None)` for dropdown
- [x] 4.3 Add reactive state `selected_event_metadata = solara.reactive({})` for rank/score
- [x] 4.4 Load analog catalog in `initialize_step2_data()` using `load_analog_catalog()`
- [x] 4.5 Set default `selected_event_date` to rank 1 event from CSV
- [x] 4.6 Update `selected_event_metadata` when dropdown changes

## 5. Dynamic File Loading (`src/step2/app.py`)
- [x] 5.1 Modify `initialize_step2_data()` to accept event_date parameter (instead of using config directly)
- [x] 5.2 Add `use_effect` to trigger file re-discovery when `selected_event_date` changes
- [x] 5.3 Clear and rebuild `_tile_clients_cache` for input/output (keep water static)
- [x] 5.4 Handle case where files are missing for selected event (log warning, show placeholder)
- [x] 5.5 Test event switching with multiple dates from CSV

## 6. Event Selector UI (`src/step2/app.py`)
- [x] 6.1 Replace Event Information section with Event Selection dropdown
- [x] 6.2 Add `solara.Select` component bound to `selected_event_date`
- [x] 6.3 Populate dropdown with dates from `analog_events_df`
- [x] 6.4 Display preview image using `solara.Image` (load via `find_event_preview()`)
- [x] 6.5 Show event metadata card: Rank, Date, MAE Score
- [x] 6.6 Add placeholder for missing preview images ("Preview not available")

## 7. Analytics Panel - Layout (`src/step2/app.py`)
- [x] 7.1 Add new row below map using `solara.Row` or `solara.Columns`
- [x] 7.2 Left column: DataFrame display using `solara.DataFrame`
- [x] 7.3 Right column: Chart container using `solara.HTML` or `solara.display`
- [x] 7.4 Set panel height to ~400px with scrollable content
- [x] 7.5 Test responsive layout on different screen sizes

## 8. Analytics Panel - Event Table (`src/step2/app.py`)
- [x] 8.1 Create table component showing rank, datetime, score columns
- [x] 8.2 Use `solara.DataFrame` with `analog_events_df.value`
- [x] 8.3 Enable scrolling for long event lists
- [x] 8.4 Test with 10, 50, and 100 events

## 9. Analytics Panel - Score Distribution Chart (`src/step2/app.py`)
- [x] 9.1 Choose charting library (matplotlib or plotly - recommend matplotlib for simplicity)
- [x] 9.2 Create box plot showing score distribution using `ax.boxplot()`
- [x] 9.3 Add strip plot overlay using `ax.scatter()` with alpha=0.5
- [x] 9.4 Highlight selected event with red star: `marker='*'`, `color='red'`, `s=200`, `zorder=10`
- [x] 9.5 Set y-axis label to "MAE Score"
- [x] 9.6 Add chart title: "Similarity Score Distribution (Lower is Better)"
- [x] 9.7 Convert matplotlib figure to Solara-compatible format
- [x] 9.8 Test chart updates when event selection changes

## 10. Legend Updates (`src/step2/app.py`)
- [x] 10.1 Update Classification legend to mention permanent water overlay
- [x] 10.2 Add text: "Blue overlay indicates permanent water boundaries"
- [x] 10.3 Verify legend text is clear and concise

## 11. Integration Testing
- [x] 11.1 Test full workflow: Start app → Load CSV → Select event → View layers
- [x] 11.2 Verify permanent water appears correctly on Classification mode
- [x] 11.3 Verify permanent water does NOT appear on Uncertainty mode
- [x] 11.4 Test switching between multiple events (3+ different dates)
- [x] 11.5 Verify analytics chart updates red star position
- [x] 11.6 Test with missing files (input, output, preview, permanent water)
- [x] 11.7 Verify console logs are informative (no silent failures)
- [x] 11.8 Test hot-reload does not create port conflicts
- [x] 11.9 Verify memory usage is stable across 10+ event switches

## 12. Documentation
- [x] 12.1 Update `CLAUDE.md` with new config sections (analog_df, permanent_water_path)
- [x] 12.2 Document CSV format requirements (columns: rank, method, datetime, score)
- [x] 12.3 Document port allocation (9102 for permanent water)
- [x] 12.4 Add troubleshooting section for common issues (missing CSV, missing preview)
- [x] 12.5 Update file structure documentation to mention analytics panel

## 13. Validation & Cleanup
- [x] 13.1 Run Python import test: `python -c "from src.step2 import app, utils"`
- [x] 13.2 Verify no linting errors (if linter is configured)
- [x] 13.3 Check for TODO/FIXME comments in modified files
- [x] 13.4 Verify all console.log/print statements are informative
- [x] 13.5 Test graceful degradation (all fallback scenarios)
