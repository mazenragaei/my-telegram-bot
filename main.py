import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, LabeledPrice
import sqlite3
from flask import Flask
from threading import Thread
import time

# ================= الإعدادات الأساسية ================= #
BOT_TOKEN = "8633987035:AAF4wt6L4aAlyNe561nfCLPGbxTA7Z5JShs"
ADMIN_ID = 123456789  # ضع الـ ID الخاص بك هنا
CHANNEL_USERNAME = "@AlphaShadowMa" # المعرف بدون مسافات، مثال: @LaraLeather
CHANNEL_URL = "https://t.me/AlphaShadowMa"

STAR_TO_BALANCE_RATE = 1.0 
bot = telebot.TeleBot(BOT_TOKEN, parse_mode="HTML")

# ================= سيرفر Flask للعمل 24/7 ================= #
app = Flask(__name__)
@app.route('/')
def home(): return "🚀 Bot is Active and Running 24/7!"
def run_flask(): app.run(host="0.0.0.0", port=8080)

# ================= إعداد قاعدة البيانات ================= #
def init_db():
    conn = sqlite3.connect('store.db', check_same_thread=False)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, balance REAL DEFAULT 0)''')
    c.execute('''CREATE TABLE IF NOT EXISTS products (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, desc TEXT, price REAL, stock INTEGER, delivery_type TEXT, auto_data TEXT)''')
    conn.commit()
    conn.close()
init_db()

def get_user_balance(user_id):
    conn = sqlite3.connect('store.db')
    c = conn.cursor()
    c.execute("SELECT balance FROM users WHERE user_id=?", (user_id,))
    res = c.fetchone()
    if not res:
        c.execute("INSERT INTO users (user_id, balance) VALUES (?, ?)", (user_id, 0))
        conn.commit()
        return 0
    conn.close()
    return res[0]

# ================= القائمة الرئيسية ================= #
@bot.message_handler(commands=['start'])
def start_msg(message):
    user_id = message.from_user.id
    balance = get_user_balance(user_id)
    
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton("🛒 تصفح المتجر", callback_data="store"),
        InlineKeyboardButton("💳 شحن الرصيد", callback_data="wallet"),
        InlineKeyboardButton("💬 الدعم الفني", url="t.me/YourUsername"),
        InlineKeyboardButton("🌟 قناتنا", url=CHANNEL_URL)
    )
    if user_id == ADMIN_ID:
        markup.add(InlineKeyboardButton("🛠 لوحة تحكم الإدارة 🛠", callback_data="admin_panel"))

    text = f"👋 <b>مرحباً بك في متجرنا الاحترافي!</b>\n\n💰 رصيدك الحالي: <b>{balance}</b>\n\n👇 <i>اختر من القائمة أدناه للبدء:</i>"
    bot.send_message(user_id, text, reply_markup=markup)

# ================= نظام التوجيه والأزرار ================= #
@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    user_id = call.from_user.id
    
    # -------- المحفظة والشحن --------
    if call.data == "wallet":
        markup = InlineKeyboardMarkup(row_width=1)
        markup.add(
            InlineKeyboardButton("⭐️ شحن تلقائي بنجوم تيليجرام", callback_data="buy_stars"),
            InlineKeyboardButton("📱 فودافون كاش / انستا باي", callback_data="pay_manual"),
            InlineKeyboardButton("🔙 رجوع", callback_data="back_main")
        )
        bot.edit_message_text("<b>اختر وسيلة الشحن المناسبة لك:</b>", chat_id=user_id, message_id=call.message.message_id, reply_markup=markup)

    elif call.data == "buy_stars":
        markup = InlineKeyboardMarkup(row_width=2)
        markup.add(
            InlineKeyboardButton("⭐️ 50 نجمة", callback_data="invoice_50"),
            InlineKeyboardButton("⭐️ 100 نجمة", callback_data="invoice_100"),
            InlineKeyboardButton("🔙 رجوع", callback_data="wallet")
        )
        bot.edit_message_text("اختر الباقة:", chat_id=user_id, message_id=call.message.message_id, reply_markup=markup)

    elif call.data.startswith("invoice_"):
        amount = int(call.data.split("_")[1])
        prices = [LabeledPrice(label=f"شحن {amount} نجمة", amount=amount)]
        bot.send_invoice(call.message.chat.id, title=f"باقة {amount} نجمة", description=f"شحن ما يعادل {amount * STAR_TO_BALANCE_RATE} رصيد.", invoice_payload=f"stars_{amount}", provider_token="", currency="XTR", prices=prices)

    elif call.data == "pay_manual":
        bot.send_message(user_id, "📱 <b>للشحن اليدوي:</b>\n\nفودافون كاش: 010XXXXXX\nانستا باي: user@instapay\n\nيرجى تحويل المبلغ ثم إرسال سكرين شوت هنا للإدارة.")

    # -------- عرض المتجر --------
    elif call.data == "store":
        conn = sqlite3.connect('store.db')
        c = conn.cursor()
        c.execute("SELECT id, name, price, stock FROM products WHERE stock > 0")
        products = c.fetchall()
        conn.close()

        if not products:
            bot.edit_message_text("🛒 <b>المتجر فارغ حالياً أو نفذت الكميات.</b>", chat_id=user_id, message_id=call.message.message_id, reply_markup=InlineKeyboardMarkup().add(InlineKeyboardButton("🔙 رجوع", callback_data="back_main")))
            return
        
        markup = InlineKeyboardMarkup(row_width=1)
        for p in products:
            markup.add(InlineKeyboardButton(f"🛍 {p[1]} | السعر: {p[2]} | متبقي: {p[3]}", callback_data=f"buy_{p[0]}"))
        markup.add(InlineKeyboardButton("🔙 رجوع", callback_data="back_main"))
        bot.edit_message_text("🛒 <b>المنتجات المتوفرة:</b>", chat_id=user_id, message_id=call.message.message_id, reply_markup=markup)

    # -------- لوحة الإدارة (التطوير الأقصى) --------
    elif call.data == "admin_panel" and user_id == ADMIN_ID:
        markup = InlineKeyboardMarkup(row_width=2)
        markup.add(
            InlineKeyboardButton("➕ إضافة منتج", callback_data="admin_add_prod"),
            InlineKeyboardButton("🗑 حذف منتج", callback_data="admin_del_prod"),
            InlineKeyboardButton("✏️ تعديل سعر/كمية", callback_data="admin_edit_prod"),
            InlineKeyboardButton("📢 إرسال رسالة للكل", callback_data="admin_broadcast"),
            InlineKeyboardButton("🔙 رجوع", callback_data="back_main")
        )
        bot.edit_message_text("<b>🛠 لوحة تحكم الإدارة:</b>", chat_id=user_id, message_id=call.message.message_id, reply_markup=markup)

    # اختيار المنتج للحذف أو التعديل
    elif call.data in ["admin_del_prod", "admin_edit_prod"] and user_id == ADMIN_ID:
        action = "del" if call.data == "admin_del_prod" else "edit"
        conn = sqlite3.connect('store.db')
        c = conn.cursor()
        c.execute("SELECT id, name FROM products")
        products = c.fetchall()
        conn.close()
        
        if not products:
            bot.answer_callback_query(call.id, "لا توجد منتجات!", show_alert=True)
            return
            
        markup = InlineKeyboardMarkup(row_width=1)
        for p in products:
            markup.add(InlineKeyboardButton(p[1], callback_data=f"{action}prod_{p[0]}"))
        markup.add(InlineKeyboardButton("🔙 رجوع", callback_data="admin_panel"))
        bot.edit_message_text("اختر المنتج المطلوب:", chat_id=user_id, message_id=call.message.message_id, reply_markup=markup)

    # حذف المنتج
    elif call.data.startswith("delprod_") and user_id == ADMIN_ID:
        prod_id = call.data.split("_")[1]
        conn = sqlite3.connect('store.db')
        c = conn.cursor()
        c.execute("DELETE FROM products WHERE id=?", (prod_id,))
        conn.commit()
        conn.close()
        bot.answer_callback_query(call.id, "✅ تم حذف المنتج!", show_alert=True)
        bot.delete_message(user_id, call.message.message_id)

    # خيارات التعديل (سعر أم كمية)
    elif call.data.startswith("editprod_") and user_id == ADMIN_ID:
        prod_id = call.data.split("_")[1]
        markup = InlineKeyboardMarkup(row_width=2)
        markup.add(
            InlineKeyboardButton("💰 تعديل السعر", callback_data=f"setprice_{prod_id}"),
            InlineKeyboardButton("📦 تعديل الكمية", callback_data=f"setstock_{prod_id}"),
            InlineKeyboardButton("🔙 رجوع", callback_data="admin_panel")
        )
        bot.edit_message_text("ماذا تريد أن تعدل في هذا المنتج؟", chat_id=user_id, message_id=call.message.message_id, reply_markup=markup)

    # استقبال السعر أو الكمية الجديدة
    elif call.data.startswith("setprice_") and user_id == ADMIN_ID:
        prod_id = call.data.split("_")[1]
        msg = bot.send_message(user_id, "أرسل السعر الجديد (أرقام فقط):")
        bot.register_next_step_handler(msg, update_product_db, prod_id, "price")

    elif call.data.startswith("setstock_") and user_id == ADMIN_ID:
        prod_id = call.data.split("_")[1]
        msg = bot.send_message(user_id, "أرسل الكمية الجديدة (أرقام فقط):")
        bot.register_next_step_handler(msg, update_product_db, prod_id, "stock")

    # إضافة منتج (الخطوة الأولى)
    elif call.data == "admin_add_prod" and user_id == ADMIN_ID:
        msg = bot.send_message(user_id, "أرسل اسم المنتج الجديد:")
        bot.register_next_step_handler(msg, add_step1)

    elif call.data == "back_main":
        bot.delete_message(user_id, call.message.message_id)
        start_msg(call.message)

# ================= دوال إضافة منتج ================= #
temp_prod = {}
def add_step1(msg):
    temp_prod['name'] = msg.text
    bot.register_next_step_handler(bot.send_message(msg.chat.id, "أرسل الوصف:"), add_step2)
def add_step2(msg):
    temp_prod['desc'] = msg.text
    bot.register_next_step_handler(bot.send_message(msg.chat.id, "أرسل السعر (أرقام):"), add_step3)
def add_step3(msg):
    temp_prod['price'] = float(msg.text)
    bot.register_next_step_handler(bot.send_message(msg.chat.id, "أرسل الكمية (أرقام):"), add_step4)
def add_step4(msg):
    temp_prod['stock'] = int(msg.text)
    temp_prod['type'] = 'manual' # يمكن تطويرها لـ auto إذا أردت
    temp_prod['data'] = 'تسليم يدوي'
    
    conn = sqlite3.connect('store.db')
    c = conn.cursor()
    c.execute("INSERT INTO products (name, desc, price, stock, delivery_type, auto_data) VALUES (?, ?, ?, ?, ?, ?)",
              (temp_prod['name'], temp_prod['desc'], temp_prod['price'], temp_prod['stock'], temp_prod['type'], temp_prod['data']))
    conn.commit()
    conn.close()
    bot.send_message(ADMIN_ID, "✅ تم إضافة المنتج بنجاح!")

# ================= دوال تحديث المنتجات ================= #
def update_product_db(message, prod_id, field):
    try:
        new_value = float(message.text) if field == "price" else int(message.text)
        conn = sqlite3.connect('store.db')
        c = conn.cursor()
        c.execute(f"UPDATE products SET {field}=? WHERE id=?", (new_value, prod_id))
        conn.commit()
        conn.close()
        bot.send_message(ADMIN_ID, f"✅ تم تحديث {'السعر 💰' if field == 'price' else 'الكمية 📦'} بنجاح!")
    except:
        bot.send_message(ADMIN_ID, "❌ حدث خطأ، تأكد من إرسال أرقام فقط.")

# ================= معالجة الدفع بنجوم تيليجرام ================= #
@bot.pre_checkout_query_handler(func=lambda query: True)
def checkout(pre_checkout_query):
    bot.answer_pre_checkout_query(pre_checkout_query.id, ok=True)

@bot.message_handler(content_types=['successful_payment'])
def got_payment(message):
    user_id = message.from_user.id
    stars_paid = message.successful_payment.total_amount
    added_balance = stars_paid * STAR_TO_BALANCE_RATE
    
    conn = sqlite3.connect('store.db')
    c = conn.cursor()
    c.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (added_balance, user_id))
    conn.commit()
    conn.close()
    
    bot.send_message(user_id, f"✅ <b>تم الشحن بنجاح!</b> تم إضافة <b>{added_balance}</b> إلى رصيدك.")

# ================= التشغيل ================= #
if __name__ == "__main__":
    Thread(target=run_flask).start()
    bot.infinity_polling()