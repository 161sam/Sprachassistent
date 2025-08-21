# Upgrade Notes

## LLM Model Listings
- WebSocket messages `get_llm_models` and `switch_llm_model` now expose
  separate lists for available and loaded models.
- Backend tracks the chosen LLM model and clears chat history when switching.

## Migration
- Clients should expect `llm_models` responses in the form:
  ```json
  {
    "type": "llm_models",
    "available": ["model-a", "model-b"],
    "loaded": ["model-a"],
    "current": "model-a"
  }
  ```
- When selecting a new model send:
  ```json
  {
    "type": "switch_llm_model",
    "model": "model-b"
  }
  ```
