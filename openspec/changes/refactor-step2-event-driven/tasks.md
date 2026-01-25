# Tasks: Refactor Step 2 to Event-Driven File Loading

## 1. Configuration Updates
- [x] 1.1 Add `get_model_config()` function to `src/config.py`
- [x] 1.2 Add `get_analog_df_config()` function to `src/config.py`
- [x] 1.3 Update `dataset/config.yaml` with event_date, input_folder, output_folder

## 2. File Discovery Module
- [x] 2.1 Create `src/step2/utils.py`
- [x] 2.2 Implement `find_event_input(event_date, input_folder)` - find S2_*.tif
- [x] 2.3 Implement `find_event_output(event_date, output_folder)` - find *_EDL.tif

## 3. Step 2 App Updates
- [x] 3.1 Import new config functions and utils
- [x] 3.2 Replace fixed paths with event-driven file discovery
- [x] 3.3 Add console logging for event_date and found files
- [x] 3.4 Add Event Information card in sidebar (Event Date, Return Period)

## 4. SplitMapControl Fix
- [x] 4.1 Add module-level `_current_split_control` variable
- [x] 4.2 Remove existing SplitMapControl BEFORE clearing layers
- [x] 4.3 Store new SplitMapControl reference after creation
- [x] 4.4 Test mode switching doesn't create duplicate controls

## 5. Legend Formatting
- [x] 5.1 Fix Classification Legend markdown (use explicit newlines)
- [x] 5.2 Fix Uncertainty Legend markdown (use explicit newlines)

## 6. Testing
- [x] 6.1 Test event_date file discovery
- [x] 6.2 Test SplitMapControl mode switching
- [x] 6.3 Verify legend display formatting
