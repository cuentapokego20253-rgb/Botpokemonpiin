import os
import discord
from discord.ext import commands
import re
import math
import asyncio
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from flask import Flask
from threading import Thread

# ==========================================
# CONFIGURACIÓN DE ZONA HORARIA (Chile)
# ==========================================
CHILE_TZ = ZoneInfo('America/Santiago')

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

# Mapeo de Canales (Tus 7 canales originales y sus respectivos espejos de destino)
CANALES_ESPEJO = {
    1522694582171599011: 1522738552587157536, # ID 100-A      100-B
    1522694783280349345: 1523963115467837480, # ID 0-A        0-B
    1522707464150192230: 1523964283484901476, # Copa500 A     Copa 500 B
    1522695765301133312: 1523907438590296064, # Liga Super A  Liga super B
    1522695933031219491: 1523907697936826392, # Liga Ultra A  Liga Utra B
    1522711485586079895: 1525184002011431082, # Pokes Raro A  Pokes Raro B
    1522728127565140008: 1525183874852978728  # Keckleon A    Keckleon B
}

# ==============================================================================
# CANALES DESTINO PARA LA ALERTA DE PRECAUCIÓN DE CLIMA
# Aquí están los 7 canales espejo. 
# Si hay alguno donde NO quieras que llegue esta alerta, simplemente bórralo de esta lista.
# ==============================================================================
CANALES_ALERTA_CLIMA = [
    1522738552587157536, #100 B
    1523963115467837480, #0 B
    1523964283484901476, #Copa 500 B
    1523907438590296064, #Liga Super 1500 B
    1523907697936826392, #Liga Ultra 2500 B
    1525184002011431082  #Pokes Raro B
]

MAPS_KEY = os.environ.get('GOOGLE_MAPS_API_KEY')

# Lista temporal ultraligera para los Pokémon que cruzan el umbral de la hora
pokemons_en_umbral = []

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

# BUCLE SILENCIOSO: Revisa cada 10 segundos y solo avisa a la hora en punto si hay Pokémon cruzando el umbral
async def weather_alert_loop():
    await bot.wait_until_ready()
    while not bot.is_closed():
        try:
            now = datetime.now(CHILE_TZ)
            ahora_ts = now.timestamp()
            
            # Limpiar de la lista los Pokémon que ya expiraron
            global pokemons_en_umbral
            pokemons_en_umbral = [p for p in pokemons_en_umbral if p['expires_at'] >= ahora_ts]
            
            # Si estamos en el minuto 0 (primeros 15 segundos) y hay Pokémon cruzando el umbral
            if now.minute == 0 and now.second < 15 and pokemons_en_umbral:
                canales_a_notificar = set(p['destination_id'] for p in pokemons_en_umbral)
                
                for channel_id in canales_a_notificar:
                    # Validar si el canal está autorizado para recibir la alerta de clima
                    if channel_id in CANALES_ALERTA_CLIMA:
                        channel = bot.get_channel(channel_id)
                        if not channel:
                            try:
                                channel = await bot.fetch_channel(channel_id)
                            except Exception:
                                continue
                        
                        if channel:
                            await channel.send(
                                "⚠️ *Cambio de Clima* ⚠️\n"
                                "¡El clima para algunos Pokémon activos ha cambiado!\n"
                                "Esto podría haber alterado los IVs y estadísticas reportadas..."
                            )
                
                # Vaciamos la lista para que no se repita la alerta en la misma hora
                pokemons_en_umbral.clear()
                
        except Exception as e:
            print(f"Error en loop de alerta de clima: {e}")
            
        await asyncio.sleep(10)

@bot.event
async def on_ready():
    print(f'Bot iniciado con éxito como {bot.user}')
    bot.loop.create_task(weather_alert_loop())

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

            # Generar el mapa estático si existen coordenadas
            if lat_f is not None and lon_f is not None:
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

            # Reenviar el mensaje al canal duplicado con mapa y círculos
            if canal_destino:
                await canal_destino.send(embed=nuevo_embed)

                # Registrar el Pokémon si cruza el umbral de la hora (para la alerta de precaución)
                try:
                    ahora = datetime.now(CHILE_TZ)
                    ahora_ts = ahora.timestamp()
                    
                    contenido_completo = message.content + " " + embed_texto
                    match_ts_discord = re.search(r'<t:(\d+)(?::[a-zA-Z])?>', contenido_completo)
                    
                    if match_ts_discord:
                        expires_at = int(match_ts_discord.group(1))
                    else:
                        expires_at = ahora_ts + 2700 
                    
                    dt_actual = datetime.fromtimestamp(ahora_ts, CHILE_TZ)
                    dt_expira = datetime.fromtimestamp(expires_at, CHILE_TZ)
                    next_hour = (dt_actual.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)).timestamp()
                    
                    if dt_expira >= datetime.fromtimestamp(next_hour, CHILE_TZ) and expires_at > ahora_ts:
                        pokemons_en_umbral.append({
                            "expires_at": expires_at,
                            "destination_id": canal_destino_id
                        })
                except Exception as umbral_err:
                    print(f"Error calculando umbral de precaución: {umbral_err}")

    except Exception as e:
        print(f"Error general procesando mensaje: {e}")

# Iniciar servidor web y conectar el bot a Discord
keep_alive()
bot.run(os.environ['DISCORD_TOKEN'])
