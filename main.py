import os
import discord
import re
import math
from discord.ext import commands
from flask import Flask
from threading import Thread

# Servidor Flask para mantener el proceso vivo
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot activo"

def run():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run)
    t.daemon = True
    t.start()

# Configuración
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

MAPS_KEY = os.environ.get('GEOAPIFY_API_KEY')

def hacer_circulo_perfecto(lat, lon, radio_metros):
    R = 6378137.0
    cx = math.radians(lon) * R
    cy = math.log(math.tan(math.pi / 4 + math.radians(lat) / 2)) * R
    pts = []
    for a in range(0, 361, 15):
        rad = math.radians(a)
        x = cx + radio_metros * math.cos(rad)
        y = cy + radio_metros * math.sin(rad)
        lon_i = math.degrees(x / R)
        lat_i = math.degrees(2 * math.atan(math.exp(y / R)) - math.pi / 2.0)
        pts.append(f"|{lat_i:.6f},{lon_i:.6f}")
    return "".join(pts)

@bot.event
async def on_message(message):
    if message.author == bot.user or message.channel.id not in CANALES_ESPEJO or not message.embeds:
        return

    for embed in message.embeds:
        nuevo_embed = embed.copy()
        embed_texto = str(embed.to_dict()).replace('%2C', ',')
        
        # Lógica de extracción original (la que funcionaba)
        lat_f = None
        lon_f = None
        
        coords_match = re.search(r'(?:q|center|query|loc|ll)=?(-?\d{1,2}\.\d+)\s*,\s*(-?\d{1,3}\.\d+)', embed_texto)
        if coords_match:
            try:
                lat_f = float(coords_match.group(1))
                lon_f = float(coords_match.group(2))
            except: pass

        if lat_f is not None and lon_f is not None:
            print(f"Coordenadas detectadas: Lat {lat_f}, Lon {lon_f}", flush=True)
            c40 = hacer_circulo_perfecto(lat_f, lon_f, 40)
            c80 = hacer_circulo_perfecto(lat_f, lon_f, 80)
            
            # URL ajustada específicamente para Geoapify
            map_url = (
                f"https://maps.geoapify.com/v1/staticmap?"
                f"style=osm-bright&width=600&height=300&scale=2&"
                f"center=lon:{lon_f},lat:{lat_f}&zoom=16&"
                f"marker=lon:{lon_f},lat:{lat_f};color:%23ff0000;size:large&"
                f"path=color:%23ff0000;width:2{c40}&"
                f"path=color:%230000ff;width:2{c80}&"
                f"apiKey={MAPS_KEY}"
            )
            nuevo_embed.set_image(url=map_url)
        else:
            print("No se encontraron coordenadas en el embed.", flush=True)

        canal_destino = bot.get_channel(CANALES_ESPEJO[message.channel.id])
        if not canal_destino:
            try: canal_destino = await bot.fetch_channel(CANALES_ESPEJO[message.channel.id])
            except: pass
        if canal_destino:
            await canal_destino.send(embed=nuevo_embed)

keep_alive()
bot.run(os.environ['DISCORD_TOKEN'])
