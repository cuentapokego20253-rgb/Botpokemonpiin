import os
import discord
import re
import math
from discord.ext import commands
from flask import Flask
from threading import Thread

# Servidor Flask para mantener vivo el proceso en Render
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot activo y funcionando"

def run():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run)
    t.daemon = True
    t.start()

# Configuración de Intenciones de Discord
intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True

bot = commands.Bot(command_prefix='!', intents=intents)

# Mapeo de Canales (Tus 7 canales configurados)
CANALES_ESPEJO = {
    1522694582171599011: 1522738552587157536,
    1522694783280349345: 1523963115467837480,
    1522695765301133312: 1523907438590296064,
    1522695933031219491: 1523907697936826392,
    1522707464150192230: 1523964283484901476,
    1522711485586079895: 1525184002011431082,
    1522728127565140008: 1525183874852978728
}

# Llave API de Geoapify
MAPS_KEY = os.environ.get('GEOAPIFY_API_KEY')

# FUNCIÓN PARA HACER LOS CÍRCULOS REDONDOS PERFECTOS
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

# EXTRACCIÓN ROBUSTA ESPECÍFICA PARA EMBEDS DE TRACKERS
def extraer_coordenadas_embed(embed):
    textos_a_revisar = []
    
    # 1. Revisar URL principal del embed
    if embed.url:
        textos_a_revisar.append(embed.url)
    
    # 2. Revisar la descripción
    if embed.description:
        textos_a_revisar.append(embed.description)
        
    # 3. Revisar todos los campos (fields) donde suelen venir los links de Google Maps
    if embed.fields:
        for field in embed.fields:
            if field.name:
                textos_a_revisar.append(field.name)
            if field.value:
                textos_a_revisar.append(field.value)
                
    # 4. Incluir representación en texto plano como respaldo general
    textos_a_revisar.append(str(embed.to_dict()))

    # Buscar patrones de coordenadas o parámetros de mapas
    for texto in textos_a_revisar:
        # Buscar en URLs con q=, center=, query=, etc.
        match = re.search(r'(?:q|center|query|loc|ll)=?(-?\d{1,2}\.\d+)[,\s]+(-?\d{1,3}\.\d+)', texto)
        if match:
            try:
                lat = float(match.group(1))
                lon = float(match.group(2))
                if -90 <= lat <= 90 and -180 <= lon <= 180:
                    return lat, lon
            except Exception:
                pass

        # Buscar coordenadas directas con varios decimales
        match_coords = re.search(r'(-?\d{1,2}\.\d{3,})\s*,\s*(-?\d{1,3}\.\d{3,})', texto)
        if match_coords:
            try:
                lat = float(match_coords.group(1))
                lon = float(match_coords.group(2))
                if -90 <= lat <= 90 and -180 <= lon <= 180:
                    return lat, lon
            except Exception:
                pass

    return None, None

@bot.event
async def on_ready():
    print(f'Bot iniciado con éxito como {bot.user}')

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    if message.channel.id not in CANALES_ESPEJO:
        return

    if not message.embeds:
        return

    try:
        for embed in message.embeds:
            nuevo_embed = embed.copy()
            
            # Extraer coordenadas usando la nueva función especializada
            lat_f, lon_f = extraer_coordenadas_embed(embed)
            print(f"Mensaje detectado en canal {message.channel.id} -> Coordenadas extraídas: Lat={lat_f}, Lon={lon_f}")

            # Generar el mapa estático con Geoapify si se encontraron coordenadas
            if lat_f is not None and lon_f is not None:
                try:
                    c40 = hacer_circulo_perfecto(lat_f, lon_f, 40)
                    c80 = hacer_circulo_perfecto(lat_f, lon_f, 80)

                    map_url = (
                        f"https://maps.geoapify.com/v1/staticmap?"
                        f"style=osm-bright&width=600&height=300&scale=2&"
                        f"center=lon:{lon_f},lat:{lat_f}&zoom=16&"
                        f"marker=lon:{lon_f},lat:{lon_f};color:%23ff0000;size:large&"
                        f"path=color:%23ff0000|width:2{c40}&"
                        f"path=color:%230000ff|width:2{c80}&"
                        f"apiKey={MAPS_KEY}"
                    )
                    nuevo_embed.set_image(url=map_url)
                    print(f"Mapa generado exitosamente para: {lat_f}, {lon_f}")
                except Exception as map_err:
                    print(f"Error generando mapa en Geoapify: {map_err}")
            else:
                print("Aviso: No se pudieron extraer coordenadas de este embed.")

            # Reenviar al canal destino
            canal_destino_id = CANALES_ESPEJO[message.channel.id]
            canal_destino = bot.get_channel(canal_destino_id)
            
            if not canal_destino:
                try:
                    canal_destino = await bot.fetch_channel(canal_destino_id)
                except Exception as fetch_err:
                    print(f"Error obteniendo canal {canal_destino_id}: {fetch_err}")

            if canal_destino:
                await canal_destino.send(embed=nuevo_embed)

    except Exception as e:
        print(f"Error general procesando mensaje: {e}")

# Iniciar servidor web y conectar el bot a Discord
keep_alive()
bot.run(os.environ['DISCORD_TOKEN'])
