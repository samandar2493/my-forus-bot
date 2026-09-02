import asyncio
import json
import logging
import os
import re
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import Command, CommandStart
from aiohttp import web

BOT_TOKEN = "8915045293:AAGKXI5Tq3VtiOr7rW9ZIuRlm4_k6J9SslA"
ADMIN_ID = 6035361698  # Telegram ID raqamingiz

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Yuborilgan xabarlarni xaritalash: {admin_msg_id: (user_id, user_msg_id)}
sent_messages_map = {}
USERS_FILE = "users.json"


def load_users():
  if os.path.exists(USERS_FILE):
    try:
      with open(USERS_FILE, "r") as f:
        return json.load(f)
    except Exception:
      return {}
  return {}


def save_users(users):
  try:
    with open(USERS_FILE, "w") as f:
      json.dump(users, f, ensure_ascii=False, indent=2)
  except Exception as e:
    logging.error(f"Faylga saqlashda xatolik: {e}")


users_db = load_users()


async def handle_ping(request):
  return web.Response(text="Bot 24/7 faol ishlamoqda!")


async def start_web_server():
  app = web.Application()
  app.router.add_get("/", handle_ping)
  runner = web.AppRunner(app)
  await runner.setup()
  port = int(os.environ.get("PORT", 8080))
  site = web.TCPSite(runner, "0.0.0.0", port)
  await site.start()


# /start handler
@dp.message(CommandStart())
async def start_handler(message: types.Message):
  user = message.from_user
  user_id_str = str(user.id)
  is_new_user = user_id_str not in users_db

  if is_new_user:
    users_db[user_id_str] = {
        "full_name": user.full_name,
        "username": user.username or "Mavjud emas",
    }
    save_users(users_db)

  if user.id == ADMIN_ID:
    await message.answer(
        "Xush kelibsiz, Admin!\n\n"
        "📊 /stat - Bot statistikasi va foydalanuvchilar ro'yxati\n"
        "🗑 /del - Yuborilgan xabarga Reply qilib `/del` yozsangiz, o'chadi\n"
        "✏️ **Tahrirlash:** Yuborgan xabaringizni tahrirlasangiz, foydalanuvchida ham o'zgaradi."
    )
  else:
    await message.answer(
        "Assalomu alaykum! Xabaringizni yozib qoldiring, tez orada javob beramiz."
    )

    # Botga kim start bosgani haqida adminga xabar
    uname = f"@{user.username}" if user.username else "Mavjud emas"
    admin_notify_text = (
        f"🚀 **Foydalanuvchi /start bosdi!**\n\n"
        f"🔹 Ism: {user.full_name}\n"
        f"🔹 Username: {uname}\n"
        f"🔹 ID: `{user.id}`"
    )
    await bot.send_message(
        chat_id=ADMIN_ID, text=admin_notify_text, parse_mode="Markdown"
    )


# /stat - Statistikani ko'rish
@dp.message(F.from_user.id == ADMIN_ID, Command("stat"))
async def show_stats(message: types.Message):
  total_users = len(users_db)
  text = (
      f"📊 **Bot Statistikasi:**\n\n"
      f"👤 Jami foydalanuvchilar: **{total_users} kishi**\n\n"
  )

  if total_users > 0:
    text += "📜 **Oxirgi foydalanuvchilar:**\n"
    for uid, uinfo in list(users_db.items())[-20:]:
      uname = (
          f"@{uinfo['username']}"
          if uinfo["username"] != "Mavjud emas"
          else "User"
      )
      text += f"• {uinfo['full_name']} ({uname}) — ID: `{uid}`\n"

  await message.answer(text, parse_mode="Markdown")


# /del - Xabarni ikkala tomondan o'chirish
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
    await message.answer("❌ Bu xabar o'chirish ro'yxatida topilmadi.")


# Admin yuborgan xabarini tahrirlaganda (Edit) foydalanuvchida ham o'zgarishi
@dp.edited_message(F.from_user.id == ADMIN_ID)
async def handle_admin_edited_message(message: types.Message):
  if message.message_id in sent_messages_map:
    user_id, user_msg_id = sent_messages_map[message.message_id]
    try:
      await bot.edit_message_text(
          chat_id=user_id, message_id=user_msg_id, text=message.text
      )
    except Exception as e:
      logging.error(f"Xabarni tahrirlashda xatolik: {e}")


# Foydalanuvchidan kelgan barcha xabarlarni Adminga uzatish
@dp.message(F.from_user.id != ADMIN_ID)
async def forward_to_admin(message: types.Message):
  user = message.from_user
  user_id_str = str(user.id)

  if user_id_str not in users_db:
    users_db[user_id_str] = {
        "full_name": user.full_name,
        "username": user.username or "Mavjud emas",
    }
    save_users(users_db)

  text = f"📩 **Yangi xabar!**\nIsm: {user.full_name}\nID: {user.id}\n\nXabar: {message.text or '[Media/Fayl]'}"
  await bot.send_message(chat_id=ADMIN_ID, text=text)


# Admin Reply qilib javob yozganda
@dp.message(F.from_user.id == ADMIN_ID, F.reply_to_message)
async def reply_to_user(message: types.Message):
  try:
    replied_text = message.reply_to_message.text or ""
    match = re.search(r"ID:\s*(\d+)", replied_text)

    if match:
      user_id = int(match.group(1))
      sent_msg = await bot.send_message(chat_id=user_id, text=message.text)
      await message.react([types.ReactionTypeEmoji(emoji="👍")])

      # Xabarni keyinchalik tahrirlash yoki o'chirish uchun xotiraga saqlaymiz
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
