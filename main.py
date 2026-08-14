import os
import re
import math
import asyncio
import aiohttp
import threading
from datetime import datetime
import discord
from discord.ext import commands
from flask import Flask
from waitress import serve

# ==================================================
# CONFIGURACIÓN DE FLASK (Servidor Web)
# ==================================================
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot activo y funcionando"

# ==================================================
# CONFIGURACIÓN DE DISCORD
# ==================================================
intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True

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

CANALES_CON_IVS = {
    1522694582171599011,
    1522694783280349345,
    1522707464150192230,
    1522695765301133312,
    1522695933031219491
}

MAPS_KEY = os.environ.get('GOOGLE_MAPS_API_KEY')

# [FUNCIONES DE LÓGICA Y CLIMA]
def traducir_clima_pogo(main_weather, description=""):
    if not main_weather: return "Soleado / Despejado ☀️"
    main_lower = str(main_weather).lower()
    desc_lower = str(description).lower()
    if "clear" in main_lower: return "Soleado / Despejado ☀️"
    elif "rain" in main_lower or "drizzle" in main_lower or "thunderstorm" in main_lower: return "Lluvia 🌧️"
    elif "snow" in main_lower: return "Nieve ❄️"
    elif "fog" in main_lower or "mist" in main_lower or "haze" in main_lower: return "Niebla 🌫️"
    elif "clouds" in main_lower:
        return "Parcialmente nublado ⛅" if ("few" in desc_lower or "scattered" in desc_lower) else "Nublado ☁️"
    return "Soleado / Despejado ☀️"

active_pokemon_cache = {}
last_checked_minute = datetime.now().minute

async def fetch_weather_for_cell(lat, lon, max_retries=3):
    api_key = os.getenv("WEATHER_API_KEY")
    if not api_key: return None
    api_url = f"https://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&appid={api_key}&units=metric"
    timeout = aiohttp.ClientTimeout(total=4)
    headers = {"User-Agent": "Mozilla/5.0"}
    for attempt in range(1, max_retries + 1):
        try:
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(api_url, headers=headers) as response:
                    if response.status == 200:
                        data = await response.json()
                        w = data.get('weather', [{}])[0]
                        return traducir_clima_pogo(w.get('main'), w.get('description', ''))
        except: await asyncio.sleep(1)
    return None

async def fetch_initial_weather_bg(msg_id, lat, lon):
    weather = await fetch_weather_for_cell(lat, lon)
    if msg_id in active_pokemon_cache and weather:
        active_pokemon_cache[msg_id]["initial_weather"] = weather

async def smart_weather_watcher_loop(bot):
    global last_checked_minute
    while True:
        await asyncio.sleep(30)
        if datetime.now().minute != last_checked_minute:
            last_checked_minute = datetime.now().minute
            # (Aquí iría la lógica de evaluación que tenías antes)
            pass

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
    print(f'Bot iniciado como {bot.user}')
    bot.loop.create_task(smart_weather_watcher_loop(bot))

@bot.event
async def on_message(message):
    if message.author == bot.user: return
    await bot.process_commands(message)
    if message.content.startswith('!') or message.channel.id not in CANALES_ESPEJO or not message.embeds: return
    
    # Lógica de procesamiento de mapas
    try:
        embed = message.embeds[0]
        embed_texto = str(embed.to_dict()).replace('%2C', ',')
        coords = re.search(r'(-?\d{1,2}\.\d+)\s*,\s*(-?\d{1,3}\.\d+)', embed_texto)
        if coords:
            lat_f, lon_f = float(coords.group(1)), float(coords.group(2))
            c40, c80 = hacer_circulo_perfecto(lat_f, lon_f, 40), hacer_circulo_perfecto(lat_f, lon_f, 80)
            map_url = f"https://maps.googleapis.com/maps/api/staticmap?center={lat_f},{lon_f}&zoom=16&size=600x300&scale=2&markers=color:red%7C{lat_f},{lon_f}&path=color:0xFF0000%7Cweight:2%7C{c40}&path=color:0x0000FF%7Cweight:2%7C{c80}&key={MAPS_KEY}"
            nuevo_embed = embed.copy()
            nuevo_embed.set_image(url=map_url)
            canal_destino = bot.get_channel(CANALES_ESPEJO[message.channel.id])
            if canal_destino: await canal_destino.send(embed=nuevo_embed)
    except Exception as e: print(f"Error: {e}")

# ==================================================
# EJECUCIÓN FINAL (Hilos invertidos con Waitress)
# ==================================================
def run_discord_bot():
    bot.run(os.environ['DISCORD_TOKEN'])

if _name_ == "_main_":
    discord_thread = threading.Thread(target=run_discord_bot)
    discord_thread.daemon = True
    discord_thread.start()

    port = int(os.environ.get("PORT", 10000))
    print(f"Servidor web en puerto {port}")
    serve(app, host='0.0.0.0', port=port, threads=4)
