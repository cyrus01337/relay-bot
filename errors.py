import discord
from discord.ext import commands


# potentially redundant - only used in try/except with "pass" statement
# class RelayConnectionError(Exception):
#     def __init__(self, channel: discord.TextChannel):
#         self.message = (f"connection has not been established with channel "
#                         f"(ID: {channel.id})")


class GuildNotFound(commands.CommandError):
    def __init__(self):
        self.embed = discord.Embed(
            title="Nope!",
            description="The guild doesn't exist using the given identifier!"
        )
