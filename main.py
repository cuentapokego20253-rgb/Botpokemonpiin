import os
import discord
import re
import math
import json
import urllib.parse
from discord.ext import commands
from flask import Flask
from threading import Thread

# Flask para mantener vivo Render
app = Flask(__name__)
@app.route('/')
def home():
    return "Bot activo"

def run_flask():
    app.run(host='0.0.0.0', port=8080)

# Iniciar Flask
Thread(target=run_flask, daemon=True).start()

# Configuración del Bot
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

CANALES_ESPEJO = {
    1522694582171599011: 1522738552587157536,
    1522694783280349345: 1523963115467837480,
    1522695765301133312: 1523907438590296064,
    1522695933031219491: 1523907697936826392,
    1522707464150192230: 1523964283484901476,
    1522711485586079895: 1525184002011431082,
    1522728127565140008: 1525183874852978728
}

def hacer_circulo_perfecto(lat, lon, radio):
    R = 6378137.0
    cx = math.radians(lon) * R
    cy = math.log(math.tan(math.pi / 4 + math.radians(lat) / 2)) * R
    pts = []
    for a in range(0, 361, 15):
        rad = math.radians(a)
        x = cx + radio * math.cos(rad)
        y = cy + radio * math.sin(rad)
        lon_i = math.degrees(x / R)
        lat_i = math.degrees(2 * math.atan(math.exp(y / R)) - math.pi / 2.0)
        pts.append([round(lon_i, 6), round(lat_i, 6)])
    return pts + [pts[0]]

@bot.event
async def on_ready():
    print('>>> BOT CONECTADO Y LISTO <<<')

@bot.event
async def on_message(message):
    if message.author == bot.user or message.channel.id not in CANALES_ESPEJO:
        return

    if message.embeds:
        try:
            embed = message.embeds[0]
            nuevo_embed = embed.copy()
            texto = str(embed.to_dict())
            
            coords = re.search(r'(-?\d{1,2}\.\d+),\s*(-?\d{1,3}\.\d+)', texto)
            if coords:
                lat, lon = float(coords.group(1)), float(coords.group(2))
                c40 = hacer_circulo_perfecto(lat, lon, 40)
                c80 = hacer_circulo_perfecto(lat, lon, 80)
                
                geo = {"type": "FeatureCollection", "features": [
                    {"type": "Feature", "geometry": {"type": "Polygon", "coordinates": [c80]}, "properties": {"stroke": "#0000FF"}},
                    {"type": "Feature", "geometry": {"type": "Polygon", "coordinates": [c40]}, "properties": {"stroke": "#FF0000"}}
                ]}
                
                url_map = f"https://api.mapbox.com/styles/v1/mapbox/light-v11/static/geojson({urllib.parse.quote(json.dumps(geo))})/{lon},{lat},16,0,0/600x300@2x?access_token={os.environ.get('MAPBOX_API_KEY')}"
                nuevo_embed.set_image(url=url_map)
            
            canal_destino = bot.get_channel(CANALES_ESPEJO[message.channel.id])
            if canal_destino:
                await canal_destino.send(embed=nuevo_embed)
        except Exception as e:
            print(f"Error: {e}")

if __name__ == '__main__':
    bot.run(os.environ['DISCORD_TOKEN'])
