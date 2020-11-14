from discord.ext import commands


class ErrorHandler(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.ignored = (
            commands.CommandNotFound,
        )

    async def on_command_error(self, ctx, error):
        error = getattr(error, "original", error)

        if isinstance(error, self.ignored):
            print("Ignored:", error)
        elif hasattr(error, "embed"):
            await ctx.send(embed=error.embed)
        else:
            raise error


def setup(bot):
    bot.add_cog(ErrorHandler(bot))
