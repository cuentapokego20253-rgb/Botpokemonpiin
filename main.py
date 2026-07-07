import os
import discord
import re
import aiohttp
from discord.ext import commands
from flask import Flask
from threading import Thread

# Configuración básica del bot
intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
bot = commands.Bot(command_prefix='!', intents=intents)

# Variables configuradas en Render (Environment Variables)
SOURCE_ID = int(os.environ['SOURCE_CHANNEL_ID'])
DEST_ID = int(os.environ['DESTINATION_CHANNEL_ID'])
PORY_ID = int(os.environ['POKEMON_BOT_ID'])
MAPS_KEY = os.environ['GOOGLE_MAPS_API_KEY']

# Servidor web para mantenerlo despierto en Render
app = Flask(_name_)
@app.route('/')
def home(): return "Bot activo"
def run(): app.run(host='0.0.0.0', port=8080)
def keep_alive():
    t = Thread(target=run)
    t.start()

@bot.event
async def on_ready():
    print(f'Bot conectado como {bot.user}')
    keep_alive()

@bot.event
async def on_message(message):
    # Ignorar mensajes propios
    if message.author == bot.user:
        return

    # Solo procesar si viene del bot Pory en el canal configurado
    if message.author.id == PORY_ID and message.channel.id == SOURCE_ID:
        if not message.embeds:
            return

        for embed in message.embeds:
            nuevo_embed = embed.copy()
            
            # Extraer el enlace de Google Maps desde los componentes (botones)
            map_url_found = None
            if message.components:
                for component in message.components:
                    for child in component.children:
                        if hasattr(child, 'url') and child.url and "google" in child.url:
                            map_url_found = child.url
                            break
            
            # Si hay link, generar y añadir la imagen del mapa
            if map_url_found:
                coords = re.search(r'(-?\d+\.\d+),(-?\d+\.\d+)', map_url_found)
                if coords:
                    lat, lon = coords.groups()
                    api_map_url = f"https://maps.googleapis.com/maps/api/staticmap?center={lat},{lon}&zoom=15&size=600x300&key={MAPS_KEY}"
                    nuevo_embed.set_image(url=api_map_url)
            
            # Enviar el nuevo embed al canal espejo
            canal_destino = bot.get_channel(DEST_ID)
            if canal_destino:
                await canal_destino.send(embed=nuevo_embed)

# Iniciar el bot
bot.run(os.environ['DISCORD_TOKEN'])
