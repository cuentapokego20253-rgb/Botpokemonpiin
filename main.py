import os
import discord
import re
import math
from discord.ext import commands
from flask import Flask
from threading import Thread

# Servidor Flask para mantener vivo el proceso en Render
app = Flask(_name_)

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
    1522695765901133312: 1523907433590296064,
    1522695933031219491: 1523907607936826392,
    1522707464450192230: 1523964283484901476,
    1522711485586079895: 1525184002011431082,
    1522728127565140008: 1525183874852978728
}

MAPS_KEY = os.environ.get('GOOGLE_MAPS_API_KEY')

# FUNCIÓN PARA HACER LOS CÍRCULOS PERFECTOS
def hacer_circulo_perfecto(lat, lon, radio_metros):
    R = 6378137.0
    cx = math.radians(lon) * R
    cy = math.log(math.tan(math.pi / 4 + math.radians(lat) / 2)) * R
    pts = []
    for a in range(0, 361, 10):
        rad = math.radians(a)
        x = cx + radio_metros * math.cos(rad)
        y = cy + radio_metros * math.sin(rad)
        lon_i = math.degrees(x / R)
        lat_i = math.degrees(2 * math.atan(math.exp(y / R)) - math.pi / 2.0)
        pts.append(f"%7C{lat_i:.6f},{lon_i:.6f}")
    return "".join(pts)

@bot.event
async def on_ready():
    print(f'Bot iniciado con éxito como {bot.user}')

@bot.event
async def on_message(message):
    # 1. Ignorar mensajes enviados por el propio bot
    if message.author == bot.user:
        return

    # 2. Verificar si el mensaje viene de un canal mapeado
    if message.channel.id not in CANALES_ESPEJO:
        return

    # 3. Validar que contenga Embeds
    if not message.embeds:
        return

    # Protección total contra cualquier error inesperado
    try:
        for embed in message.embeds:
            nuevo_embed = embed.copy()
            # Normalizamos el texto del embed reemplazando %2C por comas para compatibilidad universal
            embed_texto = str(embed.to_dict()).replace('%2C', ',')

            # Inicializar variables de coordenadas de forma segura
            lat_f = None
            lon_f = None

            # Búsqueda ultra flexible de coordenadas (soporta cualquier cantidad de decimales)
            coords_match = re.search(r'(?:q|center)=(-?\d+\.\d+),\s*(-?\d+\.\d+)', embed_texto)
            if not coords_match:
                coords_match = re.search(r'(-?\d{1,2}\.\d+),\s*(-?\d{1,3}\.\d+)', embed_texto)

            if coords_match:
                try:
                    lat_f = float(coords_match.group(1))
                    lon_f = float(coords_match.group(2))
                except Exception:
                    pass

            # Si se obtuvieron coordenadas válidas, generar el mapa estático
            if lat_f is not None and lon_f is not None:
                try:
                    # Círculo de 40 metros (Radio Avatar)
                    c40 = hacer_circulo_perfecto(lat_f, lon_f, 40)
                    
                    # Círculo de 80 metros (Radio Parque)
                    c80 = hacer_circulo_perfecto(lat_f, lon_f, 80)

                    map_url = (
                        f"https://maps.googleapis.com/maps/api/staticmap?"
                        f"center={lat_f},{lon_f}&zoom=16&size=600x300&scale=2"
                        f"&markers=color:red%7C{lat_f},{lon_f}"
                        f"&path=color:0xFF0000%7Cweight:2{c40}"
                        f"&path=color:0x0000FF%7Cweight:2{c80}"
                        f"&key={MAPS_KEY}"
                    )
                    nuevo_embed.set_image(url=map_url)
                except Exception as map_err:
                    print(f"Error generando el mapa: {map_err}")

            # Reenviar el mensaje enriquecido al canal duplicado correspondiente
            canal_destino_id = CANALES_ESPEJO[message.channel.id]
            canal_destino = bot.get_channel(canal_destino_id)
            if canal_destino:
                await canal_destino.send(embed=nuevo_embed)

    except Exception as e:
        print(f"Error general procesando el mensaje: {e}")

# Iniciar servidor web y conectar el bot a Discord
keep_alive()
bot.run(os.environ['DISCORD_TOKEN'])
