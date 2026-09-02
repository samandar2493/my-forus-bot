import asyncio
import json
import logging
import os
import re
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import Command, CommandStart
from aiohttp import web
from openai import AsyncOpenAI

BOT_TOKEN = "8915045293:AAE44Drwj2LtvCcOugkQRGRgjW0bxnjJ5_Y"
ADMIN_ID = 6035361698  # O'zingizning Telegram ID raqamingiz
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
ai_client = AsyncOpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None

AI_ENABLED = False
sent_messages_map = {}

# Foydalanuvchilarni saqlash uchun JSON fayl yo'li
USERS_FILE = "users.json"


# Foydalanuvchilar ro'yxatini fayldan yuklash
def load_users():
  if os.path.exists(USERS_FILE):
    try:
      with open(USERS_FILE, "r") as f:
        return json.load(f)
    except Exception:
      return {}
  return {}


# Foydalanuvchilar ro'yxatini faylga saqlash
def save_users(users):
  with open(USERS_FILE, "w") as f:
    json.dump(users, f, ensure_ascii=False, indent=2)


# Dastur boshlanganda foydalanuvchilarni yuklaymiz
users_db = load_users()


async def handle_ping(request):
  return web.Response(text="Bot faol ishlamoqda!")


async def start_web_server():
  app = web.Application()
  app.router.add_get("/", handle_ping)
  runner = web.AppRunner(app)
  await runner.setup()
  port = int(os.environ.get("PORT", 8080))
  site = web.TCPSite(runner, "0.0.0.0", port)
  await site.start()


@dp.message(CommandStart())
async def start_handler(message: types.Message):
  user = message.from_user
  user_id_str = str(user.id)

  # Yangi foydalanuvchini bazaga qo'shish
  if user_id_str not in users_db:
    users_db[user_id_str] = {
        "full_name": user.full_name,
        "username": user.username or "Mavjud emas",
    }
    save_users(users_db)

  if user.id == ADMIN_ID:
    await message.answer(
        "Xush kelibsiz, Admin!\n\n"
        "📊 /stat - Bot statistikasini va foydalanuvchilar sonini ko'rish\n"
        "🤖 /ai - AI rejimini yoqish/o'chirish\n"
        "🗑 /del - Yuborilgan xabarga Reply qilib `/del` yozsangiz,"
        " foydalanuvchidan ham o'chadi."
    )
  else:
    await message.answer(
        "Assalomu alaykum! Xabaringizni yozib qoldiring, tez orada javob beramiz."
    )


# Admin uchun Statistika buyrug'i (/stat)
@dp.message(F.from_user.id == ADMIN_ID, Command("stat"))
async def show_stats(message: types.Message):
  total_users = len(users_db)
  text = f"📊 **Bot Statistikasi:**\n\n" f"👤 Jami foydalanuvchilar: **{total_users} kishi**\n\n"

  if total_users > 0:
    text += "📜 **Foydalanuvchilar ro'yxati:**\n"
    for uid, uinfo in list(users_db.items())[-20:]:  # Oxirgi 20 ta foydalanuvchi
      uname = (
          f"@{uinfo['username']}"
          if uinfo["username"] != "Mavjud emas"
          else "User"
      )
      text += f"• {uinfo['full_name']} ({uname}) — ID: `{uid}`\n"

  await message.answer(text, parse_mode="Markdown")


@dp.message(F.from_user.id == ADMIN_ID, Command("ai"))
async def toggle_ai(message: types.Message):
  global AI_ENABLED
  AI_ENABLED = not AI_ENABLED
  status = "🟢 Yoqildi" if AI_ENABLED else "🔴 O'chirildi"
  await message.answer(f"AI Avto-javob: {status}")


@dp.message(F.from_user.id == ADMIN_ID, Command("del"), F.reply_to_message)
async def delete_sent_message(message: types.Message):
  replied_msg_id = message.reply_to_message.message_id
  if replied_msg_id in sent_messages_map:
    user_id, user_msg_id = sent_messages_map[replied_msg_id]
    try:
      await bot.delete_message(chat_id=user_id, message_id=user_msg_id)
      await bot.delete_message(
          chat_id=ADMIN_ID, message_id=message.reply_to_message.message_id
      )
      await bot.delete_message(chat_id=ADMIN_ID, message_id=message.message_id)
      del sent_messages_map[replied_msg_id]
    except Exception as e:
      await message.answer(f"❌ Xabarni o'chirishda xatolik: {e}")
  else:
    await message.answer(
        "❌ Bu xabar o'chiriladigan xabarlar ro'yxatida topilmadi."
    )


@dp.message(F.from_user.id != ADMIN_ID)
async def forward_to_admin(message: types.Message):
  user = message.from_user
  user_id_str = str(user.id)

  # Agar foydalanuvchi start bosmasdan to'g'ridan-to'g'ri yozgan bo'lsa ham bazaga qo'shish
  if user_id_str not in users_db:
    users_db[user_id_str] = {
        "full_name": user.full_name,
        "username": user.username or "Mavjud emas",
    }
    save_users(users_db)

  text = f"📩 Yangi xabar!\nIsm: {user.full_name}\nID: {user.id}\n\nXabar: {message.text or '[Media]'}"
  sent_to_admin = await bot.send_message(chat_id=ADMIN_ID, text=text)

  if AI_ENABLED and message.text and ai_client:
    try:
      response = await ai_client.chat.completions.create(
          model="gpt-4o-mini",
          messages=[
              {"role": "system", "content": "Siz yordamchisiz."},
              {"role": "user", "content": message.text},
          ],
      )
      ai_reply = response.choices[0].message.content
      sent_user_msg = await message.answer(ai_reply)

      sent_messages_map[sent_to_admin.message_id] = (
          message.chat.id,
          sent_user_msg.message_id,
      )
    except Exception as e:
      logging.error(f"AI error: {e}")


@dp.message(F.from_user.id == ADMIN_ID, F.reply_to_message)
async def reply_to_user(message: types.Message):
  try:
    replied_text = message.reply_to_message.text or ""
    match = re.search(r"ID:\s*(\d+)", replied_text)

    if match:
      user_id = int(match.group(1))
      sent_msg = await bot.send_message(chat_id=user_id, text=message.text)
      await message.react([types.ReactionTypeEmoji(emoji="👍")])
      sent_messages_map[message.message_id] = (user_id, sent_msg.message_id)
    else:
      await message.answer(
          "❌ ID topilmadi. Bot yuborgan xabarga 'Reply' qiling."
      )
  except Exception as e:
    await message.answer(f"❌ Xatolik yuz berdi: {e}")


async def main():
  await start_web_server()
  await dp.start_polling(bot)


if __name__ == "__main__":
  logging.basicConfig(level=logging.INFO)
  asyncio.run(main())
