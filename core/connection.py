import asyncio

import discord


class Connection(object):
    TIMEOUT = 60

    def __init__(self,
                 source: discord.TextChannel,
                 dest: discord.TextChannel):
        self._timeout_task = None
        self.webhook = None
        self.source = source
        self.dest = dest
        self.loop = asyncio.get_event_loop()
        self.send = self.webhook.send

    def __repr__(self):
        return (f"<Connection source={self.source} dest={self.dest} "
                f"webhook={self.webhook}>")
