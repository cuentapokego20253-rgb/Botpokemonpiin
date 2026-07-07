import os
import discord
import re
from discord.ext import commands
from flask import Flask
from threading import Thread

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

CANALES_ESPEJO = {
    1522694582171599011: 1522738552587157536,
    1522694783280349345: 1523963115467837480,
    1522695765301133312: 1523907433590296064,
    1522695933031219491: 1523907607936826392,
    1522707464450192230: 1523964283484901476,
}

PORY_ID = int(os.environ['POKEMON_BOT_ID'])
MAPS_KEY = os.environ['GOOGLE_MAPS_API_KEY']

@bot.event
async def on_ready():
    print(f'Bot conectado')
    keep_alive()

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    if message.author.id == PORY_ID and message.channel.id in CANALES_ESPEJO:
        if not message.embeds:
            return

        for embed in message.embeds:
            nuevo_embed = embed.copy()
            embed_texto = str(embed.to_dict())
            coords = re.search(r'(-?\d{1,2}\.\d{3,})(?:,|%2C)\s*(-?\d{1,3}\.\d{3,})', embed_texto)
            
            if coords:
                lat, lon = coords.groups()
                api_map_url = f"https://maps.googleapis.com/maps/api/staticmap?center={lat},{lon}&zoom=15&size=600x300&key={MAPS_KEY}"
                nuevo_embed.set_image(url=api_map_url)
            
            canal_destino = bot.get_channel(CANALES_ESPEJO[message.channel.id])
            if canal_destino:
                await canal_destino.send(embed=nuevo_embed)

bot.run(os.environ['DISCORD_TOKEN'])
