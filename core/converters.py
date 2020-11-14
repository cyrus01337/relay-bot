import discord
from discord.ext import commands

from .errors import GuildNotFound


class Guild(commands.Converter):
    async def convert(self, ctx, argument):
        guild_found = discord.utils.find(lambda g: g.name == argument,
                                         ctx.bot.guilds)

        if not guild_found:
            # convert to  manipulate guild id
            try:
                return ctx.bot.get_guild(int(argument))
            except ValueError:
                raise GuildNotFound
        return guild_found
