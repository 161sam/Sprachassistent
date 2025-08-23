# Summary
- add generator to convert PCM16 byte streams into float32 chunks for STT
- cover new streaming helper with unit tests

# Risk
- low: new helper is additive and existing APIs unchanged

# Rollback
- revert commits `feat(stt): add streaming PCM16 converter` and `test(stt): cover streaming converter`
