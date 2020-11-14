import asyncio
from typing import Union

import discord
from discord.ext import commands

from core import Connection
from core.converters import Guild
from core.errors import WebhookInitFailed


class Core(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

        self.webhook = None

    async def _connect(self,
                       source: discord.TextChannel,
                       dest: discord.TextChannel):
        # if one point does not exist nor will the other
        if self.bot._connections.get(dest.id, None) is None:
            webhooks = await self.get_webhooks_for(dest, source)
            source_connection = Connection(source, dest)
            dest_connection = Connection(dest, source)

            for i, c in enumerate((source_connection, dest_connection)):
                try:
                    webhook = webhooks[i]
                except IndexError:
                    webhook = None
                finally:
                    c.webhook = webhook

            self.bot._connections[source.id] = source_connection
            self.bot._connections[dest.id] = dest_connection

    async def _disconnect(self, source: discord.TextChannel):
        try:
            connection = self.bot._connections.pop(source.id)
        except KeyError:
            return ()
        else:
            ret = (connection.source, connection.dest)
            self.bot._connections.pop(connection.dest.id)
        return ret

    async def get_webhooks_for(self,
                               dest: discord.TextChannel,
                               source: discord.TextChannel):
        ret = []

        for channel in (dest, source):
            webhooks = await channel.webhooks()
            webhook_found = discord.utils.get(webhooks,
                                              name="Relay",
                                              user=self.bot.user)

            if not webhook_found:
                try:
                    webhook_found = await channel.create_webhook(
                        name="Relay",
                        avatar=self.bot._avatar_bytes
                    )
                except discord.Forbidden:
                    raise WebhookInitFailed
            ret.append(webhook_found)
        return ret

    async def cog_check(self, ctx):
        return True

    @commands.Cog.listener()
    async def on_message(self, message):
        # housed function in RelayBot class to enable overwritability
        # via inheritance
        await self.bot.process_connections(message)

    # cog check & error handler perform majority of the heavy lifting
    @commands.command()
    async def get(self, ctx, *, guild: Guild):
        await ctx.send(embed=discord.Embed(
            title="Yep!",
            description="You are able to connect to it!"
        ))

    @commands.command()
    async def connect(self,
                      ctx,
                      guild: Guild,
                      channel: Union[int, str]):
        embed = None
        channel = self.bot.get_channel(channel, guild=guild)

        if channel is None:
            embed = discord.Embed(
                title="Uh...",
                description="That channel doesn't seem to exist"
            )

        if embed is None:
            if channel == ctx.channel:
                embed = discord.Embed(title="WIP", description="WIP")
            elif not self.bot.is_rw(channel):
                embed = discord.Embed(title="WIP", description="WIP")
            elif self.bot._connections.get(ctx.channel.id, None) is not None:
                embed = discord.Embed(title="WIP", description="WIP")
            else:
                channels = (ctx.channel, channel)
                title = "Success!"
                description = ("You have been connected. You will now receive "
                               "messages from `#{}` and can also send messages "
                               "to `#{}` also! Go ahead, start typing!")
                embed = discord.Embed(title=title,
                                      description=description.format(*channels))

                await self._connect(*channels)
                await channel.send(embed=discord.Embed(
                    title=title,
                    description=description.format(*channels[::-1])
                ))
        await ctx.send(embed=embed)

    @commands.command()
    async def disconnect(self, ctx):
        channels = await self._disconnect(ctx.channel)

        for channel in channels:
            await channel.send(embed=discord.Embed(
                title="Notice",
                description=("The connection has been severed... You have been "
                             "disconnected!")
            ))


def setup(bot):
    bot.add_cog(Core(bot))
