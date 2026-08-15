import os
import requests
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from flask import Flask, request
from supabase import create_client, Client
from dotenv import load_dotenv
from datetime import datetime

# --- الإعدادات الأساسية ---
load_dotenv()
BOT_TOKEN = os.getenv('BOT_TOKEN')
API_KEY = os.getenv('API_KEY')
ADMIN_ID = int(os.getenv('ADMIN_ID', 0))
API_URL = "https://kd1s.com/api/v2"

supabase: Client = create_client(os.getenv('SUPABASE_URL'), os.getenv('SUPABASE_KEY'))
bot = telebot.TeleBot(BOT_TOKEN)
app = Flask(__name__)

# --- الرموز والأيقونات المتحركة ---
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

# --- دوال قاعدة البيانات ---
def register_user(user_id, name):
    try:
        user = supabase.table("users").select("*").eq("user_id", user_id).execute()
        if not user.data:
            supabase.table("users").insert({"user_id": user_id, "name": name, "balance": 0.0}).execute()
    except Exception as e:
        print(f"Error registering user: {e}")

def get_balance(user_id):
    try:
        res = supabase.table("users").select("balance").eq("user_id", user_id).execute()
        if res.data: return float(res.data[0]['balance'])
    except: pass
    return 0.0

def update_balance(user_id, amount, add=True):
    current = get_balance(user_id)
    new_bal = (current + amount) if add else (current - amount)
    supabase.table("users").update({"balance": new_bal}).eq("user_id", user_id).execute()
    return new_bal

def fetch_service_from_api(service_id):
    payload = {"key": API_KEY, "action": "services"}
    try:
        response = requests.post(API_URL, json=payload).json()
        for s in response:
            if str(s.get('service')) == str(service_id): return s
    except: pass
    return None

# --- واجهة الزبون الرئيسية ---
@bot.message_handler(commands=['start'])
def start_message(message):
    chat_id = message.chat.id
    register_user(chat_id, message.from_user.first_name)
    
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        ColoredButton(text="طلب جديد", callback_data="new_order", style="success", icon_custom_emoji_id="4972415571384599106"),
        ColoredButton(text="حسابي", callback_data="my_account", style="primary", icon_custom_emoji_id="5443036372325656561")
    )
    markup.add(
        ColoredButton(text="طلباتي", callback_data="my_orders", style="primary", icon_custom_emoji_id="5334961908392954329"),
        ColoredButton(text="الدعم الفني", url="https://t.me/hassanyIPA", style="default")
    )
    
    if chat_id == ADMIN_ID:
        markup.add(ColoredButton(text="لوحة التحكم (الأدمن) ⚙️", callback_data="admin_panel", style="danger"))

    text = f"مرحباً بك في بوت خدمات الرشق! {E_STAR}{E_FIRE}\n\nيمكنك من خلال البوت اختيار الخدمات التي تريدها بكل سهولة وتتبع طلباتك لحظة بلحظة.\n\nاختر من القائمة أدناه:"
    bot.send_message(chat_id, text, reply_markup=markup, parse_mode="HTML")

# --- لوحة تحكم الأدمن ---
def admin_panel_ui(chat_id, message_id=None):
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        ColoredButton(text="إضافة قسم", callback_data="admin_add_cat", style="success"),
        ColoredButton(text="إضافة خدمة", callback_data="admin_add_service", style="success")
    )
    markup.add(
        ColoredButton(text="الإحصائيات", callback_data="admin_stats", style="primary"),
        ColoredButton(text="شحن رصيد", callback_data="admin_add_balance", style="primary")
    )
    markup.add(ColoredButton(text="رجوع", callback_data="home", style="danger"))
    
    msg = "<b>لوحة التحكم الخاصة بالمدير</b> 👑\n\nاختر الإجراء المطلوب:"
    if message_id:
        bot.edit_message_text(msg, chat_id, message_id, reply_markup=markup, parse_mode="HTML")
    else:
        bot.send_message(chat_id, msg, reply_markup=markup, parse_mode="HTML")

# --- استجابات الأزرار (Callbacks) ---
@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):
    chat_id = call.message.chat.id
    mid = call.message.message_id
    data = call.data
    
    # 🏠 الرجوع للرئيسية
    if data == "home":
        bot.delete_message(chat_id, mid)
        start_message(call.message)
        
    # 👤 قسم حسابي
    elif data == "my_account":
        bal = get_balance(chat_id)
        orders = supabase.table("orders").select("id", count="exact").eq("user_id", chat_id).execute()
        count = orders.count if orders.count else 0
        
        markup = InlineKeyboardMarkup().add(ColoredButton(text="رجوع", callback_data="home", style="danger"))
        msg = f"{E_USER} <b>معلومات حسابك:</b>\n\n🆔 الأيدي: <code>{chat_id}</code>\n💰 الرصيد الحالي: <b>{bal}$</b>\n🛒 عدد الطلبات: <b>{count}</b>"
        bot.edit_message_text(msg, chat_id, mid, reply_markup=markup, parse_mode="HTML")
        
    # 🛒 قسم طلباتي
    elif data == "my_orders":
        res = supabase.table("orders").select("*").eq("user_id", chat_id).order("id", desc=True).limit(5).execute()
        markup = InlineKeyboardMarkup().add(ColoredButton(text="رجوع", callback_data="home", style="danger"))
        if not res.data:
            bot.edit_message_text("لا توجد طلبات سابقة بحسابك. ❌", chat_id, mid, reply_markup=markup)
            return
        
        msg = f"{E_CART} <b>أحدث 5 طلبات لك:</b>\n\n"
        for o in res.data:
            msg += f"🔹 خدمة: {o['service_name']}\n💵 السعر: {o['price']}$\n🔗 الرابط: {o['target_link']}\n📌 الحالة: {o['status']}\n〰️〰️〰️〰️\n"
        bot.edit_message_text(msg, chat_id, mid, reply_markup=markup, parse_mode="HTML")

    # 🚀 قسم طلب جديد (عرض الأقسام)
    elif data == "new_order":
        res = supabase.table("categories").select("*").execute()
        markup = InlineKeyboardMarkup(row_width=2)
        if res.data:
            for cat in res.data:
                markup.add(ColoredButton(text=cat['name'], callback_data=f"cat_{cat['name']}", style="primary"))
        markup.add(ColoredButton(text="رجوع", callback_data="home", style="danger"))
        bot.edit_message_text("اختر التطبيق (القسم) المطلوب:", chat_id, mid, reply_markup=markup)

    # 📂 عرض خدمات القسم المحدد
    elif data.startswith("cat_"):
        cat_name = data.split("cat_")[1]
        res = supabase.table("services").select("*").eq("category", cat_name).execute()
        markup = InlineKeyboardMarkup(row_width=1)
        if res.data:
            for s in res.data:
                markup.add(ColoredButton(text=f"{s['name']} | {s['bot_price']}$", callback_data=f"buy_{s['id']}", style="success"))
        markup.add(ColoredButton(text="رجوع", callback_data="new_order", style="danger"))
        bot.edit_message_text(f"الخدمات المتاحة لقسم <b>{cat_name}</b>:\nاختر الخدمة المطلوبة:", chat_id, mid, reply_markup=markup, parse_mode="HTML")

    # 💸 بدء عملية الشراء
    elif data.startswith("buy_"):
        service_id = int(data.split("buy_")[1])
        res = supabase.table("services").select("*").eq("id", service_id).execute()
        if not res.data:
            bot.answer_callback_query(call.id, "الخدمة غير متوفرة!", show_alert=True)
            return
        
        service = res.data[0]
        bal = get_balance(chat_id)
        if bal < service['bot_price']:
            bot.answer_callback_query(call.id, f"رصيدك غير كافٍ! تحتاج {service['bot_price']}$", show_alert=True)
            return
            
        msg = bot.edit_message_text(f"الخدمة: <b>{service['name']}</b>\nالسعر: <b>{service['bot_price']}$</b>\n\nأرسل الآن الرابط المراد الرشق له:", chat_id, mid, parse_mode="HTML")
        bot.register_next_step_handler(msg, process_order, service)

    # ⚙️ لوحة التحكم - إضافة قسم
    elif data == "admin_panel" and chat_id == ADMIN_ID:
        admin_panel_ui(chat_id, mid)
        
    elif data == "admin_add_cat" and chat_id == ADMIN_ID:
        msg = bot.edit_message_text("أرسل اسم القسم الجديد (مثلاً: انستغرام، تيك توك):", chat_id, mid)
        bot.register_next_step_handler(msg, add_category_step)

    # ⚙️ لوحة التحكم - إضافة خدمة
    elif data == "admin_add_service" and chat_id == ADMIN_ID:
        msg = bot.edit_message_text("أرسل رقم الخدمة (ID) من موقع الرشق:", chat_id, mid)
        bot.register_next_step_handler(msg, add_service_step1)

    # ⚙️ لوحة التحكم - شحن رصيد
    elif data == "admin_add_balance" and chat_id == ADMIN_ID:
        msg = bot.edit_message_text("أرسل أيدي (ID) المستخدم المراد شحنه:", chat_id, mid)
        bot.register_next_step_handler(msg, add_balance_step1)

    # ⚙️ لوحة التحكم - الإحصائيات
    elif data == "admin_stats" and chat_id == ADMIN_ID:
        u_res = supabase.table("users").select("id", count="exact").execute()
        o_res = supabase.table("orders").select("id", count="exact").execute()
        u_count = u_res.count if u_res.count else 0
        o_count = o_res.count if o_res.count else 0
        
        markup = InlineKeyboardMarkup().add(ColoredButton(text="رجوع", callback_data="admin_panel", style="danger"))
        bot.edit_message_text(f"📊 <b>إحصائيات البوت:</b>\n\n👥 عدد المستخدمين: {u_count}\n🛒 إجمالي الطلبات: {o_count}", chat_id, mid, reply_markup=markup, parse_mode="HTML")

# --- دوال عملية الشراء ---
def process_order(message, service):
    chat_id = message.chat.id
    target_link = message.text.strip()
    
    bal = get_balance(chat_id)
    if bal < service['bot_price']:
        bot.send_message(chat_id, "❌ فشل الطلب: رصيدك غير كافٍ.")
        return
        
    bot.send_message(chat_id, "جاري إرسال الطلب للموقع... ⏳")
    
    # إرسال الطلب للموقع (كمية 1000 كافتراضي، يمكن تطويرها لاحقاً لطلب الكمية من اليوزر)
    payload = {
        "key": API_KEY,
        "action": "add",
        "service": service['api_service_id'],
        "link": target_link,
        "quantity": 1000 
    }
    try:
        req = requests.post(API_URL, json=payload).json()
        if "error" in req:
            bot.send_message(chat_id, f"❌ خطأ من الموقع: {req['error']}")
            return
            
        # الخصم من الرصيد والحفظ بقاعدة البيانات
        update_balance(chat_id, service['bot_price'], add=False)
        supabase.table("orders").insert({
            "user_id": chat_id,
            "service_name": service['name'],
            "price": service['bot_price'],
            "target_link": target_link,
            "status": "قيد التنفيذ"
        }).execute()
        
        markup = InlineKeyboardMarkup().add(ColoredButton(text="رجوع للرئيسية", callback_data="home", style="primary"))
        bot.send_message(chat_id, f"{E_CHECK} <b>تم استلام طلبك بنجاح!</b>\n\nتم خصم {service['bot_price']}$ من رصيدك.\nيمكنك متابعة الحالة من قسم 'طلباتي'.", reply_markup=markup, parse_mode="HTML")
    except Exception as e:
        bot.send_message(chat_id, f"❌ حدث خطأ اثناء الاتصال بالـ API: {e}")

# --- دوال لوحة التحكم المساعدة ---
def add_category_step(message):
    name = message.text.strip()
    supabase.table("categories").insert({"name": name}).execute()
    markup = InlineKeyboardMarkup().add(ColoredButton(text="رجوع للوحة", callback_data="admin_panel", style="primary"))
    bot.send_message(message.chat.id, f"✅ تم إضافة القسم: {name}", reply_markup=markup)

def add_service_step1(message):
    service_id = message.text.strip()
    service_data = fetch_service_from_api(service_id)
    if not service_data:
        bot.send_message(message.chat.id, "❌ الخدمة مموجودة بالموقع.")
        return
    temp_data = {"api_id": service_id, "original_name": service_data['name'], "rate": service_data['rate']}
    msg = bot.send_message(message.chat.id, f"✅ الخدمة: {temp_data['original_name']}\nسعرها بالموقع: {temp_data['rate']}$\n\nدزلي السعر اللي تريد تبيع بي بالبوت:")
    bot.register_next_step_handler(msg, add_service_step2, temp_data)

def add_service_step2(message, temp_data):
    try:
        bot_price = float(message.text.strip())
        temp_data['bot_price'] = bot_price
        res = supabase.table("categories").select("*").execute()
        markup = InlineKeyboardMarkup(row_width=2)
        if res.data:
            for cat in res.data:
                markup.add(ColoredButton(text=cat['name'], callback_data=f"save_svc_{cat['name']}_{temp_data['api_id']}_{bot_price}"))
        bot.send_message(message.chat.id, "اختر القسم اللي تريد تضيف الخدمة بي:", reply_markup=markup)
    except:
        bot.send_message(message.chat.id, "❌ السعر لازم يكون رقم!")

@bot.callback_query_handler(func=lambda call: call.data.startswith('save_svc_'))
def save_svc_db(call):
    parts = call.data.split('_')
    cat_name = parts[2]
    api_id = parts[3]
    bot_price = parts[4]
    
    service_data = fetch_service_from_api(api_id)
    db_data = {"api_service_id": int(api_id), "name": service_data['name'], "bot_price": float(bot_price), "category": cat_name}
    supabase.table("services").insert(db_data).execute()
    
    markup = InlineKeyboardMarkup().add(ColoredButton(text="رجوع للوحة", callback_data="admin_panel", style="primary"))
    bot.edit_message_text(f"✅ تمت إضافة الخدمة بنجاح لقسم {cat_name}.", call.message.chat.id, call.message.message_id, reply_markup=markup)

def add_balance_step1(message):
    try:
        target_id = int(message.text.strip())
        msg = bot.send_message(message.chat.id, "أرسل المبلغ المراد إضافته (مثلاً 5.5):")
        bot.register_next_step_handler(msg, add_balance_step2, target_id)
    except:
        bot.send_message(message.chat.id, "❌ الأيدي لازم يكون أرقام فقط!")

def add_balance_step2(message, target_id):
    try:
        amount = float(message.text.strip())
        new_bal = update_balance(target_id, amount, add=True)
        bot.send_message(message.chat.id, f"✅ تم الشحن بنجاح.\nالرصيد الجديد لليوزر: {new_bal}$")
        try:
            bot.send_message(target_id, f"🎉 تم شحن رصيدك بمقدار {amount}$!\nرصيدك الحالي: {new_bal}$")
        except: pass
    except:
        bot.send_message(message.chat.id, "❌ المبلغ لازم يكون رقم!")

# --- الويب هوك الخاص بالاستضافة ---
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
    app.run(host="0.0.0.0", port=int(os.environ.get('PORT', 5000)))
