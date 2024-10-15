import random
from cachetools import TTLCache
import discord
import db
from discord import app_commands
from discord.ext import commands
import lcapi

from util import create_embed, create_profile_embed, user_command

intents = discord.Intents.default()
bot = commands.Bot(
    command_prefix="/",
    intents=intents,
    case_insensitive=False,
)
link_cache = TTLCache(maxsize=1024, ttl=300)


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
@user_command()
async def profile(interaction: discord.Interaction):
    user_info, lc_info = interaction.data["injected"]
    await interaction.response.send_message(
        embed=create_profile_embed(
            user_info, lc_info, interaction.user.name, interaction.user.avatar
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

    profile_info = await db.link_id(interaction.user.id, leetcode_username)
    solve_count = await lcapi.get_solve_count(leetcode_username)

    profile_embed = create_profile_embed(
        profile_info, solve_count, "Verified!", interaction.user.avatar
    )
    profile_embed.set_footer(
        text="Note: If you link to another Leetcode account in the future, your rank and tickets will be reset!"
    )
    await interaction.followup.send(embed=profile_embed)


@bot.event
async def on_ready():
    await bot.tree.sync()
    await db.init()
    print("Ready!")


if __name__ == "__main__":
    with open("token", "r") as f:
        token = f.read()
    bot.run(token)
