## 2024-05-24 - [Avoid `len(query.all()) > 0` for SQLModel existence checks]
**Learning:** Checking for existence using `len(query.all()) > 0` in SQLModel/SQLAlchemy will fully execute the query and load all matching models into memory, leading to an N+1 memory footprint. Also learned from codebase context that calling `.first()` on the result object without `.limit(1)` in this setup fails to prevent full database queries.
**Action:** Always append `.limit(1)` to the `select()` statement before execution (e.g., `db.exec(select(...).limit(1)).first() is not None`) to ensure the DB limits the scan natively.

## 2025-02-23 - [Consolidate database insertions using db.add_all()]
**Learning:** Sequential, individual `db.add()` and `db.commit()` operations inside loops or blocks that update multiple related tables trigger O(N) database trips. Each commit incurs blocking synchronous I/O and transaction overhead.
**Action:** Always collect objects into a list and use `db.add_all()` followed by a single `db.commit()` when performing bulk insertions or multi-table updates within an endpoint. Only use `db.flush()` if interim primary key IDs are explicitly required.
