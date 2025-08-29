# Summary
- validate 16-bit PCM data and supported sample rates in `binary_v2` messages
- document decision and mark TODO resolved

# Risk
- Low: additional checks reject malformed audio but do not alter happy-path data

# Rollback
- Revert commit `fix(protocol): validate PCM frames`
