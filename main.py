from http.server import BaseHTTPRequestHandler, HTTPServer
from dotenv import load_dotenv
from commands.TailorResume.TailorResume import TailorResume
import logging, discord, threading, os
from discord import app_commands

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")
log = logging.getLogger("bot")

class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"ok")

def start_health_server():
    port = int(os.getenv("PORT", "8080"))  
    server = HTTPServer(("", port), HealthHandler)
    server.serve_forever()

threading.Thread(target=start_health_server, daemon=True).start()

load_dotenv()  

DISCORD_BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN")
if not DISCORD_BOT_TOKEN:
    raise ValueError("Missing DISCORD_BOT_TOKEN in .env, raised in main file")

DISCORD_CHANNEL_TOKEN = int(os.getenv("DISCORD_CHANNEL"))
if not DISCORD_CHANNEL_TOKEN:
    raise ValueError("Missing DISCORD_CHANNEL_TOKEN in .env, raise in main")

DISCORD_SERVER_ID = int(os.getenv("DISCORD_SERVER_ID"))
if not DISCORD_SERVER_ID:
    raise ValueError("Missing DISCORD_SERVER_ID in .env, raise in main")

intents = discord.Intents(guilds=True)
client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)

TailorResume(tree)

@client.event
async def on_ready():
    print(f"Logged in as {client.user} ({client.user.id})")
    log.info(f"Logged in as {client.user} ({client.user.id})")
    try:
        guild = discord.Object(id=DISCORD_SERVER_ID)
        tree.copy_global_to(guild=guild)
        await tree.sync()
        log.info("Slash commands synced to guild.")

    except Exception as e:
        log.exception("Slash commands sync failed: %s", e)


    channel = client.get_channel(DISCORD_CHANNEL_TOKEN) or await client.fetch_channel(DISCORD_CHANNEL_TOKEN)
    
    if channel:
        try:
            await channel.send("Bot is now online")
        except Exception as e:
            log.warning("Failed to send startup message: %s", e)
    else:
        log.warning("Channel not found; check DISCORD_CHANNEL and permissions")
        
client.run(DISCORD_BOT_TOKEN)
