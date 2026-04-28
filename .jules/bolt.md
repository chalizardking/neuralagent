## 2024-05-24 - [Avoid `len(query.all()) > 0` for SQLModel existence checks]
**Learning:** Checking for existence using `len(query.all()) > 0` in SQLModel/SQLAlchemy will fully execute the query and load all matching models into memory, leading to an N+1 memory footprint. Also learned from codebase context that calling `.first()` on the result object without `.limit(1)` in this setup fails to prevent full database queries.
**Action:** Always append `.limit(1)` to the `select()` statement before execution (e.g., `db.exec(select(...).limit(1)).first() is not None`) to ensure the DB limits the scan natively.

## 2024-05-24 - [Remove redundant `db.refresh()` calls to save DB I/O]
**Learning:** `db.refresh()` triggers an immediate SELECT statement to reload attributes from the database. When an object's attributes are not accessed after a `db.commit()` before an endpoint returns, the refresh call is entirely redundant and wastes DB I/O. Furthermore, because `db.commit()` sets `expire_on_commit=True` by default, if an attribute is ever accessed post-commit, SQLAlchemy automatically lazy-loads it natively, negating any performance gain from an explicit `db.refresh()`.
**Action:** Remove `db.refresh()` calls when object attributes are not explicitly read again before the function returns.
