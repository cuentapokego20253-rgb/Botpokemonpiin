import os
import re
import math
import asyncio
import discord
from discord.ext import commands
from flask import Flask
from threading import Thread
from datetime import datetime
import aiohttp

# ==========================================
# SERVIDOR FLASK (PARA RENDER)
# ==========================================
app = Flask(__name__)
@app.route('/')
def home(): return "Bot Activo y Funcionando"
def run(): app.run(host='0.0.0.0', port=8080)
def keep_alive():
    t = Thread(target=run)
    t.daemon = True
    t.start()

# ==========================================
# CONFIGURACIÓN Y CACHÉ
# ==========================================
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# MAPEO EXACTO: Canal Original (Izquierda) ➔ Canal Duplicado (Derecha)
CANALES_MAPEO = {
    1522694582171599011: 152273855287157536,
    1522694783280349345: 1523963115467837480,
    1522695765301133312: 1523907438590296064,
    1522695933031219491: 1523907697936826392,
    1522707464150192230: 1523964283484901476,
    1522711485586079895: 1525184002011431082,
    1522728127565140008: 1525183874852978728
}

CANALES_CON_IVS = {1522694582171599011, 1522694783280349345, 1522707464150192230, 1522695933031219491, 1522711485586079895, 1522728127565140008, 1522695765301133312}
MAPS_KEY = os.environ.get('GOOGLE_MAPS_API_KEY')
WEATHER_API_KEY = os.environ.get('WEATHER_API_KEY')

active_pokemon_cache = {}

# ==========================================
# LÓGICA DE MAPAS Y CLIMA (OPTIMIZADA)
# ==========================================
def traducir_clima_pogo(main_weather, description=""):
    m = main_weather.lower()
    if "clear" in m: return "Soleado / Despejado ☀️"
    if any(x in m for x in ["rain", "drizzle", "thunderstorm"]): return "Lluvia 🌧️"
    if "snow" in m: return "Nieve ❄️"
    if any(x in m for x in ["fog", "mist", "haze"]): return "Niebla 🌫️"
    if "clouds" in m: return "Parcialmente nublado ⛅" if "few" in description.lower() or "scattered" in description.lower() else "Nublado ☁️"
    return "Soleado / Despejado ☀️"

def hacer_circulo_perfecto(lat, lon, radio_metros):
    R = 6378137.0
    cx, cy = math.radians(lon) * R, math.log(math.tan(math.pi / 4 + math.radians(lat) / 2)) * R
    pts = []
    for a in range(0, 361, 30):
        rad = math.radians(a)
        x = cx + radio_metros * math.cos(rad)
        y = cy + radio_metros * math.sin(rad)
        lat_i = math.degrees(2 * math.atan(math.exp(y / R)) - math.pi / 2)
        lon_i = math.degrees(x / R)
        pts.append(f"{lat_i:.4f},{lon_i:.4f}")
    return "%7C".join(pts)

async def fetch_weather_async(lat, lon):
    url = f"https://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&appid={WEATHER_API_KEY}&units=metric"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=5) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    w = data.get('weather', [{}])[0]
                    return traducir_clima_pogo(w.get('main', 'Clear'), w.get('description', ''))
    except Exception as e:
        print(f"Error API Clima: {e}")
    return None

# ==========================================
# MOTOR ASÍNCRONO DE MONITOREO
# ==========================================
async def weather_watcher_loop():
    while True:
        try:
            now = datetime.now()
            expired = [k for k, v in active_pokemon_cache.items() if v['expires_at'] < now.timestamp()]
            for k in expired: active_pokemon_cache.pop(k, None)

            if now.minute == 0 and now.second >= 10 and now.second < 20:
                for msg_id, data in list(active_pokemon_cache.items()):
                    if data['initial_weather'] == "Pending":
                        new_w = await fetch_weather_async(data['lat'], data['lon'])
                        data['initial_weather'] = new_w or "Soleado / Despejado ☀️"
                    else:
                        new_w = await fetch_weather_async(data['lat'], data['lon'])
                        if new_w and new_w != data['initial_weather']:
                            channel = bot.get_channel(data['destination_id'])
                            if channel:
                                await channel.send(f"⚠️ *Cambio Meteorológico!*\nEmbed: {data['jump_url']}\n[{data['initial_weather']}] ➔ [{new_w}]")
                            data['initial_weather'] = new_w
        except Exception as e:
            print(f"Error en bucle watcher: {e}")
        await asyncio.sleep(10)

# ==========================================
# EVENTOS Y COMANDOS DISCORD
# ==========================================
@bot.event
async def on_ready():
    print(f'Bot iniciado: {bot.user}')
    bot.loop.create_task(weather_watcher_loop())

@bot.command(name="test_clima")
async def test_clima(ctx, lat: float = -33.0269, lon: float = -71.6386):
    """Comando para verificar el clima actual (Por defecto: Playa Ancha, Valparaíso)"""
    clima = await fetch_weather_async(lat, lon)
    if clima:
        await ctx.send(f"🌤️ *Clima actual detectado* (Lat: {lat}, Lon: {lon} - Playa Ancha, Valparaíso):\n*{clima}*")
    else:
        await ctx.send("❌ Error al consultar la API del clima o clave inválida.")

@bot.event
async def on_message(message):
    await bot.process_commands(message)

    if message.author == bot.user:
        return
    
    if message.channel.id not in CANALES_MAPEO:
        return

    try:
        if not message.embeds:
            return

        embed = message.embeds[0].copy()
        text = str(embed.to_dict())
        coords = re.search(r"(-?\d+\.\d+),\s*(-?\d+\.\d+)", text)
        
        if coords:
            lat, lon = float(coords.group(1)), float(coords.group(2))
            c40 = hacer_circulo_perfecto(lat, lon, 40)
            c80 = hacer_circulo_perfecto(lat, lon, 80)
            embed.set_image(url=f"https://maps.googleapis.com/maps/api/staticmap?center={lat},{lon}&zoom=16&size=600x300&markers=color:red%7C{lat},{lon}&path=color:0xFF000037%7Cweight:2%7C{c40}&path=color:0x8E00FF7C%7Cweight:2%7C{c80}&key={MAPS_KEY}")

        id_canal_destino = CANALES_MAPEO[message.channel.id]
        canal_destino = bot.get_channel(id_canal_destino)
        
        if not canal_destino:
            print(f"Error: No se pudo encontrar el canal destino con ID {id_canal_destino}")
            return

        msg = await canal_destino.send(embed=embed)

        if message.channel.id in CANALES_CON_IVS:
            ahora_ts = datetime.now().timestamp()
            duracion_segundos = 3000
            match_tiempo = re.search(r"(\d+)\s*m", text.lower())
            if match_tiempo:
                minutos_extra = int(match_tiempo.group(1))
                if minutos_extra > 0:
                    duracion_segundos = minutos_extra * 60

            expires_at = ahora_ts + duracion_segundos
            hora_actual_num = datetime.now().hour
            hora_expiracion_num = datetime.fromtimestamp(expires_at).hour

            if hora_actual_num != hora_expiracion_num and coords:
                active_pokemon_cache[message.id] = {
                    "lat": lat,
                    "lon": lon,
                    "expires_at": expires_at,
                    "initial_weather": "Pending",
                    "jump_url": msg.jump_url,
                    "destination_id": id_canal_destino
                }
    except Exception as e:
        print(f"Error en procesamiento de mensaje: {e}")

if __name__ == '__main__':
    keep_alive()
    bot.run(os.environ.get('DISCORD_TOKEN'))
