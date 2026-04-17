## 2024-05-15 - Fast Existence Check in SQLModel
**Learning:** When checking for existence in SQLModel/SQLAlchemy within FastAPI endpoints (e.g., `threads.py`), using `len(query.all()) > 0` forces the DB to load all matching records into memory, which is a significant bottleneck. Calling `.first()` on the query builder does not append `LIMIT 1` to the executed query.
**Action:** Always append `.limit(1)` explicitly before `.first()` (i.e., `db.exec(select(...).limit(1)).first() is not None`) to ensure the database optimization happens.
