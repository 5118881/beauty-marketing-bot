import aiosqlite
from config import DATABASE_PATH


async def init_db():
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id     INTEGER PRIMARY KEY,
                username    TEXT,
                full_name   TEXT,
                has_access  INTEGER DEFAULT 0,
                joined_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS progress (
                user_id            INTEGER PRIMARY KEY,
                current_lesson     INTEGER DEFAULT 0,
                homework_status    TEXT DEFAULT 'none',
                -- none | waiting | approved | revision
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS homework (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id      INTEGER,
                lesson_num   INTEGER,
                content_type TEXT,   -- text | photo | voice | document
                file_id      TEXT,   -- для медиа
                text         TEXT,   -- для текстового ответа
                status       TEXT DEFAULT 'waiting',  -- waiting | approved | revision
                feedback     TEXT,
                submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                reviewed_at  TIMESTAMP
            )
        """)
        await db.commit()


async def get_user(user_id: int):
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM users WHERE user_id=?", (user_id,)) as c:
            row = await c.fetchone()
            return dict(row) if row else None


async def register_user(user_id: int, username: str, full_name: str):
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute(
            "INSERT OR IGNORE INTO users (user_id, username, full_name) VALUES (?,?,?)",
            (user_id, username, full_name)
        )
        await db.execute(
            "INSERT OR IGNORE INTO progress (user_id, current_lesson, homework_status) VALUES (?,0,'none')",
            (user_id,)
        )
        await db.commit()


async def grant_access(user_id: int):
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute("UPDATE users SET has_access=1 WHERE user_id=?", (user_id,))
        await db.execute(
            "UPDATE progress SET current_lesson=1, homework_status='none' WHERE user_id=?",
            (user_id,)
        )
        await db.commit()


async def has_access(user_id: int) -> bool:
    async with aiosqlite.connect(DATABASE_PATH) as db:
        async with db.execute("SELECT has_access FROM users WHERE user_id=?", (user_id,)) as c:
            row = await c.fetchone()
            return bool(row and row[0])


async def get_progress(user_id: int) -> dict | None:
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM progress WHERE user_id=?", (user_id,)) as c:
            row = await c.fetchone()
            return dict(row) if row else None


async def set_homework_status(user_id: int, status: str):
    """status: none | waiting | approved | revision"""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute(
            "UPDATE progress SET homework_status=? WHERE user_id=?", (status, user_id)
        )
        await db.commit()


async def advance_lesson(user_id: int):
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute(
            "UPDATE progress SET current_lesson=current_lesson+1, homework_status='none' WHERE user_id=?",
            (user_id,)
        )
        await db.commit()


async def save_homework(user_id: int, lesson_num: int, content_type: str,
                        file_id: str = None, text: str = None) -> int:
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cursor = await db.execute(
            "INSERT INTO homework (user_id, lesson_num, content_type, file_id, text) VALUES (?,?,?,?,?)",
            (user_id, lesson_num, content_type, file_id, text)
        )
        await db.commit()
        return cursor.lastrowid


async def update_homework_review(hw_id: int, status: str, feedback: str = None):
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute(
            "UPDATE homework SET status=?, feedback=?, reviewed_at=CURRENT_TIMESTAMP WHERE id=?",
            (status, feedback, hw_id)
        )
        await db.commit()


async def get_homework(hw_id: int) -> dict | None:
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM homework WHERE id=?", (hw_id,)) as c:
            row = await c.fetchone()
            return dict(row) if row else None


async def get_all_paid_users() -> list[int]:
    async with aiosqlite.connect(DATABASE_PATH) as db:
        async with db.execute("SELECT user_id FROM users WHERE has_access=1") as c:
            return [r[0] for r in await c.fetchall()]


async def get_all_users_for_admin() -> list[dict]:
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("""
            SELECT u.user_id, u.username, u.full_name, u.has_access,
                   p.current_lesson, p.homework_status
            FROM users u LEFT JOIN progress p ON u.user_id=p.user_id
            ORDER BY u.joined_at DESC
        """) as c:
            return [dict(r) for r in await c.fetchall()]
