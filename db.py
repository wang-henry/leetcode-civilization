import aiosqlite


db = None


async def init():
    global db
    db = await aiosqlite.connect("lcc.db")


async def link_id(discord_id: int, leetcode_handle: str, lc_info: dict):
    await db.execute(
        "INSERT INTO users (discord_id, leetcode_handle, rank, tickets, easies, mediums, hards, champion_lp)"
        + " VALUES (?, ?, 'Noob', 0, ?, ?, ?, 0) ON CONFLICT (discord_id) DO UPDATE"
        + " SET leetcode_handle = ?, rank = 'Noob', tickets = 0, easies = 0, mediums = 0, hards = 0, champion_lp = 0 WHERE discord_id = excluded.discord_id",
        (
            discord_id,
            leetcode_handle,
            lc_info["EASY"],
            lc_info["MEDIUM"],
            lc_info["HARD"],
            leetcode_handle,
        ),
    )
    await db.commit()
    return {
        "discord_id": discord_id,
        "leetcode_handle": leetcode_handle,
        "rank": "Noob",
        "tickets": 0,
    }


async def get_leetcode_handle(discord_id: int):
    async with db.execute(
        "SELECT leetcode_handle FROM users WHERE discord_id = ?", (discord_id,)
    ) as cursor:
        row = await cursor.fetchone()

    if not row:
        return None

    return row[0]


async def get_info(discord_id: int):
    async with db.execute(
        "SELECT * FROM users WHERE discord_id = ?", (discord_id,)
    ) as cursor:
        row = await cursor.fetchone()

    if not row:
        return None

    return {
        "discord_id": row[0],
        "leetcode_handle": row[1],
        "rank": row[2],
        "tickets": row[3],
        "easies": row[4],
        "mediums": row[5],
        "hards": row[6],
        "champion_lp": row[7],
    }


async def set_rank(discord_id: int, rank: str):
    await db.execute("UPDATE users SET rank = ? WHERE discord_id = ?", (rank, discord_id))
    await db.commit()

async def set_lp(discord_id: int, lp: int):
    await db.execute("UPDATE users SET champion_lp = ? WHERE discord_id = ?", (lp, discord_id))
    await db.commit()

async def set_tickets(discord_id: int, tickets: int):
    await db.execute(
        f"UPDATE users SET tickets = {tickets} WHERE discord_id = ?",
        (discord_id,),
    )
    await db.commit()


async def sync_solved(discord_id: int, lc_info: dict):
    await db.execute(
        "UPDATE users SET easies = ?, mediums = ?, hards = ? WHERE discord_id = ?",
        (lc_info["EASY"], lc_info["MEDIUM"], lc_info["HARD"], discord_id),
    )
    await db.commit()


async def check_daily_claimed(discord_id: int, start_time: int):
    async with db.execute(
        "SELECT discord_id FROM daily_claims WHERE discord_id = ? AND daily_start_time = ? LIMIT 1",
        (discord_id, start_time),
    ) as cursor:
        row = await cursor.fetchone()

    if row:
        return True

    return False


async def set_daily_claimed(discord_id: int, start_time: int):
    await db.execute("INSERT INTO daily_claims VALUES (?, ?)", (discord_id, start_time))
    await db.commit()
