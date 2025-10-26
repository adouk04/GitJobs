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

# probably not needed in main since not calling gpt here
#OPENAI_KEY = os.getenv("OPENAI_KEY")
#if not OPENAI_KEY:
#    raise ValueError("Missing OPENAI_KEY in .env, raised in main file")

# MAIN/CONSTRUCTOR (Heart of the discord bot, everything is ran in this file) 
@client.event
async def on_ready():
    
    TailorResume(tree)  # Initialize the TailorResume command
    try:
        await tree.sync() # defines slash commands in discord, discord registers on their side
    except Exception as e:
        print(f"sync failed: {e}")

    # get channel and if it's a volid token, notify that the bot is running 
    # else raise valueError for token 
    channel = client.get_channel(DISCORD_CHANNEL_TOKEN)
    if channel:
        await channel.send("Bot is now online")
    
    ## Receives user prompt /tailorresume (insert .pdf file)
    # - add cases if its not an throw a null pointer exception ("invalid file")
    #   - then send back to discord as a bot message 
    ## Parse resume (temporary .json file?) 
    # - put limitors on file size due to discord free tier limit token
    # - Parses original resume after getting a successful file
    # - Make specific, concise, and detailed prompts to send to OpenAI
    #   - has resume prompts to make not sound like gpt
    #   - has prompt to receive back text on what its changed
    # - return new resume with changes
    ## Output resume back into discord

    # activate bot, any changes should be made before this 
client.run(DISCORD_BOT_TOKEN)

