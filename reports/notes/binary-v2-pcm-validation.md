# PCM validation in Binary protocol

## Context
`ws_server/protocol/binary_v2.py` lacked checks ensuring incoming binary frames were 16‑bit PCM at a supported sample rate.

## Decision
Validate audio frames before handing them to STT:
- assert declared sample rate is in `{16000, 44100, 48000}`
- run `audioop.rms` to confirm 16‑bit PCM layout
- error out on mismatch instead of silent failure

## Consequences
Ensures early rejection of malformed audio and prevents downstream crashes; metrics remain unaffected.
