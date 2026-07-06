import os
import discord
from discord.ext import commands
from flask import Flask
from threading import Thread
import re
import aiohttp
import io
# Servidor web para mantenerlo despierto,
app = Flask(__name__)
@app.route('/')
def home(): return "Bot activo"
def run(): app.run(host='0.0.0.0', port=8080)
def keep_alive():
    t = Thread(target=run)
    t.start()

intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
bot = commands.Bot(command_prefix='!', intents=intents)
async def setup_hook():
    bot.session = aiohttp.ClientSession()
# Inicializamos la sesión para descargar imágenes
#Variables configuradas en Render,
SOURCE_ID = int(os.environ['SOURCE_CHANNEL_ID'])
DEST_ID = int(os.environ['DESTINATION_CHANNEL_ID'])
PORY_ID = int(os.environ['POKEMON_BOT_ID'])
MAPS_KEY = os.environ['GOOGLE_MAPS_API_KEY']

@bot.event
async def on_ready():
    print(f'Bot conectado como {bot.user}')
    keep_alive()

@bot.event
async def on_message(message):
    if not message.embeds:
        return
        
    for embed in message.embeds:
        nuevo_embed = embed.copy()
         
         if message.components:
             for component in message.components:
                 for child in component.children:
                     if hasattr(child, 'url') and child.url and "google" in child.url:
                         coords = re.search(r'q=(-?\d+\.\d+),(-?\d+\.\d+)', child.url)
                         if coords:
                             lat, lon = coords.groups()
                             mapa_url = f"https://maps.googleapis.com/maps/api/staticmap?center={lat},{lon}&zoom=15&size=600x300&markers=color:red%7C{lat},{lon}"
                             nuevo_embed.set_image(url=mapa_url)
          await destino.send(embed=nuevo_embed)

async def main():
    async with aiohttp.ClientSession() as session:
        bot.session = session
        await bot.start(os.environ['DISCORD_TOKEN'])

keep_alive()
import asyncio
asyncio.run(main())
