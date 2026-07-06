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
    # Configuración de los canales de origen y destino
    CANAL_ORIGEN = 1522694582171599011
    CANAL_DESTINO = 1522738552587157536

    # Ignorar mensajes propios del bot para evitar bucles
    if message.author == bot.user:
        return

    # Verificar si el mensaje viene del canal 100A
    if message.channel.id == CANAL_ORIGEN:
        destino = bot.get_channel(CANAL_DESTINO)
        
        # Si el canal destino existe, procedemos a reenviar
        if destino:
            # Reenviar texto si el mensaje tiene contenido escrito
            if message.content:
                await destino.send(message.content)
            
            # Reenviar la tarjeta (embed) con el mapa que envía PoryPro
            for embed in message.embeds:
                await destino.send(embed=embed)
            
            print(f"DEBUG: Mensaje reenviado correctamente al canal 100B")

    await bot.process_commands(message)

bot.run(os.environ['DISCORD_TOKEN'])
