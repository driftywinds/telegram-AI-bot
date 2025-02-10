import logging
from telegram import Update
from telegram.ext import Application, MessageHandler, CommandHandler, filters, ContextTypes
import aiohttp
import json
from collections import deque

# Configuration
TELEGRAM_TOKEN = "<YOUR TELEGRAM BOT TOKEN FROM BOT FATHER>"
OPENROUTER_API_KEY = "<YOUR OPENROUTER API KEY>"
DEEPSEEK_MODEL = "deepseek/deepseek-r1:free" # you can change this to any other model as you see fit
MAX_HISTORY = 6  # Keep last 3 exchanges (user + assistant)

# Store conversation history using deque for efficient memory management
conversation_history = {}

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send a message when the command /start is issued."""
    await update.message.reply_text(
        "Hi! I'm a DeepSeek-powered AI assistant with conversation memory. "
        "Send me a message and I'll help you!\n"
        "Use /reset to clear our conversation history."
    )

async def reset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Reset the conversation history"""
    chat_id = update.effective_chat.id
    conversation_history[chat_id] = deque(maxlen=MAX_HISTORY)
    await update.message.reply_text("Conversation history cleared!")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle incoming user messages with conversation history"""
    chat_id = update.effective_chat.id
    user_message = update.message.text
    
    try:
        # Initialize history if needed
        if chat_id not in conversation_history:
            conversation_history[chat_id] = deque(maxlen=MAX_HISTORY)
            
        # Add user message to history
        conversation_history[chat_id].append({"role": "user", "content": user_message})
        
        # Show typing indicator
        await context.bot.send_chat_action(
            chat_id=chat_id, 
            action="typing"
        )
        
        # Generate response using OpenRouter API
        async with aiohttp.ClientSession() as session:
            response = await generate_deepseek_response(
                session=session,
                history=list(conversation_history[chat_id])
            )
        
        # Add assistant response to history
        conversation_history[chat_id].append({"role": "assistant", "content": response})
        
        # Send the response back to user
        await update.message.reply_text(response)
        
    except Exception as e:
        logging.error(f"Error: {e}", exc_info=True)
        await update.message.reply_text("Sorry, I'm having trouble processing your request. Please try again.")

async def generate_deepseek_response(session: aiohttp.ClientSession, history: list) -> str:
    """Send async request to OpenRouter API and return generated text"""
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://github.com/your-repository",
        "X-Title": "DeepSeek Telegram Bot"
    }

    data = {
        "model": DEEPSEEK_MODEL,
        "messages": history,
        "temperature": 0.7,
        "max_tokens": 1000,
        "stream": False
    }

    try:
        async with session.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers=headers,
            json=data
        ) as response:
            response_json = await response.json()
            
            if response.status == 200:
                if 'choices' in response_json and len(response_json['choices']) > 0:
                    return response_json['choices'][0]['message']['content'].strip()
                else:
                    logging.error(f"Unexpected API response: {response_json}")
                    return "Sorry, I received an unexpected response format."
            
            error_msg = f"API Error: {response.status} - {response_json.get('error', {}).get('message', 'Unknown error')}"
            logging.error(error_msg)
            return "Sorry, I encountered an API error processing your request."

    except json.JSONDecodeError:
        logging.error("Failed to parse API response as JSON")
        return "Sorry, I received an invalid response from the API."
    except Exception as e:
        logging.error(f"Network error: {str(e)}")
        return "Sorry, I'm having trouble connecting to the API."

def main():
    """Start the bot."""
    application = Application.builder().token(TELEGRAM_TOKEN).build()

    # Register handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("reset", reset))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Run the bot
    application.run_polling()

if __name__ == "__main__":
    main()
