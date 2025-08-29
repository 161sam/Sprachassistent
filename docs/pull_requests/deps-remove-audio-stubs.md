# Summary
- drop local torch/torchaudio/soundfile/piper stubs in favor of real dependencies
- skip piper-dependent tests when audio libraries are missing

# Risk
- environments without the real audio libraries will skip related tests and functionality

# Rollback
- restore removed stub modules from git history
