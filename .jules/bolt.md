## 2026-04-15 - Optimize database existence check for working threads
**Learning:** Found instances of loading full query results into memory using `len(working_threads.all()) > 0` just to check if records exist.
**Action:** Replaced these inefficient calls with database-level existence checks using `.limit(1).first() is not None` to minimize memory consumption and speed up query execution time.
