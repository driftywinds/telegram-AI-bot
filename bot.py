import os
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
text_model = genai.GenerativeModel('gemini-pro')
vision_model = genai.GenerativeModel('gemini-pro-vision')

# Store chat histories per user
chats = {}

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
            await message.reply_text(response.text)
            
        else:
            # Handle text messages
            if user_id not in chats:
                chats[user_id] = text_model.start_chat(history=[])
            
            user_message = message.text
            response = await chats[user_id].send_message_async(user_message)
            await message.reply_text(response.text)
            
    except Exception as e:
        await message.reply_text(f"Sorry, there was an error: {str(e)}")

def main():
    application = Application.builder().token(os.getenv('TELEGRAM_BOT_TOKEN')).build()
    application.add_handler(MessageHandler(filters.TEXT | filters.PHOTO | filters.Document.IMAGE, handle_message))
    print("Bot is running...")
    application.run_polling()

if __name__ == '__main__':
    main()
