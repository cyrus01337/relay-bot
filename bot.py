from collections.abc import Callable
from typing import Union

import discord
from discord.ext import commands

import errors
import utils


# better system - 1 connection, "source" & "dest" but only send to
# "dest" from source to make lookup & communication easier
class Connection(object):
    def __init__(self,
                 source: discord.TextChannel,
                 dest: discord.TextChannel, *,
                 bot):
        self.webhook = None
        self.source = source
        self.dest = dest
        self.bot = bot

    @classmethod
    def invert(cls, connection):
        return cls(connection.dest, connection.source, bot=connection.bot)

    # potentially unnecessary
    # def resolve(self, *args):
    #     source = None
    #     dest = None

    #     for arg in args:
    #         if arg == self.source:
    #             source = arg
    #         elif arg == self.dest:
    #             dest = arg
    #         elif None not in (source, dest):
    #             break
    #     return source, dest


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

    # potentially redundant - overhead by only wrapping 1 call
    # def _get_connection_points(self, channel: discord.TextChannel):
    #     # can be improved - "channel" already exists as source/dest
    #     # point, unsure how to solve efficiently
    #     return self._connections.get(channel.id, None)

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
                             source: discord.TextChannel,
                             dest: discord.TextChannel):
        webhooks = []

        for channel in (source, dest):
            webhooks = await channel.webhooks()
            webhook_found = discord.utils.get(webhooks,
                                              name="Relay",
                                              user=self.user)

            if not webhook_found:
                print("k")
                webhook_found = await channel.create_webhook(
                    name="Relay",
                    avatar=self._avatar_bytes
                )
            print("l")
            webhooks.append(webhook_found)
        return webhooks

    async def _connect(self,
                       source: discord.TextChannel,
                       dest: discord.TextChannel):
        # if one point does not exist nor will the other
        if self._connections.get(dest.id, None) is None:
            print("g")
            webhooks = await self._init_webhooks(source, dest)
            print(source.name, dest.name)
            source_connection = Connection(source, dest, bot=self)
            dest_connection = Connection(dest, source, bot=self)

            for i, c in enumerate((source_connection, dest_connection)):
                try:
                    webhook = webhooks[i]
                    print("h", i)
                except IndexError:
                    print("i", i)
                    webhook = None
                finally:
                    c.webhook = webhook

            self._connections[source.id] = source_connection
            self._connections[dest.id] = dest_connection
            # self._connections[dest.id] = Connection.invert(source_connection)
        print("j")

    async def _disconnect(self, source: discord.TextChannel):
        try:
            connection = self._connections.pop(source.id)
        except KeyError:
            return
        else:
            self._connections.pop(connection.dest.id)

    async def process_connections(self, message: discord.Message):
        if message.author.bot:
            return
        connection = self._connections.get(message.channel.id, None)
        print(message.channel.name, message.channel.id, connection)

        if connection is not None:
            files = []
            allowed_mentions = discord.AllowedMentions(everyone=False,
                                                       roles=False)

            for attachment in message.attachments:
                file = await attachment.to_file()
                files.append(file)
            await connection.webhook.send(message.content,
                                          username=message.author.name,
                                          avatar_url=message.author.avatar_url,
                                          files=files,
                                          allowed_mentions=allowed_mentions)

        # try:
        #     connection = self._get_connection_points(message.channel)
        # except errors.RelayConnectionError:
        #     pass
        # else:
        #     await connection.send(message)

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
                  channel: Union[discord.TextChannel, int, str]):
    _check_existing_guild(ctx)
    embed = None
    guild = bot.get_guild(guild)

    # chain conditions as checksum to verify connection circumstances
    if not isinstance(channel, discord.TextChannel):
        print("a")
        channel = bot.get_channel(channel, guild=guild)

        if channel is None:
            embed = discord.Embed(
                title="Uh...",
                description="That channel doesn't seem to exist"
            )

    if embed is None:
        print("b")
        if channel == ctx.channel:
            print("c")
            embed = discord.Embed(title="WIP", description="WIP")
        elif not bot._can_read_write(channel):
            print("d")
            embed = discord.Embed(title="WIP", description="WIP")
        elif bot._connections.get(ctx.channel.id, None) is not None:
            print("e")
            embed = discord.Embed(title="WIP", description="WIP")
        else:
            print("f")
            embed = discord.Embed(
                title="Success!",
                description=("You have been connected. You will now receive "
                             "messages from the channel and can also send "
                             "messages to it also! Go ahead, start typing!")
            )
            await bot._connect(ctx.channel, channel)
    await ctx.send(embed=embed)


@bot.command()
async def disconnect(ctx):
    await bot._disconnect(ctx)
    await ctx.send()


@bot.command()
# @bot.bypass_guild_check
@commands.is_owner()
async def close(ctx):
    await ctx.message.add_reaction("👍")
    await bot.close()


if __name__ == '__main__':
    main()
