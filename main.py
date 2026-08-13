import os
import re
import math
import asyncio
import aiohttp
from datetime import datetime
import discord
from discord.ext import commands
from flask import Flask
from threading import Thread

# ==================================================
# SERVIDOR FLASK CON PUERTO DINÁMICO DE RENDER
# ==================================================
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot activo y funcionando"

def run():
    # Lee el puerto que asigna Render automáticamente (o usa 8080 localmente)
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run)
    t.daemon = True
    t.start()

# ==================================================
# CONFIGURACIÓN DE INTENCIONES DE DISCORD
# ==================================================
intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True

bot = commands.Bot(command_prefix='!', intents=intents)

# ==================================================
# MAPEO DE CANALES (Tus canales configurados)
# ==================================================
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

# ==================================================
# TRADUCTOR OFICIAL POKÉMON GO (FILTRO DE LOS 7 CLIMAS)
# ==================================================
def traducir_clima_pogo(main_weather, description=""):
    if not main_weather:
        return "Soleado / Despejado ☀️"
    
    main_lower = str(main_weather).lower()
    desc_lower = str(description).lower()

    if "clear" in main_lower:
        return "Soleado / Despejado ☀️"
    elif "rain" in main_lower or "drizzle" in main_lower or "thunderstorm" in main_lower:
        return "Lluvia 🌧️"
    elif "snow" in main_lower:
        return "Nieve ❄️"
    elif "fog" in main_lower or "mist" in main_lower or "haze" in main_lower:
        return "Niebla 🌫️"
    elif "clouds" in main_lower:
        if "few" in desc_lower or "scattered" in desc_lower:
            return "Parcialmente nublado ⛅"
        else:
            return "Nublado ☁️"
    else:
        return "Soleado / Despejado ☀️"

# ==================================================
# MOTOR DE ALERTA INTELIGENTE (EN SEGUNDO PLANO)
# ==================================================
active_pokemon_cache = {}
last_checked_minute = datetime.now().minute

async def fetch_weather_for_cell(lat, lon, max_retries=3):
    api_key = os.getenv("WEATHER_API_KEY")
    if not api_key:
        return None

    api_url = f"https://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&appid={api_key}&units=metric"
    timeout = aiohttp.ClientTimeout(total=4)
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

    for attempt in range(1, max_retries + 1):
        try:
            connector = aiohttp.TCPConnector(force_close=True)
            async with aiohttp.ClientSession(timeout=timeout, connector=connector) as session:
                async with session.get(api_url, headers=headers) as response:
                    if response.status == 200:
                        try:
                            data = await response.json()
                            weather_list = data.get('weather', [])
                            if weather_list and len(weather_list) > 0:
                                main_w = weather_list[0].get('main', 'Clear')
                                desc_w = weather_list[0].get('description', '')
                                return traducir_clima_pogo(main_w, desc_w)
                            return "Soleado / Despejado ☀️"
                        except Exception:
                            pass
        except Exception:
            pass
        await asyncio.sleep(1)
    return None

async def fetch_initial_weather_bg(msg_id, lat, lon):
    try:
        weather = await fetch_weather_for_cell(lat, lon)
        if msg_id in active_pokemon_cache and weather:
            active_pokemon_cache[msg_id]["initial_weather"] = weather
    except Exception as e:
        print(f"Error fetching initial weather bg for msg {msg_id}: {e}")

async def evaluate_active_pokemon_weather(bot):
    current_time = datetime.now().timestamp()
    
    expired_keys = [msg_id for msg_id, data in active_pokemon_cache.items() if data.get("expires_at", 0) < current_time]
    for key in expired_keys:
        active_pokemon_cache.pop(key, None)

    for msg_id, data in list(active_pokemon_cache.items()):
        try:
            new_weather = await fetch_weather_for_cell(data["lat"], data["lon"])
            if not new_weather:
                continue

            if data["initial_weather"] == "Pending":
                data["initial_weather"] = new_weather
            elif new_weather != data["initial_weather"]:
                channel = bot.get_channel(data["destination_id"])
                jump_link = data.get("jump_url", "https://discord.com")
                if channel:
                    try:
                        await channel.send(
                            f"⚠️ ¡Alerta Meteorológica Piin! ⚠️\n"
                            f"El clima en la celda de [ESTE POKÉMON ACTIVO]({jump_link}) acaba de cambiar de {data['initial_weather']} a {new_weather}.\n"
                            f"(Los IVs y el nivel de este ejemplar han variado por variación climática)"
                        )
                    except Exception as send_err:
                        print(f"Error enviando mensaje de alerta: {send_err}")
                data["initial_weather"] = new_weather
        except Exception as e:
            print(f"Error evaluando clima para el mensaje {msg_id}: {e}")
            continue

async def smart_weather_watcher_loop(bot):
    global last_checked_minute
    while True:
        try:
            await asyncio.sleep(30)
            now = datetime.now()
            current_minute = now.minute
            
            if current_minute != last_checked_minute:
                await evaluate_active_pokemon_weather(bot)
                last_checked_minute = current_minute
        except Exception as loop_err:
            print(f"Error en el bucle principal de clima: {loop_err}")
            await asyncio.sleep(10)

# ==================================================
# FUNCIÓN DE CÍRCULOS CORREGIDA (SIN DOBLE PIPE %7C%7C)
# ==================================================
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

# ==================================================
# COMANDO DE AUDITORÍA DE CLIMA POKÉMON GO
# ==================================================
@bot.command(name="test_clima")
async def test_clima(ctx, lat: float = -33.0472, lon: float = -71.6127):
    resultado = await fetch_weather_for_cell(lat, lon)
    if resultado:
        await ctx.send(f"🟢 Auditoría Pokémon GO OK: Clima actual en la celda Piin: {resultado}")
    else:
        await ctx.send("🔴 Auditoría Fallida: Error de conexión o API key inválida.")

# ==================================================
# EVENTOS DEL BOT
# ==================================================
@bot.event
async def on_ready():
    print(f'Bot iniciado con éxito como {bot.user}')
    bot.loop.create_task(smart_weather_watcher_loop(bot))

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    await bot.process_commands(message)

    if message.content.startswith('!'):
        return

    if message.channel.id not in CANALES_ESPEJO:
        return

    if not message.embeds:
        return

    try:
        for embed in message.embeds:
            nuevo_embed = embed.copy()
            embed_texto = str(embed.to_dict()).replace('%2C', ',')

            lat_f, lon_f = None, None

            coords_match = re.search(r'(?:q|center|query|loc!11)=(-?\d{1,2}\.\d+)\s*,\s*(-?\d{1,3}\.\d+)', embed_texto)
            if not coords_match:
                coords_match = re.search(r'(-?\d{1,2}\.\d{3,})\s*,\s*(-?\d{1,3}\.\d{3,})', embed_texto)

            if coords_match:
                try:
                    lat_f = float(coords_match.group(1))
                    lon_f = float(coords_match.group(2))
                except Exception:
                    pass

            if lat_f is not None and lon_f is not None:
                try:
                    c40 = hacer_circulo_perfecto(lat_f, lon_f, 40)
                    c80 = hacer_circulo_perfecto(lat_f, lon_f, 80)

                    map_url = (
                        f"https://maps.googleapis.com/maps/api/staticmap?"
                        f"center={lat_f},{lon_f}&zoom=16&size=600x300&scale=2"
                        f"&markers=color:red%7C{lat_f},{lon_f}"
                        f"&path=color:0xFF0000%7Cweight:2%7C{c40}"
                        f"&path=color:0x0000FF%7Cweight:2%7C{c80}"
                        f"&key={MAPS_KEY}"
                    )
                    nuevo_embed.set_image(url=map_url)

                    despawn_time = datetime.now().timestamp() + 1200
                    if message.channel.id in CANALES_CON_IVS:
                        active_pokemon_cache[message.id] = {
                            "lat": lat_f,
                            "lon": lon_f,
                            "expires_at": despawn_time,
                            "initial_weather": "Pending",
                            "destination_id": CANALES_ESPEJO[message.channel.id],
                            "jump_url": ""
                        }
                        bot.loop.create_task(fetch_initial_weather_bg(message.id, lat_f, lon_f))
                except Exception as map_err:
                    print(f"Error generando mapa: {map_err}")

            canal_destino_id = CANALES_ESPEJO[message.channel.id]
            canal_destino = bot.get_channel(canal_destino_id)

            if not canal_destino:
                try:
                    canal_destino = await bot.fetch_channel(canal_destino_id)
                except Exception:
                    pass

            if canal_destino:
                msg_enviado = await canal_destino.send(embed=nuevo_embed)
                if message.channel.id in CANALES_CON_IVS and message.id in active_pokemon_cache:
                    active_pokemon_cache[message.id]["jump_url"] = msg_enviado.jump_url

    except Exception as e:
        print(f"Error general procesando mensaje: {e}")

# ==================================================
# INICIO DE LA APLICACIÓN
# ==================================================
keep_alive()
bot.run(os.environ['DISCORD_TOKEN'])
