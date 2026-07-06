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
    if message.author.id == PORY_ID:
        if message.channel.id == SOURCE_ID:
            destino = bot.get_channel(DEST_ID)
            if destino:
                if message.content: 
                    await destino.send(message.content)
                for embed in message.embeds:
                    await destino.send(embed=embed)
                    if message.components:
                        for component in message.components:
                            for child in component.children:
                                if hasattr(child, 'url') and child.url and "maps.google.com" in child.url:
                                    coords = re.search(r'q=(-?\d+\.\d+),(-?\d+\.\d+)', child.url)
                                    if coords:
                                    lat, lon = coords.groups()
                                    mapa_url = f"https://maps.googleapis.com/maps/api/staticmap?center={lat},{lon}&zoom=15&size=600x300&markers=color:red%7C{lat},{lon}"
                                    try:
                                        async with bot.session.get(mapa_url) as resp:
                                            if resp.status == 200:
                                                data = await resp.read()
                                                await destino.send("Mapa del hallazgo:", file=discord.File(io.BytesIO(data), filename="mapa.png"))
                                    except Exception as e:
                                        print(f"Error generando mapa: {e}")

async def main():
    async with aiohttp.ClientSession() as session:
        bot.session = session
        await bot.start(os.environ['DISCORD_TOKEN'])

keep_alive()
import asyncio
asyncio.run(main())
