## 2024-05-24 - N+1 Issue Checks
**Learning:** For SQLModel/SQLAlchemy existence checks, using `.all()` loads all matched rows into memory before calculating `len()`, resulting in a large memory and performance overhead for checks. Calling `.limit(1)` before executing the select statement, and then checking if `.first() is not None` speeds it up to $O(1)$.
**Action:** When doing database existence checks with SQLModel, strictly use `select(...).limit(1)` in the DB execution and check if `.first() is not None`.
