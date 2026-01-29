# Design: Flood Analytics Dashboard

## Context

**Background**: The current Step 2 implementation displays a single flood event with static file paths. The system needs to support multi-event analysis for flood analog comparison based on GloFAS similarity scoring.

**Constraints**:
- Must maintain COG-based architecture (no preprocessing)
- localtileserver singleton pattern must be preserved
- Port conflicts must be avoided during hot-reload
- UI must remain responsive with <1s event switching

**Stakeholders**:
- Flood analysts comparing historical events
- Researchers evaluating analog quality
- Decision-makers selecting reference scenarios

## Goals / Non-Goals

**Goals**:
- Enable dynamic event selection from analog dataset
- Visualize permanent water boundaries for context
- Provide similarity metrics and distribution visualization
- Maintain current split-map comparison workflow
- Support both S2 and Landsat output files

**Non-Goals**:
- Real-time analog computation (CSV is pre-computed)
- Advanced filtering beyond top_n selection
- Multi-basin comparison (single watershed per session)
- Export or download functionality (v1)

## Decisions

### Decision 1: CSV-Based Event Catalog

**What**: Load analog events from CSV file specified in config.yaml

**Why**:
- GloFAS analog results are already computed and stored as CSV
- CSV format is simple, portable, and human-readable
- pandas provides efficient loading and filtering (<100ms for 1000 events)
- No database dependency required

**Alternatives considered**:
- JSON catalog: More verbose, no performance benefit
- Database (SQLite): Overkill for <1000 events
- Hardcoded list: Not maintainable

**Implementation**:
```python
# Load once at initialization
df = pd.read_csv(config['analog_df']['path'])
df = df.sort_values('rank').head(config['analog_df']['top_n'])
available_dates = df['datetime'].tolist()
```

### Decision 2: Strict S2 Input Requirement

**What**: Only accept Sentinel-2 files for input, no fallback to Landsat

**Why**:
- User explicitly requires S2 data
- Different sensors have different characteristics that affect model output
- Prevents accidental mixing of sensor types
- Clearer error messages when S2 data is missing

**Alternatives considered**:
- Auto-fallback to Landsat: Could cause confusion about data source
- Sensor detection: Adds complexity without clear benefit

**Implementation**:
```python
def find_event_input(event_date: str, input_folder: str) -> Optional[Path]:
    matches = list(Path(input_folder).glob(f"S2_{event_date}*.tif"))
    return matches[0] if matches else None  # No fallback
```

### Decision 3: Permanent Water as Static Overlay

**What**: Load permanent water COG once, use same layer across all events

**Why**:
- Permanent water boundaries don't change with event date
- Single TileClient reduces memory and port usage
- Config path is fixed (`model.permanent_water_path`)
- Overlay pattern is intuitive for users

**Alternatives considered**:
- Per-event permanent water: Unnecessary complexity
- Toggle button: Adds UI clutter, should always be visible
- Blend mode: Semi-transparency is simpler and more predictable

**Implementation**:
```python
# Create once, reuse across events
water_client = TileClient(config['model']['permanent_water_path'], port=9102)
water_layer = get_leaflet_tile_layer(
    water_client,
    palette=['transparent', '#0000FF'],
    opacity=0.5
)
# Add to map with high z-index
```

### Decision 4: Box + Strip Plot for Similarity Distribution

**What**: Use matplotlib or plotly to show score distribution with highlighted selection

**Why**:
- Box plot shows quartiles and outliers (distribution shape)
- Strip plot shows individual event scores (granularity)
- Red star makes selected event immediately visible
- Industry-standard visualization pattern

**Alternatives considered**:
- Histogram: Loses individual event identity
- Scatter plot: Doesn't show distribution statistics
- Table only: Harder to see outliers and patterns

**Implementation** (matplotlib):
```python
fig, ax = plt.subplots(figsize=(8, 4))
ax.boxplot(df['score'], vert=True)
ax.scatter([1]*len(df), df['score'], alpha=0.5)
# Highlight selected
selected_score = df[df['datetime'] == selected_date]['score'].values[0]
ax.scatter([1], [selected_score], color='red', s=200, marker='*', zorder=10)
```

### Decision 5: TileClient Port Allocation

**What**: Allocate 3 ports for TileClients (input, output, permanent water)

**Current allocation**:
- 9100: Input (Sentinel-2)
- 9101: Output (Flood classification + uncertainty)
- 9102: Permanent water (new)

**Why**:
- Maintains existing port pattern
- localtileserver requires unique ports per TileClient
- Sequential numbering is easy to remember
- Port range 9100-9199 avoids common service conflicts

**Alternatives considered**:
- Dynamic port allocation: Harder to debug and document
- Share output client with band indexing: Permanent water is separate file

## Risks / Trade-offs

### Risk 1: Port Exhaustion on Hot-Reload
**Mitigation**: Use module-level singleton cache for all TileClients, including permanent water

### Risk 2: Large CSV Files (>10k Events)
**Impact**: UI lag when loading dropdown
**Mitigation**: Use `top_n` limit in config (default 10-50 events)

### Risk 3: Missing Preview Images
**Impact**: Preview area shows "Image not found"
**Mitigation**: Graceful fallback, display text placeholder instead of error

### Risk 4: S2 File Missing for Some Events
**Impact**: Cannot visualize that event
**Mitigation**:
- Console warning logs
- Disable event in dropdown (future enhancement)
- Document file naming convention clearly

### Risk 5: Layer Composition Complexity
**Impact**: Permanent water might not render properly over classification
**Mitigation**:
- Test z-index ordering carefully
- Use semi-transparency (0.5) for visibility
- Document layer stacking order in spec

## Migration Plan

**Phase 1: Backward Compatibility**
1. Keep existing single-event mode functional if CSV is not configured
2. Check if `analog_df.path` exists in config
3. If missing, fall back to current behavior (single event_date)

**Phase 2: Configuration Update**
1. Update `dataset/config.yaml` with new sections:
   - `analog_df.path`
   - `analog_df.top_n`
   - `model.permanent_water_path`
2. Validate paths exist and are accessible

**Phase 3: Code Implementation**
1. Implement utility functions first (testable independently)
2. Add permanent water layer (visual validation)
3. Add event selector UI (interactive testing)
4. Add analytics panel (final integration)

**Rollback Plan**:
- If issues occur, remove `analog_df` section from config.yaml
- System will fall back to single-event mode
- No data migration needed (CSV is read-only)

## Open Questions

1. **Q**: Should we support filtering by score threshold?
   **A**: Defer to future enhancement. Use `top_n` for v1.

2. **Q**: What if permanent water file is missing?
   **A**: Log warning, skip overlay layer. Classification still works.

3. **Q**: Should we cache preview images in browser?
   **A**: Let browser handle caching via standard HTTP headers.

4. **Q**: How to handle timezone differences in datetime field?
   **A**: Use date string as-is, assume UTC (consistent with GloFAS data).

5. **Q**: Should analytics panel be collapsible?
   **A**: No for v1. Keep layout simple. Add toggle in future if requested.
