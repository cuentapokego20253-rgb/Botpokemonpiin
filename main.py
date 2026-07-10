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
    1522695765301133312: 1523907438590296064,
    1522695933031219491: 1523907697936826392,
    1522707464150192230: 1523964283484901476,
    1522711485586079895: 1525184002011431082,
    1522728127565140008: 1525183874852978728,
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
                import math
                lat_f, lon_f = float(lat), float(lon)
                c40 = "".join([f"|{lat_f + (40/111320.0)*math.cos(i*math.pi/12):.6f},{lon_f + (40/(111320.0*math.cos(lat_f*math.pi/180)))*math.sin(i*math.pi/12):.6f}" for i in range(25)])
                c80 = "".join([f"|{lat_f + (80/111320.0)*math.cos(i*math.pi/12):.6f},{lon_f + (80/(111320.0*math.cos(lat_f*math.pi/180)))*math.sin(i*math.pi/12):.6f}" for i in range(25)])
                api_map_url = f"https://maps.googleapis.com/maps/api/staticmap?center={lat},{lon}&zoom=17&markers=color:red%7C{lat},{lon}&size=600x300&path=color:0xFF0000|weight:2{c40}&path=color:0x0000FF|weight:2{c80}&key={MAPS_KEY}"
                canal_destino = bot.get_channel(CANALES_ESPEJO[message.channel.id])
            if canal_destino:
                await canal_destino.send(embed=nuevo_embed)

bot.run(os.environ['DISCORD_TOKEN'])
