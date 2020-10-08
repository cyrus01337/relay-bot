from collections.abc import Callable
from typing import Union

import discord
from discord.ext import commands

import errors
import utils


class Connection(object):
    def __init__(self,
                 source: discord.TextChannel,
                 dest: discord.TextChannel, *,
                 bot):
        self.webhook = None
        self.source = source
        self.dest = dest
        self.bot = bot

    def __repr__(self):
        return (f"<Connection source={self.source} dest={self.dest} "
                f"webhook={self.webhook}>")

    @classmethod
    def invert(cls, connection):
        return cls(connection.dest, connection.source, bot=connection.bot)


class RelayBot(commands.Bot):
    def __init__(self, *args, **kwargs):
        super().__init__(
            command_prefix="arcy ",
            intents=discord.Intents.all(),
            *args,
            **kwargs
        )
        self._connections = {}
        self._ignored_commands = []
        self._ignored_errors = (
            commands.CommandNotFound,
        )
        self._avatar_bytes = None
        self._allowed_mentions = discord.AllowedMentions(everyone=False,
                                                         roles=False)

        self.loop.create_task(self.__ainit__())

    async def __ainit__(self):
        await self.wait_until_ready()
        self._avatar_bytes = await self.user.avatar_url.read()

    def _attempt_get(self,
                     identifier: Union[int, str], *,
                     function: Callable,
                     iterable: list):
        result = None

        if isinstance(identifier, int):
            result = function(identifier)
        else:
            result = discord.utils.get(iterable, name=identifier)
        return result

    def _resolve_identifier(self, ctx: commands.Context):
        guild_in_kwargs = ctx.kwargs.get("guild", False)

        if guild_in_kwargs:
            if isinstance(guild_in_kwargs, (int, str)):
                return guild_in_kwargs
        for arg in ctx.args:
            if isinstance(arg, (int, str)):
                return arg
        return None

    def _can_read_write(self, channel: discord.TextChannel):
        permissions = channel.permissions_for(channel.guild.me)

        return permissions.send_messages and permissions.read_messages

    # fix "_check_existing_guild()" first
    # def bypass_guild_check(self, _):
    #     def predicate(ctx):
    #         self._ignored_commands.append(ctx.command.name)
    #         return True
    #     return commands.check(predicate)

    async def _init_webhooks(self,
                             dest: discord.TextChannel,
                             source: discord.TextChannel):
        ret = []

        for channel in (dest, source):
            webhooks = await channel.webhooks()
            webhook_found = discord.utils.get(webhooks,
                                              name="Relay",
                                              user=self.user)

            if not webhook_found:
                webhook_found = await channel.create_webhook(
                    name="Relay",
                    avatar=self._avatar_bytes
                )
            ret.append(webhook_found)
        return ret

    async def _connect(self,
                       source: discord.TextChannel,
                       dest: discord.TextChannel):
        # if one point does not exist nor will the other
        if self._connections.get(dest.id, None) is None:
            webhooks = await self._init_webhooks(dest, source)
            source_connection = Connection(source, dest, bot=self)
            dest_connection = Connection(dest, source, bot=self)

            for i, c in enumerate((source_connection, dest_connection)):
                try:
                    webhook = webhooks[i]
                except IndexError:
                    webhook = None
                finally:
                    c.webhook = webhook

            self._connections[source.id] = source_connection
            self._connections[dest.id] = dest_connection
            # self._connections[dest.id] = Connection.invert(source_connection)

    async def _disconnect(self, source: discord.TextChannel):
        try:
            connection = self._connections.pop(source.id)
        except KeyError:
            return
        else:
            ret = (connection.source, connection.dest)
            self._connections.pop(connection.dest.id)
        return ret

    async def process_connections(self, message: discord.Message):
        prefix = await self.get_prefix(message)
        if message.author.bot or message.content.startswith(prefix):
            return
        connection = self._connections.get(message.channel.id, None)

        if connection is not None:
            files = []

            for attachment in message.attachments:
                file = await attachment.to_file()
                files.append(file)
            await connection.webhook.send(
                message.content,
                username=message.author.name,
                avatar_url=message.author.avatar_url,
                files=files,
                allowed_mentions=self._allowed_mentions)

    def get_guild(self, identifier: Union[int, str]):
        return self._attempt_get(identifier,
                                 function=super().get_guild,
                                 iterable=bot.guilds)

    def get_channel(self,
                    identifier: Union[int, str], *,
                    guild: discord.Guild):
        return self._attempt_get(identifier,
                                 function=super().get_channel,
                                 iterable=guild.text_channels)

    def run(self):
        super().run(utils.get_token())

    async def on_ready(self):
        print(self.user)

    async def on_typing(self, channel, *_):
        if self._connections.get(channel.id, None) is not None:
            await channel.trigger_typing()

    async def on_message(self, message):
        await self.process_connections(message)
        await self.process_commands(message)

    async def on_command_error(self, ctx, error):
        error = getattr(error, "original", error)

        if isinstance(error, self._ignored_errors):
            pass
        elif isinstance(error, errors.GuildNotFound):
            await ctx.send(embed=error.embed)
        else:
            raise error


bot = RelayBot()
bot.load_extension("jishaku")
main = bot.run


# issue if converted into decorator - see "log.txt" for more info
def _check_existing_guild(ctx):
    if ctx.command.name in bot._ignored_commands:
        return True
    identifier = bot._resolve_identifier(ctx)

    if bot.get_guild(identifier):
        return True
    else:
        raise errors.GuildNotFound()


# helper function and error handler do the heavy lifting
@bot.command()
async def get(ctx, *, guild: Union[int, str]):
    _check_existing_guild(ctx)
    await ctx.send(embed=discord.Embed(
        title="Yep!",
        description="You are able to connect to it!"
    ))


@bot.command()
async def connect(ctx,
                  guild: Union[int, str],
                  channel: Union[int, str]):
    _check_existing_guild(ctx)
    embed = None
    guild = bot.get_guild(guild)
    channel = bot.get_channel(channel, guild=guild)

    if channel is None:
        embed = discord.Embed(
            title="Uh...",
            description="That channel doesn't seem to exist"
        )

    if embed is None:
        if channel == ctx.channel:
            embed = discord.Embed(title="WIP", description="WIP")
        elif not bot._can_read_write(channel):
            embed = discord.Embed(title="WIP", description="WIP")
        elif bot._connections.get(ctx.channel.id, None) is not None:
            embed = discord.Embed(title="WIP", description="WIP")
        else:
            channels = (ctx.channel, channel)
            title = "Success!"
            description = ("You have been connected. You will now receive "
                           "messages from `#{}` and can also send messages to "
                           "`#{}` also! Go ahead, start typing!")
            embed = discord.Embed(title=title,
                                  description=description.format(*channels))

            await channel.send(embed=discord.Embed(
                title=title,
                description=description.format(*channels[::-1])
            ))
            await bot._connect(*channels)
    await ctx.send(embed=embed)


@bot.command()
async def disconnect(ctx):
    channels = await bot._disconnect(ctx.channel)

    for channel in channels:
        await channel.send(embed=discord.Embed(
            title="Notice",
            description=("The connection has been severed... You have been "
                         "disconnected!")
        ))


@bot.command()
# @bot.bypass_guild_check
@commands.is_owner()
async def close(ctx):
    await ctx.message.add_reaction("👍")
    await bot.close()


@bot.command()
async def test(ctx, channel: Union[int, str]):
    await ctx.send(f"{type(channel)}")


if __name__ == '__main__':
    main()
