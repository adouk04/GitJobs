import discord
from dotenv import load_dotenv
from discord import app_commands
from commands.TailorResume.TailorResume import TailorResume
import os

load_dotenv()

# constant values
DISCORD_BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN")
if not DISCORD_BOT_TOKEN:
    raise ValueError("Missing DISCORD_BOT_TOKEN in .env, raised in main file")
DISCORD_CHANNEL_TOKEN = os.getenv("DISCORD_CHANNEL")
if not DISCORD_CHANNEL_TOKEN:
    raise ValueError("Missing DISCORD_CHANNEL_TOKEN in .env, raise in main")
intents = discord.Intents.default()
intents.messages = True
client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client) # sends request to allow commands to discord

@client.event
async def on_ready():
    
    TailorResume(tree)  # Initialize the TailorResume command
    try:
        await tree.sync(guild=discord.Object(id=int(DISCORD_CHANNEL_TOKEN))) # defines slash commands in discord, discord registers on their side
    except Exception as e:
        print(f"sync failed: {e}")

    # get channel and if it's a volid token, notify that the bot is running 
    # else raise valueError for token 
    channel = client.get_channel(DISCORD_CHANNEL_TOKEN)
    if channel:
        await channel.send("Bot is now online")

    # activate bot, any changes should be made before this 
client.run(DISCORD_BOT_TOKEN)

