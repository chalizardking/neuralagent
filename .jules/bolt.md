## 2024-06-25 - [SQLModel Existence Checks]
**Learning:** Checking for row existence using `len(db.exec(select(...)).all()) > 0` was found in `backend/routers/apps/threads.py`. This fetches all rows into memory which is a major bottleneck for threads with many tasks.
**Action:** Always use `db.exec(select(...).limit(1)).first() is not None` for checking existence to prevent loading the entire result set into application memory.
