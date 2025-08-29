# Design Note: Remove legacy WS backup file

The file `ws_server/compat/legacy_ws_server.py.backup.int_fix` duplicates the updated `legacy_ws_server.py`.
The backup adds no unique functionality and contains obsolete TODO comments.
Removing it avoids confusion and ensures the compat module has a single source.
Before deletion, diff confirmed all relevant fixes are present in `legacy_ws_server.py`.
