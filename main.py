import os
import requests
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from flask import Flask, request
from supabase import create_client, Client
from dotenv import load_dotenv

# تحميل المتغيرات من ملف .env
load_dotenv()

# جلب المعلومات الأساسية
BOT_TOKEN = os.getenv('BOT_TOKEN')
API_KEY = os.getenv('API_KEY')
ADMIN_ID = int(os.getenv('ADMIN_ID', 0))
API_URL = "https://kd1s.com/api/v2"

# تهيئة الاتصال بقاعدة البيانات (Supabase)
supabase: Client = create_client(os.getenv('SUPABASE_URL'), os.getenv('SUPABASE_KEY'))

# تهيئة البوت وتطبيق فلاسك للويب هوك
bot = telebot.TeleBot(BOT_TOKEN)
app = Flask(__name__)

# --- دالة لجلب تفاصيل الخدمة من موقع الرشق ---
def fetch_service_from_api(service_id):
    payload = {"key": API_KEY, "action": "services"}
    try:
        response = requests.post(API_URL, json=payload).json()
        for service in response:
            if str(service.get('service')) == str(service_id):
                return service
    except Exception as e:
        print("API Error:", e)
    return None

# --- رسالة الترحيب ---
@bot.message_handler(commands=['start'])
def start_message(message):
    bot.reply_to(message, "أهلاً بيك في بوت خدمات الرشق! 🚀\nالبوت شغال وجاهز لاستقبال الطلبات.")

# --- قسم الأدمن: إضافة خدمة جديدة ---
@bot.message_handler(commands=['add'])
def add_service_step1(message):
    if message.from_user.id != ADMIN_ID:
        return
    msg = bot.reply_to(message, "دزلي رقم الخدمة (الـ ID) من الموقع:")
    bot.register_next_step_handler(msg, add_service_step2)

def add_service_step2(message):
    service_id = message.text.strip()
    bot.reply_to(message, "جاري البحث عن الخدمة بالموقع... ⏳")
    
    service_data = fetch_service_from_api(service_id)
    
    if not service_data:
        bot.reply_to(message, "❌ الخدمة مموجودة أو اكو مشكلة بالـ API.")
        return
    
    # حفظ البيانات مؤقتاً
    temp_data = {
        "api_id": service_id,
        "original_name": service_data['name'],
        "original_rate": service_data['rate']
    }
    
    msg = bot.reply_to(message, f"✅ لگيت الخدمة!\n\n📌 اسمها: {temp_data['original_name']}\n💰 سعرها بالموقع: {temp_data['original_rate']}$\n\nدزلي السعر اللي تريد تبيع بي بالبوت:")
    bot.register_next_step_handler(msg, add_service_step3, temp_data)

def add_service_step3(message, temp_data):
    try:
        bot_price = float(message.text.strip())
        temp_data['bot_price'] = bot_price
        
        markup = InlineKeyboardMarkup()
        markup.add(
            InlineKeyboardButton("انستغرام 📸", callback_data=f"cat_instagram_{temp_data['api_id']}_{bot_price}"),
            InlineKeyboardButton("تيك توك 🎵", callback_data=f"cat_tiktok_{temp_data['api_id']}_{bot_price}")
        )
        bot.reply_to(message, "حلو! هسه اختار القسم الخاص بهاي الخدمة:", reply_markup=markup)
        
    except ValueError:
        bot.reply_to(message, "❌ السعر لازم يكون رقم! عيد الأمر من البداية بكتابة /add.")

# --- حفظ الخدمة بقاعدة البيانات ---
@bot.callback_query_handler(func=lambda call: call.data.startswith('cat_'))
def save_service_to_db(call):
    if call.from_user.id != ADMIN_ID:
        return
        
    data_parts = call.data.split('_')
    category = data_parts[1]
    api_id = int(data_parts[2])
    bot_price = float(data_parts[3])
    
    service_data = fetch_service_from_api(api_id)
    
    db_data = {
        "api_service_id": api_id,
        "name": service_data['name'],
        "bot_price": bot_price,
        "category": category
    }
    
    try:
        # الإرسال إلى جدول services في Supabase
        supabase.table("services").insert(db_data).execute()
        bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, 
                              text=f"✅ تمت إضافة الخدمة بنجاح لقسم {category} بسعر {bot_price}$")
    except Exception as e:
        bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, 
                              text=f"❌ صار خطأ بالحفظ بقاعدة البيانات، تأكد من إعدادات الجدول: {e}")

# --- إعدادات الويب هوك (Webhook) للاستضافة ---
@app.route(f'/{BOT_TOKEN}', methods=['POST'])
def webhook():
    if request.headers.get('content-type') == 'application/json':
        json_str = request.get_data().decode('UTF-8')
        update = telebot.types.Update.de_json(json_str)
        bot.process_new_updates([update])
        return '', 200
    return 'Forbidden', 403

@app.route('/')
def index():
    return "Hassany Bot is Running! 🚀"

if __name__ == '__main__':
    # لتشغيل السيرفر على الاستضافة
    app.run(host="0.0.0.0", port=int(os.environ.get('PORT', 5000)))
