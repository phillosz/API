import discord
from discord.ext import commands

# Nastavení přístupu bota
intents = discord.Intents.default()
intents.message_content = True  # Povolení čtení obsahu zpráv

bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f"{bot.user.name} je přihlášen a připraven.")

@bot.command()
async def ping(ctx):
    await ctx.send("Pong!")

@bot.command(name="helpme")
async def help_me(ctx):
    await ctx.send("Dostupné příkazy: !ping, !helpme")

bot.run("MTMyNjkxMDY4MjA0NTc0MzE1NA.G4W2-Y.H4jux_lnuRTpkxDJrMXUMgNcQ7nqFkY7qPGZcs")
