## 2024-05-24 - [Avoid `len(query.all()) > 0` for SQLModel existence checks]
**Learning:** Checking for existence using `len(query.all()) > 0` in SQLModel/SQLAlchemy will fully execute the query and load all matching models into memory, leading to an N+1 memory footprint. Also learned from codebase context that calling `.first()` on the result object without `.limit(1)` in this setup fails to prevent full database queries.
**Action:** Always append `.limit(1)` to the `select()` statement before execution (e.g., `db.exec(select(...).limit(1)).first() is not None`) to ensure the DB limits the scan natively.

## 2024-05-18 - Consolidating DB inserts
**Learning:** Found an N+1 commit anti-pattern where a loop created database objects, calling `db.add()`, `db.commit()`, and `db.refresh()` on every iteration. This multiplies database I/O by the number of items and slows down plan generation unnecessarily.
**Action:** Consolidate multiple object creations in loops into a list comprehension, followed by a single `db.add_all()` and a single `db.commit()` outside the loop.
