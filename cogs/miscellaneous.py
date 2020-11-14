import discord
from discord.ext import commands


class Miscellaneous(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

        self.invite = None
        self.permissions = discord.Permissions(
            send_messages=True,
            read_messages=True,
            add_reactions=True,
            manage_webhooks=True,
            attach_files=True,
            embed_links=True
        )

        bot.loop.create_task(self.__ainit__())

    async def __ainit__(self):
        await self.bot.wait_until_ready()
        self.invite = discord.utils.oauth_url(str(self.bot.user.id),
                                              self.permissions)

    @commands.command()
    async def invite(self, ctx):
        await ctx.send(embed=discord.Embed(
            title="Invite",
            description=f"[URL]({self.invite})"
        ))


def setup(bot):
    bot.add_cog(Miscellaneous(bot))
