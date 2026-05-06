## 2024-05-24 - [Avoid `len(query.all()) > 0` for SQLModel existence checks]
**Learning:** Checking for existence using `len(query.all()) > 0` in SQLModel/SQLAlchemy will fully execute the query and load all matching models into memory, leading to an N+1 memory footprint. Also learned from codebase context that calling `.first()` on the result object without `.limit(1)` in this setup fails to prevent full database queries.
**Action:** Always append `.limit(1)` to the `select()` statement before execution (e.g., `db.exec(select(...).limit(1)).first() is not None`) to ensure the DB limits the scan natively.

## 2024-05-18 - Avoid N+1 DB Queries by Batching Inserts
**Learning:** In SQLModel/SQLAlchemy, repeatedly calling `db.add()`, `db.commit()`, and `db.refresh()` inside a loop (like creating `PlanSubtask` objects) leads to severe N+1 database roundtrips, unnecessarily bottlenecking endpoints that process collections.
**Action:** Always refactor iterative database inserts into a list comprehension mapping items to objects, followed by a single `db.add_all(objects)` and `db.commit()` outside the loop. Use `db.refresh()` only if subsequent logic relies on generated database defaults before returning.
