import discord
from discord.ext import commands
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)
@bot.event
async def on_ready():
   print(f'Bot conectado como {bot.user}')
@bot.event
async def on_message(message):
    await bot.process_commands(message)
bot.run('MTUyMjc3NjYzODI2ODM3NTA5MA.GD_9Sv.GPRT3QkMYGsWCKVBV9Xn79XlXV5kSH5AjraOqM')
