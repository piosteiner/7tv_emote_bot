import requests
import telegram
from telegram.ext import Application, CommandHandler
import asyncio
import aiohttp
from PIL import Image
import io
import os

class SevenTVToTelegramBot:
    def __init__(self, telegram_token):
        self.telegram_token = telegram_token
        self.bot = telegram.Bot(token=telegram_token)
        
    async def get_7tv_emote_set(self, set_id):
        """Fetch emote set data from 7TV API"""
        # Using community API endpoints
        url = f"https://7tv.io/v3/emote-sets/{set_id}"
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    return data
                else:
                    raise Exception(f"Failed to fetch 7TV data: {response.status}")
    
    async def download_emote_image(self, emote_url, size="2x"):
        """Download emote image and convert to proper format for Telegram"""
        async with aiohttp.ClientSession() as session:
            async with session.get(emote_url) as response:
                if response.status == 200:
                    image_data = await response.read()
                    
                    # Convert to PNG if needed and resize
                    img = Image.open(io.BytesIO(image_data))
                    
                    # Convert to RGBA if not already
                    if img.mode != 'RGBA':
                        img = img.convert('RGBA')
                    
                    # Resize to 512x512 (Telegram requirement)
                    img = img.resize((512, 512), Image.Resampling.LANCZOS)
                    
                    # Save as PNG
                    output = io.BytesIO()
                    img.save(output, format='PNG')
                    output.seek(0)
                    
                    return output
                else:
                    raise Exception(f"Failed to download image: {response.status}")
    
    async def create_telegram_sticker_set(self, user_id, set_name, set_title, emotes_data):
        """Create a new Telegram sticker set from 7TV emotes"""
        
        stickers = []
        
        for emote in emotes_data['emotes']:
            emote_name = emote['name']
            
            # Get the best quality image URL
            image_url = None
            for host in emote['data']['host']['files']:
                if host['name'] == '2x.webp':  # Prefer 2x quality
                    image_url = f"https:{emote['data']['host']['url']}/{host['name']}"
                    break
            
            if not image_url:
                # Fallback to 1x if 2x not available
                for host in emote['data']['host']['files']:
                    if host['name'] == '1x.webp':
                        image_url = f"https:{emote['data']['host']['url']}/{host['name']}"
                        break
            
            if image_url:
                try:
                    # Download and process the image
                    image_data = await self.download_emote_image(image_url)
                    
                    # Create InputSticker object
                    sticker = telegram.InputSticker(
                        sticker=image_data,
                        emoji_list=['😀'],  # Default emoji, can be customized
                        format='static'
                    )
                    stickers.append(sticker)
                    
                    print(f"Processed emote: {emote_name}")
                    
                except Exception as e:
                    print(f"Failed to process emote {emote_name}: {e}")
                    continue
        
        # Create the sticker set
        try:
            success = await self.bot.create_new_sticker_set(
                user_id=user_id,
                name=set_name,
                title=set_title,
                stickers=stickers[:50],  # Telegram limit: max 50 stickers per set
                sticker_format='static'
            )
            
            if success:
                sticker_set_url = f"https://t.me/addstickers/{set_name}"
                return sticker_set_url
            else:
                raise Exception("Failed to create sticker set")
                
        except Exception as e:
            raise Exception(f"Error creating sticker set: {e}")
    
    async def convert_7tv_set(self, user_id, set_id, custom_name=None):
        """Main function to convert 7TV set to Telegram stickers"""
        
        # Fetch 7TV emote set data
        emotes_data = await self.get_7tv_emote_set(set_id)
        
        # Generate unique sticker set name (required format: name_by_botusername)
        bot_info = await self.bot.get_me()
        bot_username = bot_info.username
        
        if custom_name:
            set_name = f"{custom_name}_by_{bot_username}"
        else:
            set_name = f"7tv_{set_id}_by_{bot_username}"
        
        set_title = emotes_data.get('name', f"7TV Emotes - {set_id}")
        
        # Create the sticker set
        sticker_set_url = await self.create_telegram_sticker_set(
            user_id, set_name, set_title, emotes_data
        )
        
        return sticker_set_url, len(emotes_data.get('emotes', []))

# Bot command handlers
async def convert_command(update, context):
    """Handle /convert command"""
    
    if len(context.args) != 1:
        await update.message.reply_text(
            "Usage: /convert <7TV_SET_ID>\n"
            "Example: /convert 01K1BPC2WFZB8QA3T04MPBTSS9"
        )
        return
    
    set_id = context.args[0]
    user_id = update.effective_user.id
    
    await update.message.reply_text("🔄 Converting your 7TV emote set to Telegram stickers...")
    
    try:
        bot_converter = SevenTVToTelegramBot(context.bot.token)
        sticker_url, emote_count = await bot_converter.convert_7tv_set(user_id, set_id)
        
        await update.message.reply_text(
            f"✅ Successfully converted {emote_count} emotes!\n"
            f"Add your sticker set: {sticker_url}"
        )
        
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)}")

async def start_command(update, context):
    """Handle /start command"""
    await update.message.reply_text(
        "🤖 Welcome to 7TV to Telegram Stickers Bot!\n\n"
        "Send me your 7TV emote set ID using:\n"
        "/convert <SET_ID>\n\n"
        "To find your set ID, go to your 7TV profile and copy the ID from the URL."
    )

def main():
    """Main function to run the bot"""
    
    # Replace with your bot token
    BOT_TOKEN = "YOUR_BOT_TOKEN_HERE"
    
    # Create application
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Add command handlers
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("convert", convert_command))
    
    # Run the bot
    print("Bot is running...")
    application.run_polling()

if __name__ == "__main__":
    main()
