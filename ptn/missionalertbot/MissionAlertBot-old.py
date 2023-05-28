













































#
# error handling
#
@bot.event
async def on_command_error(ctx, error):
    gif = random.choice(error_gifs)
    if isinstance(error, commands.BadArgument):
        await ctx.send(f'**Bad argument!** {error}')
    elif isinstance(error, commands.CommandNotFound):
        await ctx.send("**Invalid command.**")
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send("**Sorry, that didn't work**.\n• Check you've included all required arguments. Use `m.help <command>` for details."
                       "\n• If using quotation marks, check they're opened *and* closed, and are in the proper place.\n• Check quotation"
                       " marks are of the same type, i.e. all straight or matching open/close smartquotes.")
    elif isinstance(error, commands.MissingPermissions):
        await ctx.send('**You must be a Carrier Owner to use this command.**')
    else:
        await ctx.send(gif)
        await ctx.send(f"Sorry, that didn't work. Check your syntax and permissions, error: {error}")

bot.run(TOKEN)
