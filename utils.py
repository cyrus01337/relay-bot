import os
import traceback


def _key(value: str):
    return str.lower(value[0])


def get_token():
    with open("_TOKEN", "r") as f:
        return str.strip(f.read())


def load_cogs(*, bot):
    with open("log.txt", "w") as log:
        cogs = os.listdir("cogs")
        cogs.append("jishaku")
        log.write("Loading cogs...\n\n")

        for obj in sorted(cogs, key=_key):
            if obj.startswith("_"):
                continue
            error = None
            path = ""
            output = ""
            message = ""
            cog = obj.replace(".py", "")

            try:
                log.write(f"[{cog}]\n")

                if cog == "jishaku":
                    path = cog
                else:
                    path = f"cogs.{cog}"
                bot.load_extension(path)
            except Exception as err:
                print(err, type(error))
                error = err
                output = f"Failed to load {cog}"
                message = f'[X] {output} (see "log.txt" for more details)'
            else:
                output = f"Loaded {cog}"
                message = f"[ ] {output}"
            finally:
                print(message)
                log.write(f"{output}\n\n")

                if error is not None:
                    traceback.print_exception(type(error),
                                              error,
                                              error.__traceback__,
                                              file=log)
                    log.write("\n\n\n")
