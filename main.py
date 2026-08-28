import os
import discord
import re
import math
import io
import asyncio
import aiohttp
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

# Mapeo de Canales (9 canales configurados)
CANALES_ESPEJO = {
    1522694582171599011: 1522738552587157536,
    1522694783280349345: 1523963115467837480,
    1522695765301133312: 1523907438590296064,
    1522695933031219491: 1523907697936826392,
    1522707464150192230: 1523964283484901476,
    1522711485586079895: 1525184002011431082,
    1522728127565140008: 1525183874852978728,
    1542034126528446515: 1542034236591050853,
    1542038203110916096: 1542038383755399259
}
MAPS_KEY = os.environ.get('GOOGLE_MAPS_API_KEY')

# FUNCIÓN PARA HACER LOS CÍRCULOS REDONDOS PERFECTOS
# CORREGIDA: ahora calcula el desplazamiento geodésico directo en metros
# reales (con la corrección por coseno de latitud), en vez de desplazar
# el punto dentro de la proyección Mercator. La versión anterior no
# compensaba la distorsión de esa proyección, y los círculos terminaban
# representando ~83% del radio real pedido (verificado con distancia
# real: un radio de 80m quedaba en ~66.75m en el terreno).
def hacer_circulo_perfecto(lat, lon, radio_metros, num_puntos=32):
    R = 6378137.0
    pts = []
    for i in range(num_puntos + 1):  # +1 para cerrar el círculo
        angulo = math.radians(float(i) / num_puntos * 360.0)
        dx = radio_metros * math.cos(angulo)
        dy = radio_metros * math.sin(angulo)
        d_lat = (dy / R) * (180.0 / math.pi)
        d_lon = (dx / (R * math.cos(math.radians(lat)))) * (180.0 / math.pi)
        pts.append(f"%7C{lat + d_lat:.6f},{lon + d_lon:.6f}")
    return "".join(pts)

# Descarga la imagen del mapa con reintentos, en vez de dejar que Discord
# la busque por su cuenta. Así cada mapa entregado con éxito cuenta como
# 1 petición a Google, no 2 (antes: 1 de validación + 1 de caché por
# parte de Discord). Si los 3 intentos fallan, la notificación se manda
# igual, sin imagen — nunca se cae el bot por esto.
async def descargar_mapa_con_reintentos(map_url, intentos=3):
    for intento in range(1, intentos + 1):
        try:
            async with aiohttp.ClientSession() as session:
                timeout = aiohttp.ClientTimeout(total=5)
                async with session.get(map_url, timeout=timeout) as resp:
                    if resp.status == 200:
                        data = await resp.read()
                        return io.BytesIO(data)
                    else:
                        print(f"DEBUG mapa intento {intento}: Google respondió status {resp.status}")
        except Exception as e:
            print(f"DEBUG mapa intento {intento} falló: {e}")
        if intento < intentos:
            await asyncio.sleep(1.5)
    print("DEBUG mapa: se agotaron los 3 intentos, se envía sin imagen")
    return None

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
            archivo_mapa = None

            # Búsqueda universal de coordenadas en cualquier formato
            coords_match = re.search(r'(?:q|center|query|loc|ll)=?(-?\d{1,2}\.\d+)\s*,\s*(-?\d{1,3}\.\d+)', embed_texto)
            if not coords_match:
                coords_match = re.search(r'(-?\d{1,2}\.\d{3,})\s*,\s*(-?\d{1,3}\.\d{3,})', embed_texto)

            if coords_match:
                try:
                    lat_f = float(coords_match.group(1))
                    lon_f = float(coords_match.group(2))
                except Exception:
                    pass

            # Generar el mapa estático si existen coordenadas
            if lat_f is not None and lon_f is not None:
                try:
                    c40 = hacer_circulo_perfecto(lat_f, lon_f, 40)
                    c80 = hacer_circulo_perfecto(lat_f, lon_f, 80)

                    map_url = (
                        f"https://maps.googleapis.com/maps/api/staticmap?"
                        f"center={lat_f},{lon_f}&zoom=16.5&size=600x300&scale=2"
                        f"&markers=color:red%7C{lat_f},{lon_f}"
                        f"&path=color:0xFF0000%7Cweight:2{c40}"
                        f"&path=color:0x0000FF%7Cweight:2{c80}"
                        f"&key={MAPS_KEY}"
                    )
                    print(f"DEBUG URL: {map_url}")
                    imagen_bytes = await descargar_mapa_con_reintentos(map_url)
                    if imagen_bytes:
                        archivo_mapa = discord.File(imagen_bytes, filename="mapa.png")
                        nuevo_embed.set_image(url="attachment://mapa.png")
                except Exception as map_err:
                    print(f"Error generando mapa: {map_err}")

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
                if archivo_mapa:
                    await canal_destino.send(embed=nuevo_embed, file=archivo_mapa)
                else:
                    await canal_destino.send(embed=nuevo_embed)

    except Exception as e:
        print(f"Error general procesando mensaje: {e}")

# Iniciar servidor web y conectar el bot a Discord
keep_alive()
bot.run(os.environ['DISCORD_TOKEN'])
