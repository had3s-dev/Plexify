import discord
from discord.ext import commands, tasks
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
        self.library_messages = []  # Store multiple messages for full lists
        
    async def on_ready(self):
        print(f'🤖 Bot logged in as {self.user}')
        
        # Connect to Plex
        try:
            self.plex = PlexServer(PLEX_URL, PLEX_TOKEN)
            print(f'📡 Connected to Plex server: {self.plex.friendlyName}')
        except Exception as e:
            print(f'❌ Failed to connect to Plex: {e}')
            return
            
        # Get Discord channel
        self.channel = self.get_channel(CHANNEL_ID)
        if not self.channel:
            print(f'❌ Could not find Discord channel with ID: {CHANNEL_ID}')
            return
            
        print(f'📺 Connected to Discord channel: #{self.channel.name}')
        
        # Start the update loop
        self.update_library.start()
        
    async def on_message(self, message):
        # Don't respond to ourselves or other bots
        if message.author == self.user or message.author.bot:
            return
            
        # Check if the message is in the configured channel
        if message.channel.id != CHANNEL_ID:
            return
            
        # Manual sync command
        if message.content.lower() in ('!sync', '!update', '!refresh'):
            try:
                msg = await message.channel.send('🔄 Syncing Plex library...')
                current_content = await self.get_library_content()
                current_titles = set(item['key'] for item in current_content)
                new_items = current_titles - self.last_known_content if self.last_known_content else set()
                await self.post_complete_library(current_content, new_items)
                self.last_known_content = current_titles
                await msg.edit(content='✅ Library synced successfully!')
            except Exception as e:
                await message.channel.send(f'❌ Error syncing library: {str(e)}')
        
    @tasks.loop(minutes=UPDATE_INTERVAL_MINUTES)
    async def update_library(self):
        """Check for new content and update the library list"""
        try:
            # Get current content
            current_content = await self.get_library_content()
            current_titles = set(item['key'] for item in current_content)
            
            # Check if this is the first run or if content changed
            if not self.last_known_content or current_titles != self.last_known_content:
                new_items = current_titles - self.last_known_content if self.last_known_content else set()
                
                if new_items:
                    print(f'📥 Found {len(new_items)} new items')
                
                await self.post_complete_library(current_content, new_items)
                self.last_known_content = current_titles
                
        except Exception as e:
            print(f'❌ Error updating library: {e}')
            
    async def get_library_content(self):
        """Get all movies and TV shows from Plex"""
        content = []
        
        try:
            # Get movies
            movies_section = self.plex.library.section(MOVIES_SECTION)
            for movie in movies_section.all():
                content.append({
                    'key': f"movie_{movie.ratingKey}",
                    'title': movie.title,
                    'year': movie.year or 'Unknown',
                    'type': '🎬',
                    'category': 'Movies'
                })
                
            # Get TV shows
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
        """Delete all previous library messages"""
        for message in self.library_messages:
            try:
                await message.delete()
            except:
                pass
        self.library_messages = []
    
    async def post_complete_library(self, content, new_items=None):
        """Post the complete library as markdown messages"""
        
        # Clear old messages first
        await self.clear_old_messages()
        
        # Sort content alphabetically
        movies = sorted([item for item in content if item['category'] == 'Movies'], 
                       key=lambda x: x['title'].lower())
        shows = sorted([item for item in content if item['category'] == 'TV Shows'], 
                      key=lambda x: x['title'].lower())
        
        # Create header embed
        embed = discord.Embed(
            title="📚 Plex Media Library",
            description=f"**Movies:** {len(movies)} | **TV Shows:** {len(shows)}",
            color=0xe5a00d,
            timestamp=datetime.now()
        )
        
        # Add new content notification if any
        if new_items:
            new_content = [item for item in content if item['key'] in new_items]
            new_list = []
            for item in new_content[:10]:  # Limit to 10 new items in embed
                new_list.append(f"{item['type']} {item['title']} ({item['year']})")
            
            if new_list:
                embed.add_field(
                    name="🆕 Recently Added",
                    value="\n".join(new_list),
                    inline=False
                )
        
        embed.set_footer(text=f"Last updated • Next check in {UPDATE_INTERVAL_MINUTES} minutes")
        
        # Post header message
        header_message = await self.channel.send(embed=embed)
        self.library_messages.append(header_message)
        
        # Post complete movies list
        if movies:
            await self.post_markdown_list(movies, "🎬 Movies", new_items)
        
        # Post complete TV shows list
        if shows:
            await self.post_markdown_list(shows, "📺 TV Shows", new_items)
    
    async def post_markdown_list(self, items, title, new_items=None):
        """Post a complete markdown list for movies or TV shows"""
        
        # Discord message limit is 2000 characters, so we need to split large lists
        current_message = f"## {title}\n\n"
        
        for item in items:
            marker = "🆕 " if item['key'] in (new_items or set()) else ""
            line = f"• {marker}{item['title']} ({item['year']})\n"
            
            # If adding this line would exceed Discord's limit, send current message and start new one
            if len(current_message + line) > 1900:  # Leave some buffer
                message = await self.channel.send(current_message)
                self.library_messages.append(message)
                current_message = line
            else:
                current_message += line
        
        # Send the final message if there's content
        if current_message.strip() and current_message != f"## {title}\n\n":
            message = await self.channel.send(current_message)
            self.library_messages.append(message)

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