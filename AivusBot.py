import telebot
import json
import sqlite3
import logging
import google.generativeai as genai
from concurrent.futures import ThreadPoolExecutor

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('ai_bot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

GEMINI_API_KEY = "YOUR_GEMINI_API_KEY"
bot = telebot.TeleBot('YOUR_TELEGRAM_BOT_TOKEN')

try:
    if GEMINI_API_KEY and GEMINI_API_KEY != "YOUR_GEMINI_API_KEY_HERE":
        genai.configure(api_key=GEMINI_API_KEY)
        model = genai.GenerativeModel("gemini-2.5-flash")
        logger.info("Gemini model successfully initialized")
    else:
        logger.warning("Gemini API key not set or demo key is set")
        model = None
except Exception as e:
    logger.error(f"Error initializing Gemini: {e}")
    model = None

def init_db():
    conn = sqlite3.connect('AivusBot.db', check_same_thread=False)
    cursor = conn.cursor()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            last_name TEXT,
            private_chat_id INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS chat_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            messages TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (user_id)
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS ai_responses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            question TEXT,
            response TEXT,
            liked BOOLEAN DEFAULT 0,
            used_count INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (user_id)
        )
    ''')

    conn.commit()
    return conn

db_connection = init_db()

user_chat_sessions = {}
pending_ai_responses = {}

def get_or_create_user(user_id, username, first_name, last_name, private_chat_id=None):
    cursor = db_connection.cursor()
    cursor.execute('''
        INSERT OR REPLACE INTO users (user_id, username, first_name, last_name, private_chat_id)
        VALUES (?, ?, ?, ?, ?)
    ''', (user_id, username, first_name, last_name, private_chat_id))
    db_connection.commit()

def get_chat_session(user_id):
    if user_id not in user_chat_sessions:
        cursor = db_connection.cursor()
        cursor.execute('''
            SELECT messages FROM chat_sessions WHERE user_id = ? ORDER BY updated_at DESC LIMIT 1
        ''', (user_id,))
        result = cursor.fetchone()

        if result:
            messages = json.loads(result[0])
        else:
            messages = []

        user_chat_sessions[user_id] = messages

    return user_chat_sessions[user_id]

def save_chat_session(user_id, messages):
    cursor = db_connection.cursor()
    try:
        cursor.execute('''
            INSERT OR REPLACE INTO chat_sessions (user_id, messages, updated_at)
            VALUES (?, ?, CURRENT_TIMESTAMP)
        ''', (user_id, json.dumps(messages)))
        db_connection.commit()
        user_chat_sessions[user_id] = messages
    except Exception as e:
        logger.error(f"Error saving chat session: {e}")

def clear_chat_session(user_id):
    cursor = db_connection.cursor()
    try:
        cursor.execute('DELETE FROM chat_sessions WHERE user_id = ?', (user_id,))
        db_connection.commit()
        if user_id in user_chat_sessions:
            del user_chat_sessions[user_id]
    except Exception as e:
        logger.error(f"Error clearing chat session: {e}")

def get_saved_ai_response(user_id, question):
    cursor = db_connection.cursor()
    cursor.execute('''
        SELECT response FROM ai_responses 
        WHERE user_id = ? AND question = ? AND liked = 1
        ORDER BY used_count DESC, created_at DESC
        LIMIT 1
    ''', (user_id, question))
    result = cursor.fetchone()
    return result[0] if result else None

def save_ai_response(user_id, question, response, liked=True):
    cursor = db_connection.cursor()
    try:
        cursor.execute('''
            INSERT INTO ai_responses (user_id, question, response, liked, used_count)
            VALUES (?, ?, ?, ?, ?)
        ''', (user_id, question, response, liked, 1 if liked else 0))
        db_connection.commit()
        logger.info(f"AI response saved for user {user_id}")
    except Exception as e:
        logger.error(f"Error saving AI response: {e}")

def increment_ai_response_usage(response_id):
    cursor = db_connection.cursor()
    try:
        cursor.execute('''
            UPDATE ai_responses SET used_count = used_count + 1 WHERE id = ?
        ''', (response_id,))
        db_connection.commit()
    except Exception as e:
        logger.error(f"Error updating usage counter: {e}")

def query_gemini(user_id, question):
    try:
        saved_response = get_saved_ai_response(user_id, question)
        if saved_response:
            logger.info(f"Used saved response for user {user_id}")
            return f"💾 *Response from saved:*\n\n{saved_response}"

        if model is None:
            return "❌ AI service is temporarily unavailable.\n\nPlease check your Gemini API key settings."

        messages = get_chat_session(user_id)

        chat_history = []
        for msg in messages[-10:]:
            if msg['role'] == 'user':
                chat_history.append({"role": "user", "parts": [msg['content']]})
            else:
                chat_history.append({"role": "model", "parts": [msg['content']]})

        chat_history.append({"role": "user", "parts": [question]})

        def generate_response():
            response = model.generate_content(chat_history)
            return response.text.strip()

        with ThreadPoolExecutor() as executor:
            future = executor.submit(generate_response)
            reply = future.result(timeout=30)

        if reply:
            messages.append({"role": "user", "content": question})
            messages.append({"role": "assistant", "content": reply})

            if len(messages) > 20:
                messages = messages[-20:]

            save_chat_session(user_id, messages)
            return reply
        else:
            return "❌ Failed to get a response from AI. Response is empty or invalid."

    except Exception as e:
        logger.error(f"Gemini API error: {str(e)}")

        error_msg = str(e).lower()

        if "quota" in error_msg or "billing" in error_msg:
            return "❌ API quota exceeded or billing issue. Check your Google AI Studio settings."
        elif "safety" in error_msg or "blocked" in error_msg:
            return "❌ Request was blocked by safety system. Try rephrasing your question."
        elif "api key" in error_msg:
            return "❌ Problem with API key. Check your Gemini key validity."
        elif "network" in error_msg or "connection" in error_msg:
            return "❌ Network issue. Check your internet connection."
        elif "timeout" in error_msg:
            return "❌ Response timeout. Please try again."
        else:
            return f"❌ An error occurred while contacting AI: {str(e)}\n\nTry rephrasing your question or try again later."

def create_keyboard(main_menu=False):
    markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)

    if main_menu:
        buttons = ["🤖 Ask AI question", "🧹 Clear history", "❓ Help"]
        markup.add(*buttons)

    return markup

def create_feedback_keyboard():
    markup = telebot.types.InlineKeyboardMarkup()
    markup.row(
        telebot.types.InlineKeyboardButton("👍 Liked", callback_data="feedback_like"),
        telebot.types.InlineKeyboardButton("👎 Disliked", callback_data="feedback_dislike")
    )
    return markup

@bot.message_handler(commands=['start'])
def handle_start(message):
    chat_type = 'private' if message.chat.type == 'private' else 'group'
    user_id = message.from_user.id

    get_or_create_user(
        user_id=user_id,
        username=message.from_user.username,
        first_name=message.from_user.first_name,
        last_name=message.from_user.last_name,
        private_chat_id=message.chat.id if chat_type == 'private' else None
    )

    welcome_text = (
        f"Hello, {message.from_user.first_name}! 👋\n\n"
        "I'm an AI assistant powered by Google Gemini! 🤖\n"
        "Ask me ANY question, and I'll try to answer it!\n\n"
        "I remember the context of our conversation and can learn from your ratings.\n\n"
        "Just write your question or choose an action from the menu:"
    )
    bot.send_message(message.chat.id, welcome_text, reply_markup=create_keyboard(main_menu=True), parse_mode='Markdown')

@bot.message_handler(commands=['ai', 'help', 'clear'])
def handle_ai_commands(message):
    chat_type = 'private' if message.chat.type == 'private' else 'group'
    user_id = message.from_user.id

    get_or_create_user(
        user_id=user_id,
        username=message.from_user.username,
        first_name=message.from_user.first_name,
        last_name=message.from_user.last_name,
        private_chat_id=message.chat.id if chat_type == 'private' else None
    )

    if message.text.startswith('/ai'):
        ai_command(message)
    elif message.text.startswith('/help'):
        help_command(message)
    elif message.text.startswith('/clear'):
        clear_history_command(message)

def ai_command(message):
    bot.send_message(
        message.chat.id,
        "🤖 *AI Assistant Mode*\n\n"
        "Ask me ANY question, and I'll try to answer it! 🚀\n"
        "I remember the context of our conversation.\n\n"
        "Example questions:\n"
        "• Explain quantum physics in simple terms\n"
        "• Tell me about the history of Ancient Rome\n"
        "• Help me write Python code\n\n"
        "Waiting for your question...",
        parse_mode='Markdown'
    )

def help_command(message):
    help_text = (
        "📖 *AI Assistant Help*\n\n"
        
        "🤖 *How to use:*\n"
        "• Just write any question in the chat\n"
        "• I'll answer using Google Gemini AI\n"
        "• I remember the context of recent messages\n\n"
        
        "💡 *Features:*\n"
        "• Context memory (remembers up to 20 recent messages)\n"
        "• Saving liked responses\n"
        "• Learning from your ratings\n"
        "• Support for various topics and questions\n\n"
        
        "⚡ *Commands:*\n"
        "• /start - restart the bot\n"
        "• /ai - activate AI mode\n"
        "• /clear - clear conversation history\n"
        "• /help - show this help\n\n"
        
        "🎯 *Tips:*\n"
        "• Be specific in your questions\n"
        "• Use 👍/👎 to rate responses\n"
        "• Clear history if you want to start a new dialogue\n\n"
        
        "*Ask any question - I'm ready to help!* 🚀"
    )
    bot.send_message(message.chat.id, help_text, parse_mode='Markdown')

def clear_history_command(message):
    user_id = message.from_user.id
    clear_chat_session(user_id)
    bot.send_message(
        message.chat.id,
        "🧹 Conversation history cleared! Starting a new dialogue!",
        reply_markup=create_keyboard(main_menu=True)
    )

@bot.message_handler(func=lambda message: message.text in [
    "🤖 Ask AI question", "🧹 Clear history", "❓ Help"
])
def handle_menu_buttons(message):
    chat_type = 'private' if message.chat.type == 'private' else 'group'
    user_id = message.from_user.id

    get_or_create_user(
        user_id=user_id,
        username=message.from_user.username,
        first_name=message.from_user.first_name,
        last_name=message.from_user.last_name,
        private_chat_id=message.chat.id if chat_type == 'private' else None
    )

    if message.text == "🤖 Ask AI question":
        ai_command(message)
    elif message.text == "🧹 Clear history":
        clear_history_command(message)
    elif message.text == "❓ Help":
        help_command(message)

@bot.callback_query_handler(func=lambda call: call.data.startswith('feedback_'))
def handle_feedback(call):
    user_id = call.from_user.id
    message_id = call.message.message_id
    
    if call.data == 'feedback_like':
        if user_id in pending_ai_responses and message_id in pending_ai_responses[user_id]:
            question, response = pending_ai_responses[user_id][message_id]
            save_ai_response(user_id, question, response, liked=True)
            
            del pending_ai_responses[user_id][message_id]
            
            bot.answer_callback_query(call.id, "✅ Response saved! I'll use it in the future.")
            bot.edit_message_text(
                f"🤖 *AI Response:*\n\n{response}\n\n✅ *Response saved to database*",
                call.message.chat.id,
                call.message.message_id,
                parse_mode='Markdown'
            )
        else:
            bot.answer_callback_query(call.id, "⚠️ Response information not found")
    
    elif call.data == 'feedback_dislike':
        if user_id in pending_ai_responses and message_id in pending_ai_responses[user_id]:
            question, old_response = pending_ai_responses[user_id][message_id]
            
            del pending_ai_responses[user_id][message_id]
            
            bot.answer_callback_query(call.id, "🔄 Generating new response...")
            
            new_response = query_gemini(user_id, question)
            
            sent_message = bot.send_message(
                call.message.chat.id,
                f"🤖 *AI Response (updated):*\n\n{new_response}",
                parse_mode='Markdown',
                reply_markup=create_feedback_keyboard()
            )
            
            if user_id not in pending_ai_responses:
                pending_ai_responses[user_id] = {}
            pending_ai_responses[user_id][sent_message.message_id] = (question, new_response)
            
            try:
                bot.delete_message(call.message.chat.id, call.message.message_id)
            except:
                pass

@bot.message_handler(func=lambda message: True)
def handle_all_messages(message):
    if message.text and message.text.startswith('/'):
        return

    chat_type = 'private' if message.chat.type == 'private' else 'group'
    user_id = message.from_user.id
    chat_id = message.chat.id

    get_or_create_user(
        user_id=user_id,
        username=message.from_user.username,
        first_name=message.from_user.first_name,
        last_name=message.from_user.last_name,
        private_chat_id=chat_id if chat_type == 'private' else None
    )

    bot.send_chat_action(chat_id, 'typing')
    ai_response = query_gemini(user_id, message.text)
    
    sent_message = bot.send_message(
        chat_id, 
        f"🤖 *AI Response:*\n\n{ai_response}", 
        parse_mode='Markdown',
        reply_markup=create_feedback_keyboard()
    )
    
    if user_id not in pending_ai_responses:
        pending_ai_responses[user_id] = {}
    pending_ai_responses[user_id][sent_message.message_id] = (message.text, ai_response)

def check_gemini_availability():
    try:
        if model:
            response = model.generate_content("Hello! Reply 'OK' if you are working.")
            return response.text is not None
        return False
    except:
        return False

if __name__ == "__main__":
    print("=" * 50)
    print("🤖 AI Bot is starting...")

    gemini_available = check_gemini_availability()

    if gemini_available:
        print("✅ Gemini AI is active and ready to work!")
    else:
        print("❌ Gemini AI is unavailable. Check API key and settings.")

    print("🤖 AI bot is ready to work! Use /start")
    print("=" * 50)

    try:
        bot.polling(none_stop=True, interval=0, timeout=60)
    except Exception as e:
        logger.error(f"Error starting bot: {e}")
        print(f"❌ An error occurred: {e}")