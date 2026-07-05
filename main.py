import os
import discord
from discord.ext import commands
from flask import Flask
from threading import Thread
import re

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
    print(f"DEBUG: Autor: {message.author.id}")
    print(f"DEBUG: Mensaje recibido en canal {message.channel.id} de autor {message.author.id} (Nombre: {message.author.name})")
    # Ignorar mensajes propios
    if message.author == bot.user:
        return

    # Verificar si el mensaje viene de PoryPro y del canal 100A 
    print(f"DEBUG: Mensaje del canal {message.channel.id} y autor {message.author.id}")
    #if message.author.id == PORY_ID and message.channel.id == SOURCE_ID:
    content = message.content
    # Buscar coordenadas en el mensaje (ejemplo: @-33.123, -71.123)
    coords = re.findall(r'@(-?\d+.\d+),\s*(-?\d+.\d+)', content)

    if coords:
        lat, lon = coords[0]
        map_url = f"https://maps.googleapis.com/maps/api/staticmap?center={lat},{lon}&zoom=15&size=600x300&markers=color:red%7C{lat},{lon}&key={MAPS_KEY}"

# Crear y enviar el mensaje con el mapa al canal 100B,
canal_destino = bot.get_channel(DEST_ID)
if canal_destino:
    embed = discord.Embed(title="Nueva ubicación detectada", description=content)
    embed.set_image(url=map_url)
    await canal_destino.send(embed=embed)

await bot.process_commands(message)

bot.run(os.environ['DISCORD_TOKEN'])
