from discord.ext import commands


class Owner(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def cog_check(self, ctx):
        return await self.bot.is_owner(ctx.author)

    @commands.command()
    async def close(self, ctx):
        await ctx.message.add_reaction("👍")
        await self.bot.close()

    @commands.command()
    async def test(self, ctx):
        await ctx.send("Working!")


def setup(bot):
    bot.add_cog(Owner(bot))
