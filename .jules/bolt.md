## 2024-05-24 - [Avoid `len(query.all()) > 0` for SQLModel existence checks]
**Learning:** Checking for existence using `len(query.all()) > 0` in SQLModel/SQLAlchemy will fully execute the query and load all matching models into memory, leading to an N+1 memory footprint. Also learned from codebase context that calling `.first()` on the result object without `.limit(1)` in this setup fails to prevent full database queries.
**Action:** Always append `.limit(1)` to the `select()` statement before execution (e.g., `db.exec(select(...).limit(1)).first() is not None`) to ensure the DB limits the scan natively.

## 2024-05-25 - [Optimize mapping collections to list comprehensions]
**Learning:** Found multiple instances where collections were mapped using explicit `for`-loops with `.append()` inside the AI Agent routing functions (`backend/routers/aiagent/*` and `backend/routers/apps/threads.py`). While typical in some languages, Python evaluates list comprehensions in C, making them faster than `.append()` calls in a loop.
**Action:** Replaced these explicit loops with list comprehensions where data was being mapped. Next time, always use list comprehensions for array mappings in Python.
