# GUI Animations – Message Flash

## Context
Existing GUI implements matrix rain and avatar pulse but lacks a visual cue when new text arrives in the overlay.

## Design
- Add CSS `messageFlash` keyframes and `.flash` class.
- Trigger flash when `assistant_text` event sets overlay text.
- Remove class after animation to allow repeated flashes.
- Style uses accent color fading back to transparent background.
