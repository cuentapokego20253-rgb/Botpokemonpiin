import os
import discord
import re
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

# Llave API de Geoapify (asegúrate de que en Render se llame exactamente así)
MAPS_KEY = os.environ.get('GEOAPIFY_API_KEY')

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
            coords_match = re.search(r'(?:q|center|query|loc|ll)=?(-?\d{1,2}\.\d+)\s*,\s*(-?\d{1,3}\.\d+)', embed_texto)
            if not coords_match:
                coords_match = re.search(r'(-?\d{1,2}\.\d{3,})\s*,\s*(-?\d{1,3}\.\d{3,})', embed_texto)

            if coords_match:
                try:
                    lat_f = float(coords_match.group(1))
                    lon_f = float(coords_match.group(2))
                except Exception:
                    pass

            # Generar el mapa estático con Geoapify si existen coordenadas
            if lat_f is not None and lon_f is not None:
                try:
                    # Geoapify genera los círculos de forma nativa, evitando URLs gigantes
                    map_url = (
                        f"https://maps.geoapify.com/v1/staticmap?"
                        f"style=osm-bright&width=600&height=300&scale=2&"
                        f"center=lon:{lon_f},lat:{lat_f}&zoom=16&"
                        f"marker=lon:{lon_f},lat:{lat_f};color:%23ff0000;size:large&"
                        f"geometry=circle:{lon_f},{lat_f},40;color:%23ff0000;background:%23ff000033;linewidth:2&"
                        f"geometry=circle:{lon_f},{lat_f},80;color:%230000ff;background:%230000ff22;linewidth:2&"
                        f"apiKey={MAPS_KEY}"
                    )
                    nuevo_embed.set_image(url=map_url)
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
                await canal_destino.send(embed=nuevo_embed)

    except Exception as e:
        print(f"Error general procesando mensaje: {e}")

# Iniciar servidor web y conectar el bot a Discord
keep_alive()
bot.run(os.environ['DISCORD_TOKEN'])
