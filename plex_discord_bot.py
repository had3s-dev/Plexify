import discord
from discord.ext import tasks
from plexapi.server import PlexServer
import asyncio
import json
import os
from datetime import datetime

# Configuration - Now using environment variables
DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
PLEX_URL = os.getenv('PLEX_URL')
PLEX_TOKEN = os.getenv('PLEX_TOKEN')
CHANNEL_ID = int(os.getenv('CHANNEL_ID', '0'))

# Optional: Customize these
UPDATE_INTERVAL_MINUTES = int(os.getenv('UPDATE_INTERVAL_MINUTES', '120'))
MOVIES_SECTION = os.getenv('MOVIES_SECTION', 'Movies')
TV_SECTION = os.getenv('TV_SECTION', 'TV Shows')

# Validate required environment variables
if not all([DISCORD_TOKEN, PLEX_URL, PLEX_TOKEN, CHANNEL_ID]):
    print("❌ Missing required environment variables!")
    print("Required: DISCORD_TOKEN, PLEX_URL, PLEX_TOKEN, CHANNEL_ID")
    exit(1)

class PlexDiscordBot(discord.Client):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(intents=intents)
        
        self.plex = None
        self.channel = None
        self.last_known_content = set()
        self.library_messages = []
        
    async def on_ready(self):
        print(f'🤖 Bot logged in as {self.user}')
        
        try:
            self.plex = PlexServer(PLEX_URL, PLEX_TOKEN)
            print(f'📡 Connected to Plex server: {self.plex.friendlyName}')
        except Exception as e:
            print(f'❌ Failed to connect to Plex: {e}')
            return
            
        self.channel = self.get_channel(CHANNEL_ID)
        if not self.channel:
            print(f'❌ Could not find Discord channel with ID: {CHANNEL_ID}')
            return
            
        print(f'📺 Connected to Discord channel: #{self.channel.name}')
        
        self.update_library.start()
        
    async def on_message(self, message):
        if message.author == self.user or message.author.bot:
            return
        if message.channel.id != CHANNEL_ID:
            return
            
        if message.content.lower() in ('!sync', '!update', '!refresh'):
            try:
                msg = await message.channel.send('🔄 Syncing Plex library...')
                current_content = await self.get_library_content()
                current_titles = set(item['key'] for item in current_content)
                new_items = current_titles - self.last_known_content if self.last_known_content else set()
                await self.post_complete_library(current_content, new_items)
                self.last_known_content = current_titles
                await msg.edit(content='✅ Library synced successfully!')
            except discord.Forbidden as e:
                print(f"❌ Forbidden while syncing library: {e}")
                await message.channel.send(f"❌ Missing permissions: {e}")
            except Exception as e:
                print(f"❌ Error syncing library: {e}")
                await message.channel.send(f"❌ Error syncing library: {str(e)}")
        
    @tasks.loop(minutes=UPDATE_INTERVAL_MINUTES)
    async def update_library(self):
        try:
            print(f"⏳ Checking for updates at {datetime.now()}")
            current_content = await self.get_library_content()
            current_titles = set(item['key'] for item in current_content)
            new_items = current_titles - self.last_known_content if self.last_known_content else set()
            if new_items:
                print(f"📥 Found {len(new_items)} new items.")
                await self.post_complete_library(current_content, new_items)
            self.last_known_content = current_titles
        except discord.Forbidden as e:
            print(f"❌ Forbidden error (permissions): {e}")
        except discord.HTTPException as e:
            print(f"❌ HTTP error during library update: {e}")
        except Exception as e:
            print(f"❌ General error updating library: {e}")
            
    async def get_library_content(self):
        content = []
        try:
            movies_section = self.plex.library.section(MOVIES_SECTION)
            for movie in movies_section.all():
                content.append({
                    'key': f"movie_{movie.ratingKey}",
                    'title': movie.title,
                    'year': movie.year or 'Unknown',
                    'type': '🎬',
                    'category': 'Movies'
                })
            tv_section = self.plex.library.section(TV_SECTION)
            for show in tv_section.all():
                content.append({
                    'key': f"show_{show.ratingKey}",
                    'title': show.title,
                    'year': show.year or 'Unknown',
                    'type': '📺',
                    'category': 'TV Shows'
                })
        except Exception as e:
            print(f'❌ Error getting library content: {e}')
        return content
    
    async def clear_old_messages(self):
        for message in self.library_messages:
            try:
                if message.author == self.user:
                    print(f"🗑️ Deleting old message: {message.id}")
                    await message.delete()
                else:
                    print(f"⚠️ Skipping message not sent by bot: {message.id}")
            except discord.Forbidden as e:
                print(f"❌ Forbidden while deleting message {message.id}: {e}")
            except Exception as e:
                print(f"⚠️ Could not delete message {message.id}: {e}")
        self.library_messages = []
    
    async def post_complete_library(self, content, new_items=None):
        try:
            await self.clear_old_messages()
            movies = sorted([item for item in content if item['category'] == 'Movies'], 
                           key=lambda x: x['title'].lower())
            shows = sorted([item for item in content if item['category'] == 'TV Shows'], 
                          key=lambda x: x['title'].lower())

            embed = discord.Embed(
                title="📚 Plex Media Library",
                description=f"**Movies:** {len(movies)} | **TV Shows:** {len(shows)}",
                color=0xe5a00d,
                timestamp=datetime.now()
            )

            if new_items:
                new_content = [item for item in content if item['key'] in new_items]
                new_list = []
                for item in new_content[:10]:
                    new_list.append(f"{item['type']} {item['title']} ({item['year']})")
                if new_list:
                    embed.add_field(
                        name="🆕 Recently Added",
                        value="\n".join(new_list),
                        inline=False
                    )

            embed.set_footer(text=f"Last updated • Next check in {UPDATE_INTERVAL_MINUTES} minutes")

            print("📨 Sending library header embed...")
            header_message = await self.channel.send(embed=embed)
            self.library_messages.append(header_message)

            if movies:
                await self.post_markdown_list(movies, "🎬 Movies", new_items)
            if shows:
                await self.post_markdown_list(shows, "📺 TV Shows", new_items)
        except discord.Forbidden as e:
            print(f"❌ Forbidden error posting library: {e}")
        except Exception as e:
            print(f"❌ Error posting library: {e}")
    
    async def post_markdown_list(self, items, title, new_items=None):
        current_message = f"## {title}\n\n"
        for item in items:
            marker = "🆕 " if item['key'] in (new_items or set()) else ""
            line = f"• {marker}{item['title']} ({item['year']})\n"
            if len(current_message + line) > 1900:
                try:
                    print("📨 Sending markdown list chunk...")
                    message = await self.channel.send(current_message)
                    self.library_messages.append(message)
                except discord.Forbidden as e:
                    print(f"❌ Forbidden sending markdown: {e}")
                    return
                current_message = line
            else:
                current_message += line

        if current_message.strip() and current_message != f"## {title}\n\n":
            try:
                print("📨 Sending final markdown message...")
                message = await self.channel.send(current_message)
                self.library_messages.append(message)
            except discord.Forbidden as e:
                print(f"❌ Forbidden sending final markdown: {e}")

# Run the bot
if __name__ == "__main__":
    bot = PlexDiscordBot()
    print("🚀 Starting Plex Discord Bot...")
    print("📡 Connecting to Plex and Discord...")
    try:
        bot.run(DISCORD_TOKEN)
    except Exception as e:
        print(f"❌ Failed to start bot: {e}")
        print("💡 Check your environment variables and bot permissions!")