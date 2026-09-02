import asyncio
import logging
import os
import re
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import Command, CommandStart
from aiohttp import web
from openai import AsyncOpenAI

BOT_TOKEN = "8915045293:AAE44Drwj2LtvCcOugkQRGRgjW0bxnjJ5_Y"
ADMIN_ID = 6035361698  # Telegram ID raqamingiz
OPENAI_API_KEY = "OPENAI_API_KEYINI_SHUYERGA_YAZING"  # Sk-... bilan boshlanadi

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
ai_client = AsyncOpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None

# AI holati (Odatiy holatda o'chiq bo'ladi)
AI_ENABLED = False

# Xabarlar ID larini moslashtirib saqlash uchun lug'at (Xabarni o'chirish uchun)
# key: admin_msg_id -> value: user_chat_id, user_msg_id
message_map = {}


# Render uchun soxta veb-server
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


@dp.message(CommandStart())
async def start_handler(message: types.Message):
  if message.from_user.id == ADMIN_ID:
    await message.answer(
        "Xush kelibsiz, Admin!\n\n"
        "🤖 **AI buyruqlari:**\n"
        "/ai - AI javob berishini yoqish/o'chirish\n\n"
        "Javob berish uchun kelgan xabarga 'Reply' qiling."
    )
  else:
    await message.answer(
        "Assalomu alaykum! Xabaringizni yozib qoldiring, tez orada javob beramiz."
    )


# Admin uchun AI rejimini yoqish va o'chirish buyrug'i
@dp.message(F.from_user.id == ADMIN_ID, Command("ai"))
async def toggle_ai(message: types.Message):
  global AI_ENABLED
  AI_ENABLED = not AI_ENABLED
  status = (
      "🟢 **Yoqildi** (Foydalanuvchilarga AI javob beradi)"
      if AI_ENABLED
      else "🔴 **O'chirildi** (Faqat o'zingiz javob berasiz)"
  )
  await message.answer(f"AI Avto-javob rejimi: {status}", parse_mode="Markdown")


# Foydalanuvchidan xabar kelganda
@dp.message(F.from_user.id != ADMIN_ID)
async def forward_to_admin(message: types.Message):
  user = message.from_user
  text = f"📩 Yangi xabar!\nIsm: {user.full_name}\nID: {user.id}\n\nXabar: {message.text or '[Media]'}"

  # Adminga yo'naltirish
  sent_to_admin = await bot.send_message(chat_id=ADMIN_ID, text=text)

  # Agar AI yoqilgan bo'lsa va matnli xabar bo'lsa, AI javob beradi
  if AI_ENABLED and message.text and ai_client:
    try:
      response = await ai_client.chat.completions.create(
          model="gpt-4o-mini",
          messages=[
              {
                  "role": "system",
                  "content": (
                      "Siz professional va xushmuomala yordamchisiz. Barcha"
                      " savollarga aniq va loqaydsiz javob bering."
                  ),
              },
              {"role": "user", "content": message.text},
          ],
      )
      ai_reply = response.choices[0].message.content
      sent_user_msg = await message.answer(ai_reply)

      # Xabarlar xaritasiga saqlaymiz (O'chirish uchun)
      message_map[sent_to_admin.message_id] = (
          message.chat.id,
          sent_user_msg.message_id,
      )
    except Exception as e:
      logging.error(f"AI Xatolik: {e}")


# Admin Reply qilganda javob yuborish
@dp.message(F.from_user.id == ADMIN_ID, F.reply_to_message)
async def reply_to_user(message: types.Message):
  try:
    replied_text = message.reply_to_message.text or ""
    match = re.search(r"ID:\s*(\d+)", replied_text)

    if match:
      user_id = int(match.group(1))
      sent_msg = await bot.send_message(chat_id=user_id, text=message.text)
      await message.react([types.ReactionTypeEmoji(emoji="👍")])

      # Admin xabarining ID sini foydalanuvchiga borgan xabar ID si bilan bog'laymiz
      message_map[message.message_id] = (user_id, sent_msg.message_id)
    else:
      await message.answer(
          "❌ ID topilmadi. Bot yuborgan xabarga 'Reply' qiling."
      )
  except Exception as e:
    await message.answer(f"❌ Xatolik yuz berdi: {e}")


# Admin guruhda/chatda xabarni o'chirsa (Sync Delete)
@dp.message(F.from_user.id == ADMIN_ID, F.deleted)
async def handle_deleted_message(message: types.Message):
  pass  # Telegram Bot API hozirda o'chirilgan xabar voqeasini to'g'ridan-to'g'ri bermaydi


async def main():
  await start_web_server()
  await dp.start_polling(bot)


if __name__ == "__main__":
  logging.basicConfig(level=logging.INFO)
  asyncio.run(main())
