## 2024-05-24 - [Avoid `len(query.all()) > 0` for SQLModel existence checks]
**Learning:** Checking for existence using `len(query.all()) > 0` in SQLModel/SQLAlchemy will fully execute the query and load all matching models into memory, leading to an N+1 memory footprint. Also learned from codebase context that calling `.first()` on the result object without `.limit(1)` in this setup fails to prevent full database queries.
**Action:** Always append `.limit(1)` to the `select()` statement before execution (e.g., `db.exec(select(...).limit(1)).first() is not None`) to ensure the DB limits the scan natively.
## 2024-05-16 - Bolt Optimization: Consolidate DB insertions
**Learning:** Calling `db.commit()` inside a loop causes a separate database transaction per item, increasing latency linearly (O(N) DB transaction overhead).
**Action:** Use `db.add_all()` to consolidate items into a list outside the loop and call a single `db.commit()` to achieve O(1) DB transaction overhead, significantly speeding up plan creation in environments with database latency.
