import os
import asyncio
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

MAPS_KEY = os.environ.get('GOOGLE_MAPS_API_KEY')

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
        pts.append(f"%7C{lat_i:.6f},{lon_i:.6f}")
    return "".join(pts)

@bot.event
async def on_ready():
    print(f'Bot iniciado con éxito como {bot.user}')

@bot.event
async def on_message(message):
    # 1. Ignorar mensajes propios del bot
    if message.author == bot.user:
        return

    # 2. Verificar si el canal está en el mapeo
    if message.channel.id not in CANALES_ESPEJO:
        return

    # 3. Validar que contenga Embeds
    if not message.embeds:
        return

    try:
        for embed in message.embeds:
            nuevo_embed = embed.copy()
            embed_texto = str(embed.to_dict()).replace('%2C', ',')

            lat_f = None
            lon_f = None

            # Búsqueda universal de coordenadas en cualquier formato
            coords_match = re.search(r'(?:q|center|query|loc|ll)=(-?\d{1,2}\.\d+)\s*,\s*(-?\d{1,3}\.\d+)', embed_texto)
            if not coords_match:
                coords_match = re.search(r'(-?\d{1,2}\.\d{3,})\s*,\s*(-?\d{1,3}\.\d{3,})', embed_texto)

            if coords_match:
                try:
                    lat_f = float(coords_match.group(1))
                    lon_f = float(coords_match.group(2))
                except Exception:
                    pass

            # Generar el mapa estático con sistema de reintentos si existen coordenadas
            if lat_f is not None and lon_f is not None:
                mapa_exitoso = False
                for intento in range(3):
                    try:
                        c40 = hacer_circulo_perfecto(lat_f, lon_f, 40)
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
                        mapa_exitoso = True
                        break  # Si el mapa sale bien, rompemos el ciclo de reintentos
                    except Exception as map_err:
                        print(f"Intento {intento + 1} fallido generando mapa: {map_err}")
                        if intento < 2:
                            await asyncio.sleep(1)  # Espera 1 segundo antes de reintentar
                
                if not mapa_exitoso:
                    print("Aviso: No se pudo generar el mapa tras 3 intentos, se enviará el embed sin mapa.")

            # Obtención ultra segura del canal destino
            canal_destino_id = CANALES_ESPEJO[message.channel.id]
            canal_destino = bot.get_channel(canal_destino_id)

            if not canal_destino:
                try:
                    canal_destino = await bot.fetch_channel(canal_destino_id)
                except Exception as fetch_err:
                    print(f"Error obteniendo canal {canal_destino_id}: {fetch_err}")

            # Reenviar el mensaje al canal duplicado
            if canal_destino:
                await canal_destino.send(embed=nuevo_embed)

    except Exception as e:
        print(f"Error general procesando mensaje: {e}")

# Iniciar servidor web y conectar el bot a Discord
keep_alive()
bot.run(os.environ['DISCORD_TOKEN'])
