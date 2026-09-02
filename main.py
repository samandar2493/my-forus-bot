import asyncio
import logging
import os
import re
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import Command, CommandStart
from aiohttp import web
from openai import AsyncOpenAI

BOT_TOKEN = "8915045293:AAE44Drwj2LtvCcOugkQRGRgjW0bxnjJ5_Y"
ADMIN_ID = 6035361698  # O'zingizning Telegram ID raqamingiz
OPENAI_API_KEY = "5a0015bc7a17302eb916a68a778f51a48047c30dbe01bd4151645bf5049b9676"

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
ai_client = AsyncOpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None

AI_ENABLED = False

# Xabarlarni o'chirish uchun ID larni saqlaydigan lug'at
# admin_reply_msg_id -> (user_id, sent_user_msg_id)
sent_messages_map = {}


async def handle_ping(request):
  return web.Response(text="Bot faol!")


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
  if message.from_user.id == ADMIN_ID:
    await message.answer(
        "Xush kelibsiz, Admin!\n\n"
        "🤖 /ai - AI rejimini yoqish/o'chirish\n"
        "🗑 /del - Yuborilgan xabarga 'Reply' qilib `/del` deb yozsangiz,"
        " foydalanuvchidan ham o'chadi."
    )
  else:
    await message.answer("Assalomu alaykum! Xabaringizni yozib qoldiring.")


@dp.message(F.from_user.id == ADMIN_ID, Command("ai"))
async def toggle_ai(message: types.Message):
  global AI_ENABLED
  AI_ENABLED = not AI_ENABLED
  status = "🟢 Yoqildi" if AI_ENABLED else "🔴 O'chirildi"
  await message.answer(f"AI Avto-javob: {status}")


# Admin yuborgan xabarni o'chirish buyrug'i (/del)
@dp.message(F.from_user.id == ADMIN_ID, Command("del"), F.reply_to_message)
async def delete_sent_message(message: types.Message):
  replied_msg_id = message.reply_to_message.message_id

  if replied_msg_id in sent_messages_map:
    user_id, user_msg_id = sent_messages_map[replied_msg_id]
    try:
      # Foydalanuvchining chatidagi xabarni o'chirish
      await bot.delete_message(chat_id=user_id, message_id=user_msg_id)

      # Admin chatidagi xabar va /del buyrug'ini o'chirish
      await bot.delete_message(
          chat_id=ADMIN_ID, message_id=message.reply_to_message.message_id
      )
      await bot.delete_message(chat_id=ADMIN_ID, message_id=message.message_id)

      del sent_messages_map[replied_msg_id]
    except Exception as e:
      await message.answer(
          f"❌ Xabarni o'chirishda xatolik (balki 48 soatdan o'tib ketgan): {e}"
      )
  else:
    await message.answer(
        "❌ Bu xabar o'chiriladigan xabarlar ro'yxatida topilmadi."
    )


# Foydalanuvchidan xabar kelganda
@dp.message(F.from_user.id != ADMIN_ID)
async def forward_to_admin(message: types.Message):
  user = message.from_user
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

      # AI bergan javobni ham xaritaga saqlaymiz
      sent_messages_map[sent_to_admin.message_id] = (
          message.chat.id,
          sent_user_msg.message_id,
      )
    except Exception as e:
      logging.error(f"AI error: {e}")


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

      # Admin yuborgan xabar ID sini foydalanuvchidagi ID bilan bog'laymiz
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
