## 2024-05-24 - [Avoid `len(query.all()) > 0` for SQLModel existence checks]
**Learning:** Checking for existence using `len(query.all()) > 0` in SQLModel/SQLAlchemy will fully execute the query and load all matching models into memory, leading to an N+1 memory footprint. Also learned from codebase context that calling `.first()` on the result object without `.limit(1)` in this setup fails to prevent full database queries.
**Action:** Always append `.limit(1)` to the `select()` statement before execution (e.g., `db.exec(select(...).limit(1)).first() is not None`) to ensure the DB limits the scan natively.

## 2025-05-08 - [Batch DB Inserts in Loops]
**Learning:** Found an anti-pattern in `backend/routers/aiagent/generic.py` where O(n) individual `db.add()` and `db.commit()` operations were executed inside a loop during AI plan subtask generation. This creates high Database I/O latency.
**Action:** Always consolidate database insertions within loops by collecting objects into a list (using a list comprehension when possible) and executing a single `db.add_all()` and `db.commit()` outside the loop.
