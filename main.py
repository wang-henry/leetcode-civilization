import asyncio
import random
from cachetools import TTLCache
import discord
from consts import RANKUP_PROGRESSION
import db
from discord import app_commands
from discord.ext import commands
import lcapi
from datetime import datetime, timezone
import time

from util import create_embed, create_profile_embed, user_command

intents = discord.Intents.default()
bot = commands.Bot(
    command_prefix="/",
    intents=intents,
    case_insensitive=False,
)
link_cache = TTLCache(maxsize=1024, ttl=300)
rankup_cache = TTLCache(maxsize=1024, ttl=60 * 20)


@bot.tree.command(
    name="ping",
    description="Pong",
)
async def ping(interaction: discord.Interaction):
    await interaction.response.send_message("Pong!", ephemeral=True)


@bot.tree.command(
    name="link", description="Link your Discord account to a Leetcode account."
)
@app_commands.describe(leetcode_username="The Leetcode username to link to.")
async def link(interaction: discord.Interaction, leetcode_username: str):
    verification_code = str(random.randint(0, 999999)).zfill(6)
    link_cache[interaction.user.id] = (verification_code, leetcode_username)
    await interaction.response.send_message(
        embed=create_embed(
            f"To verify you own this Leetcode account ({leetcode_username}), add `{verification_code}` to your summary and use `/verify`."
        ),
        ephemeral=True,
    )


@bot.tree.command(name="profile", description="Check your privilege.")
@user_command(fetch_lc=False)
async def profile(interaction: discord.Interaction):
    user_info, _ = interaction.data["injected"]
    # used saved LC stats
    lc_info = {
        "EASY": user_info["easies"],
        "MEDIUM": user_info["mediums"],
        "HARD": user_info["hards"],
    }
    await interaction.response.send_message(
        embed=create_profile_embed(
            user_info, lc_info, interaction.user.name, interaction.user.avatar
        )
    )


@bot.tree.command(
    name="sync",
    description="Sync your Leetcode solved questions with Leetcode Civilization.",
)
@user_command(fetch_lc=True)
async def sync(interaction: discord.Interaction):
    user_info, lc_info = interaction.data["injected"]
    await db.sync_solved(interaction.user.id, lc_info)

    easies_solved = max(0, lc_info["EASY"] - user_info["easies"])
    mediums_solved = max(0, lc_info["MEDIUM"] - user_info["mediums"])
    hards_solved = max(0, lc_info["HARD"] - user_info["hards"])

    easy_suffix = "Easy" if easies_solved == 1 else "Easies"
    medium_suffix = "Medium" if mediums_solved == 1 else "Mediums"
    hard_suffix = "Hard" if hards_solved == 1 else "Hards"

    tickets = easies_solved * 5 + mediums_solved * 10 + hards_solved * 25

    if tickets > 0:
        await db.set_tickets(interaction.user.id, user_info["tickets"] + tickets)

    add_msg = (
        "No change from before."
        if easies_solved + mediums_solved + hards_solved == 0
        else f"You solved **{easies_solved}** {easy_suffix}, **{mediums_solved}** {medium_suffix}, and **{hards_solved}** {hard_suffix}, earning you a total of **{tickets}** tickets."
    )
    await interaction.response.send_message(
        embed=create_embed(f"Successfully synced solved questions!\n{add_msg}")
    )


@bot.tree.command(
    name="daily",
    description="Claim your daily tickets if you've finished today's daily problem.",
)
@user_command(fetch_lc=False)
async def daily(interaction: discord.Interaction):
    user_info, _ = interaction.data["injected"]
    await interaction.response.defer(thinking=True)

    daily_question = await lcapi.get_daily_question()

    ac_rate = daily_question["question"]["acRate"]
    difficulty = daily_question["question"]["difficulty"]
    question_link = daily_question["link"]

    base_difficulty_tickets = {
        "Easy": 8,
        "Medium": 15,
        "Hard": 30,
    }
    tickets = base_difficulty_tickets[difficulty] + round(
        (max(0, (100 - ac_rate)) / 100) * (base_difficulty_tickets[difficulty] / 2)
    )
    start_time = int(
        datetime.strptime(daily_question["date"], "%Y-%m-%d")
        .replace(tzinfo=timezone.utc)
        .timestamp()
    )
    question_interval = (start_time, start_time + 86400)

    if await db.check_daily_claimed(interaction.user.id, start_time):
        await interaction.followup.send(
            embed=create_embed("You already claimed today's daily tickets!")
        )
        return

    recent_ac = await lcapi.get_recent_ac(user_info["leetcode_handle"])
    for submission in recent_ac:
        if (
            submission["titleSlug"] == daily_question["question"]["titleSlug"]
            and question_interval[0]
            <= int(submission["timestamp"])
            <= question_interval[1]
        ):
            await db.set_daily_claimed(interaction.user.id, start_time)
            await db.set_tickets(interaction.user.id, user_info["tickets"] + tickets)
            await interaction.followup.send(
                embed=create_embed(
                    f"For completing today's daily (**{difficulty}**) with an acceptance rate of **~{round(ac_rate, 2)}%**, you earned **{tickets}** tickets!"
                )
            )
            return

    await interaction.followup.send(
        embed=create_embed(
            f"You haven't done today's daily, or your submission is outside of your recent 15. Please complete the daily [here](https://leetcode.com{question_link})."
        )
    )


@bot.tree.command(
    name="verify",
    description="Verify your linked Leetcode account. Only use this after using /link.",
)
async def verify(interaction: discord.Interaction):
    if interaction.user.id not in link_cache:
        await interaction.response.send_message(
            embed=create_embed(
                "You haven't called `/link`, or your verification code has expired. Please `/link` again!"
            ),
            ephemeral=True,
        )
        return

    verification_code, leetcode_username = link_cache[interaction.user.id]

    await interaction.response.defer(ephemeral=True)

    summary = await lcapi.get_profile_summary(leetcode_username)
    if verification_code not in summary:
        await interaction.followup.send(
            embed=create_embed(f"Didn't find `{verification_code}` in your summary!"),
            ephemeral=True,
        )
        return

    solve_count = await lcapi.get_solve_count(leetcode_username)
    profile_info = await db.link_id(interaction.user.id, leetcode_username, solve_count)

    profile_embed = create_profile_embed(
        profile_info, solve_count, "Verified!", interaction.user.avatar
    )
    profile_embed.set_footer(
        text="Note: If you link to another Leetcode account in the future, your rank and tickets will be reset!"
    )
    await interaction.followup.send(embed=profile_embed)


@bot.tree.command(name="rankup", description="Use tickets to attempt to rank up.")
@user_command(fetch_lc=False)
async def rankup(interaction: discord.Interaction):
    user_info, _ = interaction.data["injected"]
    await interaction.response.defer(thinking=True)
    # if user already called rankup
    if interaction.user.id in rankup_cache:
        recent_ac = await lcapi.get_recent_ac(user_info["leetcode_handle"])
        if not recent_ac:
            await interaction.followup.send(
                embed=create_embed("Your recent submission list is empty.")
            )
            return
        latest_submission = recent_ac[0]
        question_info = rankup_cache[interaction.user.id]
        if latest_submission["titleSlug"] == question_info["titleSlug"]:
            if user_info["rank"] != "Champion":
                new_rank = RANKUP_PROGRESSION[user_info["rank"]]["next_rank"]
                await db.set_rank(interaction.user.id, new_rank)
                await interaction.followup.send(
                    embed=create_embed(
                        f"Congrats on ranking up! You are now a Leetcode **{new_rank}**."
                    )
                )

                del rankup_cache[interaction.user.id]
            else:
                base_lp = {
                    "Easy": 2,
                    "Medium": 5,
                    "Hard": 10,
                }

                lp_gain = round(
                    base_lp[question_info["difficulty"]]
                    + ((100 - question_info["acRate"]) / 100)
                    * base_lp[question_info["difficulty"]]
                )
                new_lp = user_info["champion_lp"] + lp_gain
                await db.set_lp(interaction.user.id, new_lp)
                await interaction.followup.send(
                    embed=create_embed(
                        f"Congrats on ranking up! You gained **+{lp_gain}** LP, and now have a total of **{new_lp}** LP."
                    )
                )

                del rankup_cache[interaction.user.id]
        else:
            await interaction.followup.send(
                embed=create_embed(
                    f"Your latest submission is not the challenge problem.\nComplete the challenge problem [here](https://leetcode.com/problems/{question_info['titleSlug']})."
                )
            )
            return
    else:
        # if user did not call rankup (or challenge has expired)
        if user_info["tickets"] < RANKUP_PROGRESSION[user_info["rank"]]["ticket_cost"]:
            await interaction.followup.send(
                embed=create_embed(
                    f"You need at least **{RANKUP_PROGRESSION[user_info["rank"]]["ticket_cost"]}** tickets to attempt the rankup challenge."
                )
            )
            return

        if user_info["rank"] == "Champion":
            difficulty = random.choice(["MEDIUM", "HARD"])

        question_info = await lcapi.get_random_problem(difficulty=difficulty)

        if not question_info:
            await interaction.followup.send(
                embed=create_embed("There was a problem getting a problem, try again!")
            )
            return

        await db.set_tickets(
            interaction.user.id,
            user_info["tickets"] - RANKUP_PROGRESSION[user_info["rank"]]["ticket_cost"],
        )
        difficulty = RANKUP_PROGRESSION[user_info["rank"]]["difficulty"]
        rankup_cache[interaction.user.id] = question_info
        exp_time = int(time.time() + 60 * 20)
        await interaction.followup.send(
            embed=create_embed(
                f"Used **{RANKUP_PROGRESSION[user_info["rank"]]["ticket_cost"]}** tickets to attempt the rankup challenge!\n\n"
                + f"Your rankup challenge is **[{question_info['title']}](https://leetcode.com/problems/{question_info['titleSlug']}) ({question_info['difficulty']})**."
                + f"\nYou must finish it <t:{exp_time}:R>.\nImmediately after you submit an accepted solution, use `/rankup` again."
            )
        )


@bot.event
async def on_ready():
    await bot.tree.sync()
    print("Ready!")


if __name__ == "__main__":
    asyncio.run(db.init())
    with open("token", "r") as f:
        token = f.read()
    bot.run(token)
