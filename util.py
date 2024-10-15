import functools
import discord

import db
import lcapi


def create_embed(message: str):
    embed = discord.Embed(color=0xFFAE00)
    embed.description = message
    return embed


def create_profile_embed(info: dict, lc_info: dict, title: str, avatar):
    embed = discord.Embed(color=0xFFAE00)
    embed.title = title

    if not avatar:
        url = "https://cdn.discordapp.com/embed/avatars/0.png"
    else:
        url = avatar.url

    embed.set_thumbnail(url=url)

    embed.add_field(name="LC User", value=info["leetcode_handle"])
    if info["rank"] == "Champion":
        embed.add_field(name="Rank", value=f"{info['rank']} ({info['champion_lp']} LP)")
    else:
        embed.add_field(name="Rank", value=info["rank"])

    embed.add_field(name="Tickets", value=info["tickets"])
    embed.add_field(name="Easies", value=lc_info["EASY"])
    embed.add_field(name="Mediums", value=lc_info["MEDIUM"])
    embed.add_field(name="Hards", value=lc_info["HARD"])
    embed.set_footer(
        text="Number of solved questions are not realtime - sync with /sync"
    )

    return embed


def user_command(fetch_lc=False):
    def wrapper(func):
        @functools.wraps(func)
        async def wrapped(interaction: discord.Interaction, *args, **kwargs):
            user_data = await db.get_info(interaction.user.id)

            async def noop(interaction: discord.Interaction, *args, **kwargs):
                await interaction.response.send_message(
                    embed=create_embed("You don't have an account linked!"),
                    ephemeral=True,
                )

            if not user_data:
                return await noop(interaction, *args, **kwargs)

            if fetch_lc:
                lc_info = await lcapi.get_solve_count(user_data["leetcode_handle"])
            else:
                lc_info = None

            interaction.data["injected"] = (user_data, lc_info)

            return await func(interaction, *args, **kwargs)

        return wrapped

    return wrapper
