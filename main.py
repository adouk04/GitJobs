import os
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import discord
from discord import app_commands
from dotenv import load_dotenv

from commands.TailorResume.TailorResume import TailorResume

# ---- Cloud Run health server (so the container "listens on $PORT") ----
class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"ok")

def start_health_server():
    port = int(os.getenv("PORT", "8080"))  # Cloud Run sets PORT
    server = HTTPServer(("", port), HealthHandler)
    server.serve_forever()

threading.Thread(target=start_health_server, daemon=True).start()
# -----------------------------------------------------------------------

load_dotenv()  # used locally; in Cloud Run, env vars come from the service config

# Required env vars
DISCORD_BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN")
if not DISCORD_BOT_TOKEN:
    raise ValueError("Missing DISCORD_BOT_TOKEN")

DISCORD_CHANNEL_ID = os.getenv("DISCORD_CHANNEL")
if not DISCORD_CHANNEL_ID:
    raise ValueError("Missing DISCORD_CHANNEL")
DISCORD_CHANNEL_ID = int(DISCORD_CHANNEL_ID)  # ensure int

# Intents
intents = discord.Intents.default()
intents.messages = True
intents.guilds = True

client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)

@client.event
async def on_ready():
    # Register slash commands
    TailorResume(tree)
    try:
        # if you want global commands instead, use: await tree.sync()
        await tree.sync(guild=discord.Object(id=DISCORD_CHANNEL_ID))
    except Exception as e:
        print(f"[slash sync] {e}")

    # Send startup notice
    channel = client.get_channel(DISCORD_CHANNEL_ID)
    if channel is None:
        try:
            channel = await client.fetch_channel(DISCORD_CHANNEL_ID)
        except Exception as e:
            print(f"[fetch_channel] {e}")

    if channel:
        try:
            await channel.send("Bot is now online ✅")
        except Exception as e:
            print(f"[send] {e}")
    else:
        print("[warn] Channel not found; check DISCORD_CHANNEL id and bot permissions")

client.run(DISCORD_BOT_TOKEN)
