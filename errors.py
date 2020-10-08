import discord
from discord.ext import commands


class WebhookNotFound(Exception):
    pass


class GuildNotFound(commands.CommandError):
    def __init__(self):
        self.embed = discord.Embed(
            title="Nope!",
            description="The guild doesn't exist using the given identifier!"
        )
