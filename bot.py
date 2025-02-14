import os
import re
import base64
import google.generativeai as genai
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes
from dotenv import load_dotenv
import mimetypes

# Load environment variables
load_dotenv()

# Configure Google AI
genai.configure(api_key=os.getenv('GOOGLE_API_KEY'))
text_model = genai.GenerativeModel('gemini-2.0-flash') # You can change this according to your requirements
vision_model = genai.GenerativeModel('gemini-2.0-flash') # You can change this according to your requirements

# Store chat histories per user
chats = {}

def format_response(text):
    """Convert markdown-style formatting to Telegram HTML formatting"""
    # Convert **bold** to <b>bold</b>
    text = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', text)
    # Convert *italic* to <i>italic</i>
    text = re.sub(r'\*(.*?)\*', r'<i>\1</i>', text)
    # Convert `code` to <code>code</code>
    text = re.sub(r'`(.*?)`', r'<code>\1</code>', text)
    # Convert ~~strikethrough~~ to <s>strikethrough</s>
    text = re.sub(r'~~(.*?)~~', r'<s>\1</s>', text)
    # Convert [link text](url) to <a href="url">link text</a>
    text = re.sub(r'\[(.*?)\]\((.*?)\)', r'<a href="\2">\1</a>', text)
    return text

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    message = update.message
    
    try:
        if message.photo or message.document:
            # Get the file ID and MIME type
            if message.photo:
                file_id = message.photo[-1].file_id
                mime_type = "image/jpeg"
            else:
                file_id = message.document.file_id
                mime_type = message.document.mime_type
                if not mime_type.startswith('image/'):
                    await message.reply_text("Please send an image file (JPEG, PNG, WEBP).")
                    return

            # Download and prepare image
            file = await context.bot.get_file(file_id)
            image_bytes = await file.download_as_bytearray()
            
            # Convert to base64
            base64_image = base64.b64encode(image_bytes).decode('utf-8')
            
            # Create content structure
            contents = {
                "parts": [
                    {"text": message.caption or "What's in this image?"},
                    {
                        "inline_data": {
                            "mime_type": mime_type,
                            "data": base64_image
                        }
                    }
                ]
            }

            # Get response from vision model
            response = await vision_model.generate_content_async(contents)
            formatted_response = format_response(response.text)
            await message.reply_text(formatted_response, parse_mode='HTML')
            
        else:
            # Handle text messages
            if user_id not in chats:
                chats[user_id] = text_model.start_chat(history=[])
            
            user_message = message.text
            response = await chats[user_id].send_message_async(user_message)
            formatted_response = format_response(response.text)
            await message.reply_text(formatted_response, parse_mode='HTML')
            
    except Exception as e:
        await message.reply_text(f"Sorry, there was an error: {str(e)}")

def main():
    application = Application.builder().token(os.getenv('TELEGRAM_BOT_TOKEN')).build()
    application.add_handler(MessageHandler(filters.TEXT | filters.PHOTO | filters.Document.IMAGE, handle_message))
    print("Bot is running...")
    application.run_polling()

if __name__ == '__main__':
    main()
