import os
import discord
import re
import math
from discord.ext import commands
from flask import Flask
from threading import Thread

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

# --- AQUÍ ESTÁ LA FÓRMULA MATEMÁTICA RESTAURADA ---
def hacer_circulo_perfecto(lat, lon, radio_metros, num_puntos=32):
    coordenadas = []
    radio_tierra = 6378137.0 # Radio de la Tierra en metros
    for i in range(num_puntos + 1): # +1 para cerrar el polígono conectando con el primer punto
        angulo = math.radians(float(i) / num_puntos * 360.0)
        dx = radio_metros * math.cos(angulo)
        dy = radio_metros * math.sin(angulo)
        factor_correccion = 1.5 
        d_lat = ((dy / radio_tierra) * (180.0 / math.pi)) / factor_correccion
        d_lon = ((dx / (radio_tierra * math.cos(math.radians(lat)))) * (180.0 / math.pi)) / factor_correccion
        
        # Geoapify requiere formato "longitud,latitud"
        coordenadas.append(f"{lon + d_lon:.6f},{lat + d_lat:.6f}")
    
    return ",".join(coordenadas)
# --------------------------------------------------

@bot.event
async def on_message(message):
    if message.author == bot.user or message.channel.id not in CANALES_ESPEJO or not message.embeds:
        return

    for embed in message.embeds:
        nuevo_embed = embed.copy()
        embed_texto = str(embed.to_dict()).replace('%2C', ',')
        
        lat_f = None
        lon_f = None
        
        # Regex original intacta
        coords_match = re.search(r'(?:q|center|query|loc|ll)=?(-?\d{1,2}\.\d+)\s*,\s*(-?\d{1,3}\.\d+)', embed_texto)
        if not coords_match:
            coords_match = re.search(r'(-?\d{1,2}\.\d{3,})\s*,\s*(-?\d{1,3}\.\d{3,})', embed_texto)
            
        if coords_match:
            lat_f = float(coords_match.group(1))
            lon_f = float(coords_match.group(2))

        if lat_f is not None and lon_f is not None:
            # Calculamos las coordenadas del polígono
            c40 = hacer_circulo_perfecto(lat_f, lon_f, 40)
            c80 = hacer_circulo_perfecto(lat_f, lon_f, 80)

            # Insertamos los polígonos matemáticos en Geoapify
            map_url = (
                f"https://maps.geoapify.com/v1/staticmap?"
                f"style=osm-bright&width=600&height=300&"
                f"center=lonlat:{lon_f},{lat_f}&zoom=15.5&"
                f"marker=lonlat:{lon_f},{lat_f};color:%23ff0000;size:large&"
                f"geometry=polygon:{c40};linewidth:2;linecolor:%23ff0000;fillopacity:0|"
                f"polygon:{c80};linewidth:2;linecolor:%230000ff;fillopacity:0&"
                f"apiKey={MAPS_KEY}"
            )
            
            print(f"DEBUG URL: {map_url}")
            nuevo_embed.set_image(url=map_url)

        canal_destino = bot.get_channel(CANALES_ESPEJO[message.channel.id])
        if canal_destino:
            await canal_destino.send(embed=nuevo_embed)

keep_alive()
bot.run(os.environ['DISCORD_TOKEN'])
