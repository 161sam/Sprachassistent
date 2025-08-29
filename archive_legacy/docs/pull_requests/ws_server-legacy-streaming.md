# Summary
- stream binary audio chunks in legacy WebSocket server instead of buffering
- log Kokoro voice detection errors rather than silently passing
- add regression test for chunk-wise STT handling

# Risk
- minimal: changes confined to legacy compat layer and test

# Rollback
- revert commit `fix(ws_server): stream legacy binary audio chunk-wise`
