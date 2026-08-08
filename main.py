import os
import discord
import re
import math
from discord.ext import commands

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
    1522728127565140008: 152518387485297828
}

PORY_ID = int(os.environ['POKEMON_BOT_ID'])
MAPS_KEY = os.environ['GOOGLE_MAPS_API_KEY']

@bot.event
async def on_ready():
    print('Bot conectado')

@bot.event
async def on_message(message):
    if message.author.id != PORY_ID or message.channel.id not in CANALES_ESPEJO or not message.embeds:
        return

    for embed in message.embeds:
        new_embed = discord.Embed(title=embed.title, description=embed.description, color=embed.color)
        
        for field in embed.fields:
            new_embed.add_field(name=field.name, value=field.value, inline=field.inline)

        texto_busqueda = (embed.description or "") + "\n" + "".join([f.value for f in embed.fields])
        coords = re.search(r'(-?\d{1,2}\.\d{3,})(?:,|\%2C|\s)\s*(-?\d{1,3}\.\d{3,})', texto_busqueda)
        
        if coords:
            try:
                lat, lon = coords.groups()
                lat_f, lon_f = float(lat), float(lon)
                c40 = "".join([f"|{lat_f + (40/111320.0)*math.cos(i*math.pi/12):.6f},{lon_f + (40/(111320.0*math.cos(lat_f*math.pi/180)))*math.sin(i*math.pi/12):.6f}" for i in range(25)])
                c80 = "".join([f"|{lat_f + (80/111320.0)*math.cos(i*math.pi/12):.6f},{lon_f + (80/(111320.0*math.cos(lat_f*math.pi/180)))*math.sin(i*math.pi/12):.6f}" for i in range(25)])
                map_url = f"https://maps.googleapis.com/maps/api/staticmap?center={lat},{lon}&zoom=16&size=600x300&scale=2&markers=color:red%7C{lat},{lon}&path=color:0xFF0000|weight:1{c40}&path=color:0x0000FF|weight:1{c80}&key={MAPS_KEY}"
                new_embed.set_image(url=map_url)
            except Exception as e:
                print(f"Error procesando coordenadas: {e}")

        canal_destino = bot.get_channel(CANALES_ESPEJO[message.channel.id])
        if canal_destino:
            await canal_destino.send(embed=new_embed)

bot.run(os.environ['TOKEN'])
