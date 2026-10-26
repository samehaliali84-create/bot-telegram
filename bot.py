from datetime import datetime
import random
import sqlite3
import string
import telebot
from telebot import types

# التوكن الجديد الخاص بك
TOKEN = "8961232938:AAG2mwNw0t-e5ddlLxygm_36Os0j5v1-zQY"
bot = telebot.TeleBot(TOKEN)

# روابط الاشتراك الإلزامي الثلاثة
MANDATORY_URL_1 = "https://t.me/Texas_4Win_Cash"
MANDATORY_URL_2 = "https://t.me/Texas_4Win_Cash_Gifts_bot?start=ref_8802213264"
MANDATORY_URL_3 = "https://t.me/khbonse89"

# إضافة زر الأوامر (/start) ليظهر تلقائياً في قائمة (Menu) الخاصة بالبوت
try:
  bot.set_my_commands([
      telebot.types.BotCommand("start", "تشغيل البوت والقائمة الرئيسية 🚀")
  ])
except Exception as e:
  print(f"Error setting commands: {e}")

# قواميس لحفظ حالات المستخدمين والبيانات المؤقتة
user_states = {}
user_temp_data = {}


# إعداد قاعدة البيانات المحلية SQLite
def init_db():
  conn = sqlite3.connect("bot_database.db", check_same_thread=False)
  cursor = conn.cursor()
  cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            phone TEXT,
            balance REAL DEFAULT 0,
            frozen_balance REAL DEFAULT 0,
            referred_by INTEGER,
            weekly_claimed INTEGER DEFAULT 0,
            sub_verified INTEGER DEFAULT 0,
            last_daily_date TEXT
        )
    """)
  cursor.execute("""
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    """)
  cursor.execute("""
        CREATE TABLE IF NOT EXISTS promo_codes (
            code TEXT PRIMARY KEY,
            amount REAL,
            max_uses INTEGER,
            used_count INTEGER DEFAULT 0
        )
    """)
  cursor.execute("""
        CREATE TABLE IF NOT EXISTS redeemed_codes (
            user_id INTEGER,
            code TEXT,
            PRIMARY KEY (user_id, code)
        )
    """)
  try:
    cursor.execute("ALTER TABLE users ADD COLUMN last_daily_date TEXT")
  except:
    pass
  conn.commit()
  conn.close()


init_db()


def get_db():
  conn = sqlite3.connect("bot_database.db", check_same_thread=False)
  return conn, conn.cursor()


# دالة لجلب آيدي المدير المحفوظ تلقائياً
def get_admin_id():
  conn, cursor = get_db()
  cursor.execute("SELECT value FROM settings WHERE key = 'admin_id'")
  res = cursor.fetchone()
  conn.close()
  return int(res[0]) if res else None


# أمر لتعيين نفسك كمدير للبوت من خلال كتابة /setadmin في المحادثة
@bot.message_handler(commands=["setadmin"])
def set_admin(message):
  user_id = message.from_user.id
  conn, cursor = get_db()
  cursor.execute(
      "REPLACE INTO settings (key, value) VALUES ('admin_id', ?)",
      (str(user_id),),
  )
  conn.commit()
  conn.close()
  bot.send_message(
      message.chat.id,
      f"✅ **تم تعيينك كمدير للبوت بنجاح!**\n\n"
      f"🆔 آيدي الخاص بك: `{user_id}`\n"
      f"ستظهر لك الآن لوحة التحكم في القائمة الرئيسية.",
      parse_mode="Markdown",
  )
  show_main_menu(message.chat.id)


# أمر البدء /start مع حفظ صاحب الإحالة والتحقق من رقم الهاتف والاشتراك
@bot.message_handler(commands=["start"])
def send_welcome(message):
  user_id = message.from_user.id
  args = message.text.split()

  conn, cursor = get_db()
  cursor.execute(
      "SELECT phone, sub_verified FROM users WHERE user_id = ?", (user_id,)
  )
  user = cursor.fetchone()

  referrer_id = None
  if len(args) > 1 and args[1].isdigit():
    referrer_id = int(args[1])
    if referrer_id == user_id:
      referrer_id = None

  if not user:
    cursor.execute(
        "INSERT INTO users (user_id, referred_by) VALUES (?, ?)",
        (user_id, referrer_id),
    )
    conn.commit()

  conn.close()

  if user and user[0]:
    if user[1] == 1:
      show_main_menu(message.chat.id)
    else:
      send_subscription_prompt(message.chat.id)
  else:
    markup = types.ReplyKeyboardMarkup(
        resize_keyboard=True, one_time_keyboard=True
    )
    markup.add(types.KeyboardButton("📱 مشاركة رقم الهاتف", request_contact=True))
    bot.send_message(
        message.chat.id,
        "مرحباً بك! لاستخدام البوت، يجب مشاركة رقم هاتفك أولاً (التحقق حصراً"
        " لأرقام سوريا +963 أو لبنان +961):",
        reply_markup=markup,
    )


# استقبال رقم الهاتف والتحقق منه وإظهار روابط الاشتراك الإلزامي
@bot.message_handler(content_types=["contact"])
def handle_contact(message):
  if message.contact is not None:
    user_id = message.from_user.id
    phone = message.contact.phone_number
    cleaned_phone = phone.replace("+", "")

    if cleaned_phone.startswith("963") or cleaned_phone.startswith("961"):
      conn, cursor = get_db()
      cursor.execute(
          "UPDATE users SET phone = ? WHERE user_id = ?", (phone, user_id)
      )
      conn.commit()
      conn.close()

      bot.send_message(
          message.chat.id,
          "✅ تم التحقق من رقم هاتفك بنجاح!",
          reply_markup=types.ReplyKeyboardRemove(),
      )
      send_subscription_prompt(message.chat.id)
    else:
      markup = types.ReplyKeyboardMarkup(
          resize_keyboard=True, one_time_keyboard=True
      )
      markup.add(
          types.KeyboardButton("📱 مشاركة رقم الهاتف", request_contact=True)
      )
      bot.send_message(
          message.chat.id,
          "❌ عذراً، الرقم غير مدعوم. البوت مخصص لأرقام سوريا (+963) أو لبنان"
          " (+961) فقط. يرجى المحاولة مرة أخرى:",
          reply_markup=markup,
      )


# إرسال روابط الاشتراك الإلزامي الثلاثة
def send_subscription_prompt(chat_id):
  markup = types.InlineKeyboardMarkup()
  markup.add(types.InlineKeyboardButton("🔗 الرابط الأول", url=MANDATORY_URL_1))
  markup.add(
      types.InlineKeyboardButton("🔗 الرابط الثاني", url=MANDATORY_URL_2)
  )
  markup.add(
      types.InlineKeyboardButton("🔗 الرابط الثالث", url=MANDATORY_URL_3)
  )
  markup.add(
      types.InlineKeyboardButton(
          "✅ تحقق من الاشتراك", callback_data="check_sub"
      )
  )
  bot.send_message(
      chat_id,
      "⚠️ يرجى الاشتراك في الروابط الإلزامية أدناه ثم اضغط على زر التحقق للمتابعة:",
      reply_markup=markup,
  )


# قبول التحقق فوراً عند الضغط على زر "تحقق من الاشتراك"
@bot.callback_query_handler(func=lambda call: call.data == "check_sub")
def verify_sub(call):
  user_id = call.from_user.id

  conn, cursor = get_db()
  cursor.execute(
      "SELECT referred_by, sub_verified FROM users WHERE user_id = ?",
      (user_id,),
  )
  res = cursor.fetchone()

  if res and res[1] == 0:
    cursor.execute(
        "UPDATE users SET sub_verified = 1 WHERE user_id = ?", (user_id,)
    )
    conn.commit()

    ref_id = res[0]
    if ref_id:
      cursor.execute(
          "UPDATE users SET frozen_balance = frozen_balance + 500 WHERE"
          " user_id = ?",
          (ref_id,),
      )
      conn.commit()
      try:
        bot.send_message(
            ref_id,
            "🎉 انضم مستخدم جديد عبر رابط الإحالة الخاص بك وتم إضافة 500 ليرة إلى"
            " رصيدك المجمد!",
        )
      except:
        pass

  conn.close()
  bot.answer_callback_query(call.id, "✅ تم التحقق بنجاح!")
  try:
    bot.delete_message(call.message.chat.id, call.message.message_id)
  except:
    pass

  bot.send_message(call.message.chat.id, "تم التحقق بنجاح وتفعيل حسابك!")
  show_main_menu(call.message.chat.id)


# القائمة الرئيسية
def show_main_menu(chat_id):
  admin_id = get_admin_id()
  markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
  markup.add(
      types.KeyboardButton("🎁 الهدية اليومية"),
      types.KeyboardButton("⭐ الهدية الاسبوعية"),
      types.KeyboardButton("💰 رصيدي"),
      types.KeyboardButton("🎁 شحن كود هدية"),
      types.KeyboardButton("🔗 اضافة احالات"),
      types.KeyboardButton("📞 تواصل مع الدعم"),
      types.KeyboardButton("💸 سحب رصيدي"),
  )
  if admin_id and chat_id == admin_id:
    markup.add(types.KeyboardButton("👑 لوحة التحكم"))
  bot.send_message(chat_id, "مرحباً بك في القائمة الرئيسية:", reply_markup=markup)


# التعامل مع الوسائط (الصور المرفقة لطلبات السحب أو الإذاعة)
@bot.message_handler(
    content_types=["photo", "video", "document", "audio", "voice"]
)
def handle_media(message):
  user_id = message.from_user.id
  state = user_states.get(user_id)
  admin_id = get_admin_id()

  # 1. حالة الإذاعة الجماعية
  if state == "waiting_broadcast" and admin_id and user_id == admin_id:
    conn, cursor = get_db()
    cursor.execute("SELECT user_id FROM users")
    users = cursor.fetchall()
    conn.close()

    success = 0
    failed = 0
    for u in users:
      uid = u[0]
      try:
        bot.copy_message(
            chat_id=uid,
            from_chat_id=message.chat.id,
            message_id=message.message_id,
        )
        success += 1
      except:
        failed += 1

    bot.send_message(
        message.chat.id,
        f"✅ تم إرسال الرسالة الجماعية بنجاح!\n• وصل إلى: {success}"
        f" مستخدم\n• فشل الإرسال إلى: {failed} مستخدم",
    )
    user_states.pop(user_id, None)
    return

  # 2. استقبال صورة الرصيد لتأكيد السحب (لكلتا الطريقتين)
  if state == "waiting_withdrawal_photo":
    data = user_temp_data.get(user_id, {})
    wallet = data.get("wallet", "غير معروف")
    amount = data.get("amount", 0)
    method = data.get("method", "غير معروف")
    photo_id = message.photo[-1].file_id if message.photo else None

    if not photo_id:
      bot.send_message(message.chat.id, "⚠️ يرجى إرسال صورة لرصيدك بالبوت:")
      return

    # خصم الرصيد فوراً عند تأكيد الطلب وإرساله للإدارة
    conn, cursor = get_db()
    cursor.execute(
        "UPDATE users SET balance = balance - ? WHERE user_id = ?",
        (amount, user_id),
    )
    conn.commit()
    conn.close()

    if admin_id:
      try:
        markup_admin = types.InlineKeyboardMarkup(row_width=2)
        markup_admin.add(
            types.InlineKeyboardButton(
                "✅ قبول", callback_data=f"wd_acc_{user_id}_{int(amount)}"
            ),
            types.InlineKeyboardButton(
                "❌ رفض", callback_data=f"wd_rej_{user_id}_{int(amount)}"
            ),
        )
        bot.send_photo(
            admin_id,
            photo_id,
            caption=f"💸 **طلب سحب جديد ({method})**\n\n"
            f"👤 آيدي المستخدم: `{user_id}`\n"
            f"💰 المبلغ: `{amount} ل.س`\n"
            f"📱 رقم المحفظة/الحساب: `{wallet}`",
            reply_markup=markup_admin,
            parse_mode="Markdown",
        )
      except Exception as e:
        print(f"Error sending withdrawal to admin: {e}")

    bot.send_message(
        message.chat.id, "تم ارسال الطلب للمراجعة وسيتم التحقق قريبآ شكرا لصبرك"
    )

    user_states.pop(user_id, None)
    user_temp_data.pop(user_id, None)
    return


# التعامل مع الرسائل النصية
@bot.message_handler(func=lambda message: True, content_types=["text"])
def handle_text(message):
  text = message.text
  user_id = message.from_user.id
  state = user_states.get(user_id)
  admin_id = get_admin_id()

  if text == "👑 لوحة التحكم" and admin_id and user_id == admin_id:
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton(
            "➕ إنشاء كود هدية", callback_data="admin_create_code"
        ),
        types.InlineKeyboardButton(
            "📢 رسالة جماعية", callback_data="admin_broadcast"
        ),
        types.InlineKeyboardButton(
            "📊 إحصائيات البوت", callback_data="admin_stats"
        ),
    )
    bot.send_message(
        message.chat.id,
        "👑 **لوحة تحكم المشرف الأساسية:**",
        reply_markup=markup,
        parse_mode="Markdown",
    )
    return

  if state == "waiting_code_details" and admin_id and user_id == admin_id:
    parts = text.split()
    if (
        len(parts) != 2
        or not parts[0].isdigit()
        or not parts[1].isdigit()
    ):
      bot.send_message(
          message.chat.id,
          "⚠️ صيغة غير صحيحة. أرسل المبلغ وعدد المستخدمين هكذا:\n`المبلغ"
          " عدد_المستخدمين`\nمثال: `5000 20`",
          parse_mode="Markdown",
      )
      return

    amount = float(parts[0])
    max_uses = int(parts[1])
    code = "".join(
        random.choices(string.ascii_uppercase + string.digits, k=8)
    )

    conn, cursor = get_db()
    cursor.execute(
        "INSERT INTO promo_codes (code, amount, max_uses, used_count) VALUES"
        " (?, ?, ?, 0)",
        (code, amount, max_uses),
    )
    conn.commit()
    conn.close()

    bot.send_message(
        message.chat.id,
        f"✅ **تم إنشاء كود الهدية بنجاح!**\n\n"
        f"🎁 الكود: `{code}`\n"
        f"💰 القيمة: `{amount} ل.س`\n"
        f"👥 الحد الأقصى للاستخدام: `{max_uses}`",
        parse_mode="Markdown",
    )
    user_states.pop(user_id, None)
    return

  if state == "waiting_broadcast" and admin_id and user_id == admin_id:
    conn, cursor = get_db()
    cursor.execute("SELECT user_id FROM users")
    users = cursor.fetchall()
    conn.close()

    success = 0
    failed = 0
    for u in users:
      uid = u[0]
      try:
        bot.send_message(uid, text, parse_mode="Markdown")
        success += 1
      except:
        failed += 1

    bot.send_message(
        message.chat.id,
        f"✅ تم إرسال الرسالة الجماعية بنجاح!\n• وصل إلى: {success}"
        f" مستخدم\n• فشل الإرسال إلى: {failed} مستخدم",
    )
    user_states.pop(user_id, None)
    return

  if state == "waiting_redeem_code":
    code_text = text.strip().upper()
    conn, cursor = get_db()
    cursor.execute(
        "SELECT amount, max_uses, used_count FROM promo_codes WHERE code = ?",
        (code_text,),
    )
    promo = cursor.fetchone()

    if not promo:
      bot.send_message(message.chat.id, "❌ الكود غير صحيح أو انتهى.")
      conn.close()
      user_states.pop(user_id, None)
      return

    amount, max_uses, used_count = promo

    cursor.execute(
        "SELECT * FROM redeemed_codes WHERE user_id = ? AND code = ?",
        (user_id, code_text),
    )
    redeemed = cursor.fetchone()

    if redeemed:
      bot.send_message(message.chat.id, "❌ لقد قمت باستخدام هذا الكود مسبقاً!")
      conn.close()
      user_states.pop(user_id, None)
      return

    if used_count >= max_uses:
      bot.send_message(
          message.chat.id,
          "❌ عذراً، لقد وصل هذا الكود إلى الحد الأقصى للاستخدام!",
      )
      conn.close()
      user_states.pop(user_id, None)
      return

    cursor.execute(
        "UPDATE users SET balance = balance + ? WHERE user_id = ?",
        (amount, user_id),
    )
    cursor.execute(
        "UPDATE promo_codes SET used_count = used_count + 1 WHERE code = ?",
        (code_text,),
    )
    cursor.execute(
        "INSERT INTO redeemed_codes (user_id, code) VALUES (?, ?)",
        (user_id, code_text),
    )
    conn.commit()
    conn.close()

    bot.send_message(
        message.chat.id,
        f"🎉 مبروك! تم شحن الكود بنجاح وإضافة `{amount} ل.س` إلى رصيدك.",
        parse_mode="Markdown",
    )
    user_states.pop(user_id, None)
    return

  if state == "waiting_support":
    if admin_id:
      try:
        bot.send_message(
            admin_id,
            f"📞 **رسالة دعم جديدة من المستخدم:**\n\n🆔 الآيدي:"
            f" `{user_id}`\n💬 النص:\n{text}",
            parse_mode="Markdown",
        )
      except Exception as e:
        print(f"Error sending support to admin: {e}")

    bot.send_message(message.chat.id, "تم ارسال التفاصيل للإدارة بإنتظار المراجعة")
    user_states.pop(user_id, None)
    return

  elif state == "waiting_withdraw_amount":
    if not text.isdigit():
      bot.send_message(
          message.chat.id, "⚠️ يرجى إدخال رقم صحيح للمبلغ المراد سحبه:"
      )
      return

    amount = float(text)
    if amount < 10000:
      bot.send_message(
          message.chat.id,
          "⚠️ الحد الأدنى للسحب هو 10,000 ل.س. يرجى إدخال مبلغ 10000 أو أكثر:",
      )
      return

    conn, cursor = get_db()
    cursor.execute("SELECT balance FROM users WHERE user_id = ?", (user_id,))
    res = cursor.fetchone()
    conn.close()

    if not res or res[0] < amount:
      bot.send_message(
          message.chat.id,
          "❌ رصيدك المتاح لا يكفي لهذا المبلغ. يمكنك جمع المزيد من الرصيد أو"
          " إدخال مبلغ أقل.",
      )
      user_states.pop(user_id, None)
      user_temp_data.pop(user_id, None)
      return

    user_temp_data[user_id]["amount"] = amount
    method = user_temp_data[user_id].get("method")

    # الانتقال لطلب رقم المحفظة/الحساب لأي طريقة سحب اختيارها المستخدم
    user_states[user_id] = "waiting_wallet_number"
    bot.send_message(
        message.chat.id,
        f"📱 ممتاز ({method}). الآن أدخل رقم المحفظة أو الحساب الخاص بك:",
    )
    return

  elif state == "waiting_wallet_number":
    user_temp_data[user_id]["wallet"] = text
    user_states[user_id] = "waiting_withdrawal_photo"
    bot.send_message(
        message.chat.id,
        "📸 ممتاز. الآن أرسل صورة لرصيدك بالبوت لتأكيد الطلب:",
    )
    return

  # الأزرار الرئيسية
  if text == "🎁 الهدية اليومية":
    today = datetime.now().strftime("%Y-%m-%d")
    conn, cursor = get_db()
    cursor.execute("SELECT last_daily_date FROM users WHERE user_id = ?", (user_id,))
    res = cursor.fetchone()
    if res and res[0] == today:
      bot.send_message(
          message.chat.id,
          "⏳ لقد استلمت الهدية اليومية مسبقاً اليوم، عد غداً لاستلامها مجدداً.",
      )
    else:
      cursor.execute(
          "UPDATE users SET balance = balance + 500, last_daily_date = ? WHERE"
          " user_id = ?",
          (today, user_id),
      )
      conn.commit()
      bot.send_message(message.chat.id, "تم اضافة 500 ليرة الى رصيدك")
    conn.close()

  elif text == "⭐ الهدية الاسبوعية":
    conn, cursor = get_db()
    cursor.execute(
        "SELECT weekly_claimed FROM users WHERE user_id = ?", (user_id,)
    )
    res = cursor.fetchone()
    if res and res[0] == 1:
      bot.send_message(
          message.chat.id, "⏳ لقد استلمت الهدية الأسبوعية مسبقاً لهذا الأسبوع."
      )
    else:
      cursor.execute(
          "UPDATE users SET balance = balance + 2000, weekly_claimed = 1 WHERE"
          " user_id = ?",
          (user_id,),
      )
      conn.commit()
      bot.send_message(message.chat.id, "تم اضافة 2000 ليرة الى رصيدك")
    conn.close()

  elif text == "💰 رصيدي":
    conn, cursor = get_db()
    cursor.execute(
        "SELECT balance, frozen_balance FROM users WHERE user_id = ?",
        (user_id,),
    )
    res = cursor.fetchone()
    conn.close()
    if res:
      bal, frozen = res
      bot.send_message(
          message.chat.id,
          f"💰 **معلومات حسابك:**\n\n"
          f"🆔 آيدي حسابك: `{user_id}`\n"
          f"• الرصيد المتاح: {bal} ل.س\n"
          f"• الرصيد المجمد: {frozen} ل.س",
          parse_mode="Markdown",
      )

  elif text == "🎁 شحن كود هدية":
    user_states[user_id] = "waiting_redeem_code"
    bot.send_message(message.chat.id, "🎁 أرسل كود الهدية الآن لشحنه في حسابك:")

  elif text == "🔗 اضافة احالات":
    conn, cursor = get_db()
    cursor.execute(
        "SELECT COUNT(*) FROM users WHERE referred_by = ?", (user_id,)
    )
    ref_count = cursor.fetchone()[0]
    conn.close()

    bot_info = bot.get_me()
    ref_link = f"https://t.me/{bot_info.username}?start={user_id}"
    bot.send_message(
        message.chat.id,
        f"🔗 **رابط الإحالة الخاص بك:**\n\n`{ref_link}`\n\n"
        f"ℹ️ تكسب **500 ل.س** عن كل إحالة تنضم عبر رابطك.\n"
        f"⚠️ **شرط الإحالة:** البقاء في الاشتراكات الإلزامية لمدة ساعتين.\n"
        f"👥 عدد الإحالات المنضمة إليك: `{ref_count}` شخص",
        parse_mode="Markdown",
    )

  elif text == "📞 تواصل مع الدعم":
    user_states[user_id] = "waiting_support"
    bot.send_message(
        message.chat.id, "📞 أرسل رسالتك أو استفسارك الآن في رسالة واحدة:"
    )

  elif text == "💸 سحب رصيدي":
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("📱 سيريتيل كاش", callback_data="wd_syriatel"),
        types.InlineKeyboardButton("💳 شام كاش", callback_data="wd_sham"),
    )
    bot.send_message(
        message.chat.id, "اختر طريقة السحب المناسبة:", reply_markup=markup
    )


# التعامل مع أزرار قبول/رفض طلبات السحب من قبل المشرف
@bot.callback_query_handler(
    func=lambda call: call.data.startswith("wd_acc_")
    or call.data.startswith("wd_rej_")
)
def handle_withdrawal_decision(call):
  admin_id = get_admin_id()
  if call.from_user.id != admin_id:
    bot.answer_callback_query(
        call.id, "❌ هذه لوحة التحكم خاصة بالمشرف فقط!", show_alert=True
    )
    return

  parts = call.data.split("_")
  action = parts[1]  # acc or rej
  user_id = int(parts[2])
  amount = float(parts[3])

  if action == "acc":
    bot.answer_callback_query(call.id, "✅ تم قبول الطلب وإشعار المستخدم.")
    try:
      bot.send_message(
          user_id,
          f"✅ **تم قبول طلب سحبك بنجاح!**\n💰 المبلغ:"
          f" `{amount} ل.س`\nتم إرسال المبلغ إلى محفظتك.",
          parse_mode="Markdown",
      )
    except:
      pass
    try:
      if call.message.photo:
        bot.edit_message_caption(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            caption=call.message.caption + "\n\n✅ **حالة الطلب:** تم القبول ☑️",
            parse_mode="Markdown",
        )
      else:
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=call.message.text + "\n\n✅ **حالة الطلب:** تم القبول ☑️",
            parse_mode="Markdown",
        )
    except:
      pass
  elif action == "rej":
    conn, cursor = get_db()
    cursor.execute(
        "UPDATE users SET balance = balance + ? WHERE user_id = ?",
        (amount, user_id),
    )
    conn.commit()
    conn.close()

    bot.answer_callback_query(
        call.id, "❌ تم رفض الطلب وإعادة المبلغ لرصيد المستخدم."
    )
    try:
      bot.send_message(
          user_id,
          f"❌ **عذراً، تم رفض طلب سحبك.**\n💰 المبلغ `{amount} ل.س` تم إعادته إلى"
          " رصيدك المتاح.",
          parse_mode="Markdown",
      )
    except:
      pass
    try:
      if call.message.photo:
        bot.edit_message_caption(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            caption=call.message.caption + "\n\n❌ **حالة الطلب:** تم الرفض ❌",
            parse_mode="Markdown",
        )
      else:
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=call.message.text + "\n\n❌ **حالة الطلب:** تم الرفض ❌",
            parse_mode="Markdown",
        )
    except:
      pass


# التعامل مع أزرار لوحة تحكم المشرف (Inline)
@bot.callback_query_handler(func=lambda call: call.data.startswith("admin_"))
def handle_admin_callbacks(call):
  user_id = call.from_user.id
  admin_id = get_admin_id()
  if not admin_id or user_id != admin_id:
    bot.answer_callback_query(
        call.id, "❌ هذه لوحة التحكم خاصة بالمشرف فقط!", show_alert=True
    )
    return

  if call.data == "admin_create_code":
    bot.answer_callback_query(call.id)
    user_states[user_id] = "waiting_code_details"
    bot.send_message(
        call.message.chat.id,
        "➕ أرسل تفاصيل الكود بهذا الشكل بالصيغة:\n`المبلغ"
        " عدد_المستخدمين`\nمثال: `5000 20`",
        parse_mode="Markdown",
    )

  elif call.data == "admin_broadcast":
    bot.answer_callback_query(call.id)
    user_states[user_id] = "waiting_broadcast"
    bot.send_message(
        call.message.chat.id,
        "📢 أرسل الآن الرسالة (نص، صورة، أو وسائط) ليتم بثها فوراً لجميع"
        " المستخدمين:",
    )

  elif call.data == "admin_stats":
    conn, cursor = get_db()
    cursor.execute("SELECT COUNT(*) FROM users")
    total_users = cursor.fetchone()[0]
    cursor.execute("SELECT SUM(balance), SUM(frozen_balance) FROM users")
    res = cursor.fetchone()
    total_bal = res[0] or 0
    total_frozen = res[1] or 0
    conn.close()

    bot.answer_callback_query(
        call.id,
        f"👥 المستخدمين: {total_users}\n💰 الأرصدة المتاحة:"
        f" {total_bal}\n🔒 الأرصدة المجمدة: {total_frozen}",
        show_alert=True,
    )


# التعامل مع أزرار اختيار طريقة السحب
@bot.callback_query_handler(
    func=lambda call: call.data.startswith("wd_")
    and not call.data.startswith("wd_acc_")
    and not call.data.startswith("wd_rej_")
)
def handle_withdraw_callback(call):
  user_id = call.from_user.id
  if call.data == "wd_syriatel":
    bot.answer_callback_query(call.id, "سيريتيل كاش")
    user_temp_data[user_id] = {"method": "سيريتيل كاش"}
    user_states[user_id] = "waiting_withdraw_amount"
    bot.send_message(
        call.message.chat.id,
        "💸 ادخل المبلغ المراد سحبه (الحد الأدنى 10000 ل.س):",
    )
  elif call.data == "wd_sham":
    bot.answer_callback_query(call.id, "شام كاش")
    user_temp_data[user_id] = {"method": "شام كاش"}
    user_states[user_id] = "waiting_withdraw_amount"
    bot.send_message(
        call.message.chat.id,
        "💸 ادخل المبلغ المراد سحبه (الحد الأدنى 10000 ل.س):",
    )


if __name__ == "__main__":
  print("Bot is running...")
  bot.infinity_polling()
