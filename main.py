import os
import re
import math
import time
import threading
import discord
from discord.ext import commands
from flask import Flask
from waitress import serve

# Configuración básica
app = Flask(__name__)
@app.route('/')
def home():
    return "Bot Online", 200

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

# Canales
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
        pts.append(f"{lat_i:.6f},{lon_i:.6f}")
    return "%7C".join(pts)

@bot.event
async def on_ready():
    print(f'Bot {bot.user} conectado exitosamente.')

@bot.event
async def on_message(message):
    if message.author == bot.user: return
    await bot.process_commands(message)
    if message.channel.id in CANALES_ESPEJO and message.embeds:
        try:
            embed = message.embeds[0]
            embed_texto = str(embed.to_dict()).replace('%2C', ',')
            coords = re.search(r'(-?\d{1,2}\.\d+)\s*,\s*(-?\d{1,3}\.\d+)', embed_texto)
            if coords:
                lat_f, lon_f = float(coords.group(1)), float(coords.group(2))
                c40 = hacer_circulo_perfecto(lat_f, lon_f, 40)
                c80 = hacer_circulo_perfecto(lat_f, lon_f, 80)
                map_url = f"https://maps.googleapis.com/maps/api/staticmap?center={lat_f},{lon_f}&zoom=16&size=600x300&scale=2&markers=color:red%7C{lat_f},{lon_f}&path=color:0xFF0000%7Cweight:2%7C{c40}&path=color:0x0000FF%7Cweight:2%7C{c80}&key={MAPS_KEY}"
                nuevo_embed = embed.copy()
                nuevo_embed.set_image(url=map_url)
                canal_destino = bot.get_channel(CANALES_ESPEJO[message.channel.id])
                if canal_destino: await canal_destino.send(embed=nuevo_embed)
        except Exception as e: print(e)

# --- EJECUCIÓN CORREGIDA ---
def start_bot():
    time.sleep(5) 
    bot.run(os.environ['DISCORD_TOKEN'])

if __name__ == "__main__":
    t = threading.Thread(target=start_bot, daemon=True)
    t.start()
    port = int(os.environ.get("PORT", 10000))
    serve(app, host='0.0.0.0', port=port)
