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

# Mapeo de Canales: { ID_CANAL_ORIGINAL_PORYPRO : ID_CANAL_DUPLICADO_DESTINO }
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
            embed_texto = str(embed.to_dict())

            # Inicializar variables de coordenadas de forma segura
            lat_f = None
            lon_f = None

            # Búsqueda ultra segura de coordenadas en el embed
            coords_match = re.search(r'q=(-?\d+\.\d+)(?:%2C|,)\s*(-?\d+\.\d+)', embed_texto)
            if not coords_match:
                coords_match = re.search(r'(-?\d{1,2}\.\d{4,})\s*,\s*(-?\d{1,3}\.\d{4,})', embed_texto)

            if coords_match:
                try:
                    lat_f = float(coords_match.group(1))
                    lon_f = float(coords_match.group(2))
                except Exception:
                    pass

            # Si se obtuvieron coordenadas válidas, generar el mapa estático con los dos círculos
            if lat_f is not None and lon_f is not None:
                try:
                    # Cálculo de puntos para el círculo de 40 metros (Radio Avatar)
                    c40 = "".join([f"%7C{lat_f + (40/(111320.0*math.cos(lat_f*math.pi/180)))*math.sin(i*math.pi/12):.6f},{lon_f + (40/111320.0)*math.cos(i*math.pi/12):.6f}" for i in range(25)])
                    
                    # Cálculo de puntos para el círculo de 80 metros (Radio Parque)
                    c80 = "".join([f"%7C{lat_f + (80/(111320.0*math.cos(lat_f*math.pi/180)))*math.sin(i*math.pi/12):.6f},{lon_f + (80/111320.0)*math.cos(i*math.pi/12):.6f}" for i in range(25)])

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

            # Reenviar el mensaje enriquecido al canal duplicado
            canal_destino_id = CANALES_ESPEJO[message.channel.id]
            canal_destino = bot.get_channel(canal_destino_id)
            if canal_destino:
                await canal_destino.send(embed=nuevo_embed)

    except Exception as e:
        print(f"Error general procesando el mensaje: {e}")

# Iniciar servidor web y conectar el bot a Discord
keep_alive()
bot.run(os.environ['DISCORD_TOKEN'])
