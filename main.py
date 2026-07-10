import os
import discord
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
    t.start()

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
    1522728127565140008: 1525183874852978728,
}

PORY_ID = int(os.environ['POKEMON_BOT_ID'])

@bot.event
async def on_ready():
    print(f'Bot conectado')
    keep_alive()

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    if message.author.id == PORY_ID and message.channel.id in CANALES_ESPEJO:
        canal_destino = bot.get_channel(CANALES_ESPEJO[message.channel.id])
        if canal_destino:
            for embed in message.embeds:
                await canal_destino.send(embed=embed)

bot.run(os.environ['TOKEN'])
