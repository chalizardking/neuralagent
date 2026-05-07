## 2024-05-24 - [Avoid `len(query.all()) > 0` for SQLModel existence checks]
**Learning:** Checking for existence using `len(query.all()) > 0` in SQLModel/SQLAlchemy will fully execute the query and load all matching models into memory, leading to an N+1 memory footprint. Also learned from codebase context that calling `.first()` on the result object without `.limit(1)` in this setup fails to prevent full database queries.
**Action:** Always append `.limit(1)` to the `select()` statement before execution (e.g., `db.exec(select(...).limit(1)).first() is not None`) to ensure the DB limits the scan natively.
## 2024-05-18 - Fast API Route N+1 DB Commits
**Learning:** Found multiple places in `backend/routers/aiagent/generic.py` where SQLModel objects were sequentially added, committed, and refreshed in loops or back-to-back blocks. This causes high DB load and latency.
**Action:** When working with FastAPI and SQLModel routes, always look for iterations and sequentially built queries. Collect these objects in lists and perform a single `db.add_all()` and `db.commit()` operation.
