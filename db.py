import aiosqlite


db = None


async def init():
    global db
    db = await aiosqlite.connect("lcc.db")


async def link_id(discord_id: int, leetcode_handle: str):
    await db.execute(
        "INSERT INTO users (discord_id, leetcode_handle, rank, tickets)"
        + " VALUES (?, ?, 'Noob', 0) ON CONFLICT (discord_id) DO UPDATE"
        + " SET leetcode_handle = ?, rank = 'Noob', tickets = 0 WHERE discord_id = excluded.discord_id",
        (discord_id, leetcode_handle, leetcode_handle),
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
    }


async def set_rank(discord_id: int, rank: str):
    await db.execute("UPDATE SET rank = ? WHERE discord_id = ?", (rank, discord_id))
    await db.commit()


async def add_tickets(discord_id: int, tickets: int):
    async with db.execute(
        "SELECT tickets FROM users WHERE discord_id = ?", (discord_id,)
    ) as cursor:
        row = cursor.fetchone()

    if not row:
        return

    old_tickets = row[0]

    await db.execute(
        f"UPDATE SET tickets = {old_tickets + tickets} WHERE discord_id = ?",
        (discord_id,),
    )
    await db.commit()

    return old_tickets + tickets


async def remove_tickets(discord_id: int, tickets: int):
    async with db.execute(
        "SELECT tickets FROM users WHERE discord_id = ?", (discord_id,)
    ) as cursor:
        row = cursor.fetchone()

    if not row:
        return

    old_tickets = row[0]
    new_tickets = old_tickets - tickets
    if old_tickets - tickets < 0:
        new_tickets = 0

    await db.execute(
        f"UPDATE SET tickets = {new_tickets} WHERE discord_id = ?", (discord_id,)
    )
    await db.commit()

    return new_tickets
