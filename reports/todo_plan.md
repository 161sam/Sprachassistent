# TODO Work Plan

## Overview
Tasks prioritized by urgency and dependency.

1. **Merge VoiceAssistantCore & AudioStreamer**  
   - **Priority:** Medium  
   - **Domain:** Frontend  
   - **Dependencies:** Requires analyzing shared streaming logic; prerequisite for GUI consolidation.  
   - **Rationale:** Eliminates duplicated client streaming code, simplifying maintenance.

2. **Consolidate GUI with Shared Core**  
   - **Priority:** Medium  
   - **Domain:** Frontend  
   - **Dependencies:** Depends on Task 1 to provide unified streaming module.  
   - **Rationale:** Avoids redundant GUI logic and ensures consistent behavior.

3. **Unify Voice Alias Configuration**  
   - **Priority:** Low  
   - **Domain:** Config / Backend  
   - **Dependencies:** None.  
   - **Rationale:** Prevents drift between `ws_server/tts/voice_aliases.py`, `config/tts.json`, and environment defaults.

4. **Replace Stubbed Audio Dependencies**  
   - **Priority:** Low  
   - **Domain:** Backend / Dependencies  
   - **Dependencies:** Availability of real `torch`, `torchaudio`, `soundfile`, and `piper` packages.  
   - **Rationale:** Removes temporary stubs, enabling real audio processing and cleaner tests.

5. **GUI Layout and Animation Refresh**  
   - **Priority:** Low  
   - **Domain:** Frontend / UX  
   - **Dependencies:** None, but best tackled after core consolidation to avoid conflicts.  
   - **Rationale:** Modernizes the interface and improves user feedback.

