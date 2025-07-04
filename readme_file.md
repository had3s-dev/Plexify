# Plex Discord Bot

A Discord bot that monitors your Plex media server and automatically posts your complete movie and TV show library to a Discord channel. The bot updates the list whenever new content is added to your Plex server.

## Features

- 🎬 **Complete Movie Library**: Shows all movies with release years
- 📺 **Complete TV Show Library**: Shows all TV shows with release years
- 🆕 **New Content Notifications**: Highlights recently added content
- 📝 **Clean Markdown Lists**: Displays content in organized, easy-to-read lists
- 🔄 **Automatic Updates**: Checks for new content every 30 minutes (configurable)
- 🗑️ **Message Management**: Automatically replaces old library messages

## Setup

### Prerequisites

- A Plex Media Server
- A Discord bot token
- A Discord server where you want to post the library

### Environment Variables

Set these environment variables:

- `DISCORD_TOKEN`: Your Discord bot token
- `PLEX_URL`: Your Plex server URL (e.g., `http://192.168.1.100:32400`)
- `PLEX_TOKEN`: Your Plex authentication token
- `CHANNEL_ID`: Discord channel ID where the bot will post

Optional variables:
- `UPDATE_INTERVAL_MINUTES`: How often to check for updates (default: 30)
- `MOVIES_SECTION`: Name of your Plex movie library (default: "Movies")
- `TV_SECTION`: Name of your Plex TV show library (default: "TV Shows")

### Getting Your Plex Token

1. Sign in to your Plex account
2. Go to Settings → Account → Privacy
3. Copy your Plex Token

### Getting Discord Channel ID

1. Enable Developer Mode in Discord (User Settings → Advanced → Developer Mode)
2. Right-click on your desired channel
3. Select "Copy ID"

## Deployment

### Railway (Recommended)

1. Fork this repository
2. Sign up at [railway.app](https://railway.app)
3. Connect your GitHub account
4. Deploy from your forked repository
5. Set environment variables in Railway dashboard

### Local Development

```bash
# Install dependencies
pip install -r requirements.txt

# Set environment variables
export DISCORD_TOKEN="your_discord_token"
export PLEX_URL="your_plex_url"
export PLEX_TOKEN="your_plex_token"
export CHANNEL_ID="your_channel_id"

# Run the bot
python plex_discord_bot.py
```

## How It Works

1. **Connects** to your Plex server and Discord
2. **Scans** your movie and TV show libraries
3. **Posts** a complete library list to your Discord channel
4. **Monitors** for new content every 30 minutes
5. **Updates** the library list when new content is detected
6. **Highlights** newly added content with 🆕 markers

## File Structure

```
plex-discord-bot/
├── plex_discord_bot.py    # Main bot code
├── requirements.txt       # Python dependencies
├── Procfile              # Railway deployment config
├── runtime.txt           # Python version
├── .gitignore           # Git ignore rules
└── README.md            # This file
```

## Troubleshooting

**Bot won't start:**
- Check that all environment variables are set correctly
- Verify your Discord bot token is valid
- Ensure your Plex server is accessible

**Bot can't find channel:**
- Make sure the channel ID is correct
- Verify the bot has permission to send messages in the channel

**No Plex content found:**
- Check that your library section names match the configured values
- Verify your Plex token has access to the libraries

## Contributing

Feel free to submit issues and enhancement requests!

## License

This project is open source and available under the MIT License.