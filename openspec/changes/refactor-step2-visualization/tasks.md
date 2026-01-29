# Tasks: Refactor Step 2 Visualization

- [ ] Remove duplicate `map_widget`, `load_files_for_event`, and `use_effect` blocks in `src/step2/app.py`
- [ ] Implement `cleanup_map(m)` helper function to thoroughly remove controls (especially SplitMapControl) and layers
- [ ] Refactor `update_layers` to accept `tile_clients`, `current_event_date`, and `layer_mode` as explicit arguments
- [ ] Modify `load_files_for_event` to pass fresh `_tile_clients_cache` to `update_layers`
- [ ] Implement unique layer naming (e.g., `f"Classification_{date}_{mode}"`) to bust browser cache
- [ ] Add `STRICT S2 CHECK` and file existence verification
- [ ] Verify fix by switching between events and modes without artifacts
