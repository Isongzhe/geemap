# Change: Fix SplitMapControl Global Variable Update

## Why
The `_current_split_control` module-level variable is not being updated correctly in the `update_layers()` function because the `global` keyword is missing. This causes the split map control in Uncertainty mode to display broken images where the left and right layers don't properly occupy 100% width.

## What Changes
- Add `global _current_split_control` declaration at the start of `update_layers()` function
- Ensure proper cleanup of the module-level singleton before creating new SplitMapControl instances

## Impact
- Affected specs: `step2-visualization`
- Affected code: `src/step2/app.py` (lines 484-615, specifically the `update_layers()` function)
- **Breaking**: No
