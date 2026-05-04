## 2024-05-24 - [Avoid `len(query.all()) > 0` for SQLModel existence checks]
**Learning:** Checking for existence using `len(query.all()) > 0` in SQLModel/SQLAlchemy will fully execute the query and load all matching models into memory, leading to an N+1 memory footprint. Also learned from codebase context that calling `.first()` on the result object without `.limit(1)` in this setup fails to prevent full database queries.
**Action:** Always append `.limit(1)` to the `select()` statement before execution (e.g., `db.exec(select(...).limit(1)).first() is not None`) to ensure the DB limits the scan natively.
## 2024-05-24 - Database Optimization with DB.ADD_ALL()
**Learning:** Frequent individual `db.commit()` inside loops causes severe DB I/O latency.
**Action:** Consolidate multiple database insertions and updates within loops by collecting objects into a list and calling `db.add_all()` followed by a single `db.commit()` outside the loop.
