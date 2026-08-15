import os
import requests
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from flask import Flask, request
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv('BOT_TOKEN')
API_KEY = os.getenv('API_KEY')
ADMIN_ID = int(os.getenv('ADMIN_ID', 0))
API_URL = "https://kd1s.com/api/v2"

supabase: Client = create_client(os.getenv('SUPABASE_URL'), os.getenv('SUPABASE_KEY'))
bot = telebot.TeleBot(BOT_TOKEN)
app = Flask(__name__)

# --- الرموز المتحركة ---
E_ROCKET = '<tg-emoji emoji-id="5861568308116984245">🚀</tg-emoji>'
E_CHECK  = '<tg-emoji emoji-id="5197512496675571164">✅</tg-emoji>'
E_STAR   = '<tg-emoji emoji-id="5307699753805451797">🤩</tg-emoji>'
E_FIRE   = '<tg-emoji emoji-id="5210862586471424132">🔥</tg-emoji>'
E_CART   = '<tg-emoji emoji-id="5334961908392954329">🛒</tg-emoji>'
E_USER   = '<tg-emoji emoji-id="5443036372325656561">👤</tg-emoji>'

# --- كلاس الأزرار الملونة الشفافة ---
class ColoredButton(InlineKeyboardButton):
    def __init__(self, text, style=None, icon_custom_emoji_id=None, **kwargs):
        super().__init__(text, **kwargs)
        self.style = style
        self.icon_custom_emoji_id = icon_custom_emoji_id
        
    def to_dict(self):
        d = super().to_dict()
        if self.style: d['style'] = self.style
        if self.icon_custom_emoji_id: d['icon_custom_emoji_id'] = self.icon_custom_emoji_id
        return d

# --- واجهة المستخدم (الزبون) ---
@bot.message_handler(commands=['start'])
def start_message(message):
    chat_id = message.chat.id
    
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        ColoredButton(text="طلب جديد", callback_data="new_order", style="success", icon_custom_emoji_id="4972415571384599106"),
        ColoredButton(text="حسابي", callback_data="my_account", style="primary", icon_custom_emoji_id="5443036372325656561")
    )
    markup.add(
        ColoredButton(text="طلباتي", callback_data="my_orders", style="primary", icon_custom_emoji_id="5334961908392954329"),
        ColoredButton(text="الدعم الفني", url="https://t.me/hassanyIPA", style="default") # رابط قناتك او حسابك
    )
    
    if chat_id == ADMIN_ID:
        markup.add(ColoredButton(text="لوحة التحكم (الأدمن) ⚙️", callback_data="admin_panel", style="danger"))

    welcome_text = f"مرحباً بك في بوت خدمات الرشق! {E_STAR}{E_FIRE}\n\nيمكنك من خلال البوت اختيار الخدمات التي تريدها بكل سهولة وتتبع طلباتك لحظة بلحظة.\n\nاختر من القائمة أدناه:"
    bot.send_message(chat_id, welcome_text, reply_markup=markup, parse_mode="HTML")

# --- واجهة الأدمن (لوحة التحكم) ---
def admin_panel_ui(chat_id, message_id):
    markup = InlineKeyboardMarkup(row_width=2)
    
    markup.add(
        ColoredButton(text="إضافة تطبيق (قسم)", callback_data="add_category", style="success"),
        ColoredButton(text="إضافة خدمة", callback_data="add_service", style="success")
    )
    markup.add(
        ColoredButton(text="المشتركون والإحصائيات", callback_data="users_stats", style="primary"),
        ColoredButton(text="شحن رصيد لمستخدم", callback_data="add_balance", style="primary")
    )
    markup.add(ColoredButton(text="رجوع", callback_data="home", style="danger"))
    
    bot.edit_message_text("<b>لوحة التحكم الخاصة بالمدير</b> 👑\n\nاختر الإجراء المطلوب:", chat_id, message_id, reply_markup=markup, parse_mode="HTML")

# --- التحكم بالاستجابات (Callbacks) ---
@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):
    chat_id = call.message.chat.id
    mid = call.message.message_id
    data = call.data
    
    if data == "home":
        bot.delete_message(chat_id, mid)
        start_message(call.message)
    
    elif data == "admin_panel" and chat_id == ADMIN_ID:
        admin_panel_ui(chat_id, mid)
        
    elif data == "my_account":
        # سيتم برمجتها بعد تحديث قاعدة البيانات
        bot.answer_callback_query(call.id, "قريباً: عرض الرصيد والطلبات!")
        
    else:
        bot.answer_callback_query(call.id, "جاري العمل على هذا القسم ⏳")

# --- الويب هوك للاستضافة ---
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
    return "Hassany Bot V2 is Running! 🚀"

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=int(os.environ.get('PORT', 5000)))
