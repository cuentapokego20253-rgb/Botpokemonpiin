import os
import discord
import re
import math
from urllib.parse import quote
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

# --- CAMBIO DE PROVEEDOR: ahora Mapbox ---
MAPS_KEY = os.environ.get('MAPBOX_ACCESS_TOKEN')
MAPBOX_STYLE = os.environ.get('MAPBOX_STYLE', 'streets-v12')  # el estilo visualmente más parecido a Google Maps

# --- FÓRMULA MATEMÁTICA RESTAURADA (sin ningún cambio en la matemática) ---
def hacer_circulo_perfecto(lat, lon, radio_metros, num_puntos=185):
    puntos = []
    radio_tierra = 6378137.0  # Radio de la Tierra en metros
    for i in range(num_puntos + 1):  # +1 para cerrar el polígono conectando con el primer punto
        angulo = math.radians(float(i) / num_puntos * 360.0)
        dx = radio_metros * math.cos(angulo)
        dy = radio_metros * math.sin(angulo)
        factor_correccion = 1.6
        d_lat = ((dy / radio_tierra) * (180.0 / math.pi)) / factor_correccion
        d_lon = ((dx / (radio_tierra * math.cos(math.radians(lat)))) * (180.0 / math.pi)) / factor_correccion

        # Mapbox necesita los puntos como pares (lat, lon), en ese orden,
        # para poder codificarlos como polilínea (ver encode_polyline)
        puntos.append((lat + d_lat, lon + d_lon))

    return puntos
# --------------------------------------------------

# --- NUEVO: codificador de polilínea (Google Encoded Polyline Algorithm Format) ---
# Mapbox exige que los overlays de tipo "path" vengan en este formato comprimido,
# en vez de coordenadas en texto plano como usaban Geoapify/MapTiler.
# Implementado a mano para no depender de instalar la librería "polyline" en Render.
def _codificar_numero(num):
    num = num << 1
    if num < 0:
        num = ~num
    partes = []
    while num >= 0x20:
        partes.append(chr((0x20 | (num & 0x1f)) + 63))
        num >>= 5
    partes.append(chr(num + 63))
    return "".join(partes)

def codificar_polilinea(puntos, precision=5):
    factor = 10 ** precision
    resultado = []
    prev_lat = 0
    prev_lon = 0
    for lat, lon in puntos:
        lat_e5 = round(lat * factor)
        lon_e5 = round(lon * factor)
        resultado.append(_codificar_numero(lat_e5 - prev_lat))
        resultado.append(_codificar_numero(lon_e5 - prev_lon))
        prev_lat = lat_e5
        prev_lon = lon_e5
    return "".join(resultado)
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
            # Calculamos los puntos del círculo (misma matemática de siempre)
            c40 = hacer_circulo_perfecto(lat_f, lon_f, 40)
            c80 = hacer_circulo_perfecto(lat_f, lon_f, 80)

            # Codificamos cada círculo como polilínea y la escapamos con quote(),
            # porque una polilínea codificada puede contener \, ?, ~, `, etc.,
            # caracteres que romperían la URL (y por lo tanto la vista previa en Discord)
            # si no se codifican con %XX.
            poly40 = quote(codificar_polilinea(c40), safe="")
            poly80 = quote(codificar_polilinea(c80), safe="")

            # --- URL migrada a Mapbox Static Images API ---
            # El overlay va en el PATH de la URL (no en query string), separado por comas:
            #   pin-s+color(lon,lat)                                  -> el pin rojo
            #   path-{grosor}+{colorBorde}-{opacidadBorde}+{colorRelleno}-{opacidadRelleno}(polilínea)
            overlay_pin = f"pin-s+ff0000({lon_f:.6f},{lat_f:.6f})"
            overlay_c40 = f"path-1+ff0000-1+ff0000-0({poly40})"   # círculo de 40m, rojo, sin relleno
            overlay_c80 = f"path-1+0000ff-1+0000ff-0({poly80})"   # círculo de 80m, azul, sin relleno
            overlays = f"{overlay_pin},{overlay_c40},{overlay_c80}"

            map_url = (
                f"https://api.mapbox.com/styles/v1/mapbox/{MAPBOX_STYLE}/static/"
                f"{overlays}/{lon_f:.6f},{lat_f:.6f},16.2/600x300@2x"
                f"?access_token={MAPS_KEY}"
            )

            print(f"DEBUG URL: {map_url}")
            nuevo_embed.set_image(url=map_url)

        canal_destino = bot.get_channel(CANALES_ESPEJO[message.channel.id])
        if canal_destino:
            await canal_destino.send(embed=nuevo_embed)

keep_alive()
bot.run(os.environ['DISCORD_TOKEN'])
