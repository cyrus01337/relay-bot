import asyncio
from collections.abc import Callable
from typing import Union

import discord
from discord.ext import commands

import utils


class RelayBot(commands.Bot):
    def __init__(self, *args, **kwargs):
        super().__init__(
            command_prefix="arcy ",
            intents=discord.Intents(
                guild_messages=True,
                webhooks=True,
                guilds=True
            ),
            *args,
            **kwargs
        )
        self._avatar_bytes = None
        self._connections = {}
        self._webhook_event = asyncio.Event()
        self.webhooks = {}

        utils.load_cogs(bot=self)
        self.loop.create_task(self.__ainit__())

    async def __ainit__(self):
        await self.wait_until_ready()
        self._avatar_bytes = await self.user.avatar_url.read()
        self.webhooks = await self.cache_webhooks()

    def get(self,
            identifier: Union[int, str],
            *, function: Callable,
            iterable: list):
        if isinstance(identifier, int):
            return function(identifier)
        return discord.utils.get(iterable, name=identifier)

    def get_webhook(self, channel_id: int):
        return self.webhooks.get(channel_id, None)

    def is_rw(self, channel: discord.TextChannel):
        permissions = channel.permissions_for(channel.guild.me)

        return permissions.read_messages and permissions.send_messages

    async def cache_webhooks(self):
        ret = {}

        for guild in self.guilds:
            for channel in guild.text_channels:
                try:
                    ret[channel.id] = await channel.webhooks()
                except discord.Forbidden:
                    continue
        self._webhook_event.set()
        return ret

    async def wait_until_webhooks_ready(self):
        await self._webhook_event.wait()

    # overwritable
    async def process_connections(self, message: discord.Message):
        await self.wait_until_webhooks_ready()
        prefix = await self.get_prefix(message)
        if message.author.bot or message.content.startswith(prefix):
            return
        connection = self._connections.get(message.channel.id, None)

        if connection is not None:
            files = []

            for attachment in message.attachments:
                file = await attachment.to_file()
                files.append(file)
            await connection.send(
                message.content,
                username=message.author.display_name,
                avatar_url=message.author.avatar_url,
                files=files,
                allowed_mentions=discord.AllowedMentions(
                    everyone=False,
                    roles=False
                )
            )

    # overwritten
    def get_guild(self, identifier: Union[int, str]):
        return self.get(identifier,
                        function=super().get_guild,
                        iterable=self.guilds)

    def get_channel(self,
                    identifier: Union[int, str], *,
                    guild: discord.Guild):
        return self.get(identifier,
                        function=super().get_channel,
                        iterable=guild.text_channels)

    def run(self):
        super().run(utils.get_token())

    async def on_ready(self):
        print(f"\n{self.user}")

    async def on_typing(self, channel, *_):
        if self._connections.get(channel.id, None) is not None:
            await channel.trigger_typing()

    async def on_webhooks_update(self, channel):
        await self.wait_until_webhooks_ready()

        # keep webhooks cache substantially up to date
        if self.get_webhook(channel.id) is None:
            try:
                self.webhooks[channel.id] = await channel.webhooks()
            except discord.Forbidden:
                return


def main():
    bot = RelayBot()
    try:
        bot.run()
    except RuntimeError:
        pass


if __name__ == '__main__':
    main()
