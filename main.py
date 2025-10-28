import discord
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from dotenv import load_dotenv
from discord import app_commands
from commands.TailorResume.TailorResume import TailorResume
import os
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer


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
    raise ValueError("Missing DISCORD_BOT_TOKEN in .env, raised in main file")

DISCORD_CHANNEL_TOKEN = os.getenv("DISCORD_CHANNEL")
if not DISCORD_CHANNEL_TOKEN:
    raise ValueError("Missing DISCORD_CHANNEL_TOKEN in .env, raise in main")

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
        await tree.sync(guild=discord.Object(id=int(DISCORD_CHANNEL_TOKEN)))
    except Exception as e:
        print(f"[slash sync] {e}")

    # get channel and if it's a volid token, notify that the bot is running 
    # else raise valueError for token 
    channel = client.get_channel(DISCORD_CHANNEL_TOKEN)
    if channel is None:
        try:
            channel = await client.fetch_channel(DISCORD_CHANNEL_TOKEN)
        except Exception as e:
            print(f"[fetch_channel] {e}")

    if channel:
        try:
            await channel.send("Bot is now online")
        except Exception as e:
            print(f"[send] {e}")
    else:
        print("[warn] Channell not found; check DISCORD_CHANNEL id and bot permission")
    # activate bot, any changes should be made before this 
client.run(DISCORD_BOT_TOKEN)
