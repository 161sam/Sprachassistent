# Design Note: unify chunking with sanitizer pipeline

- rely on `pre_sanitize_text` from `text_sanitizer` for all normalization
- drop redundant `unicodedata.normalize` call
- expose `limit_and_chunk` publicly (remove underscore) for clearer API
- adjust imports across codebase to new function name
- update tests and docs accordingly

