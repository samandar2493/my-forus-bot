import asyncio
import logging
import re
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import CommandStart

BOT_TOKEN = "8915045293:AAE44Drwj2LtvCcOugkQRGRgjW0bxnjJ5_Y"
ADMIN_ID = 6035361698  # O'zingizning Telegram ID raqamingiz

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()


@dp.message(CommandStart())
async def start_handler(message: types.Message):
  if message.from_user.id == ADMIN_ID:
    await message.answer(
        "Xush kelibsiz, Admin! Javob berish uchun kelgan xabarga 'Reply' qiling."
    )
  else:
    await message.answer(
        "Assalomu alaykum! Xabaringizni yozib qoldiring, tez orada javob beramiz."
    )


# Foydalanuvchi xabarlarini Adminga yo'naltirish
@dp.message(F.from_user.id != ADMIN_ID)
async def forward_to_admin(message: types.Message):
  user = message.from_user
  # ID raqamni aniq formatda yozamiz
  text = f"📩 Yangi xabar!\nIsm: {user.full_name}\nID: {user.id}\n\nXabar: {message.text or '[Rasm/Fayl/Ovozli xabar]'}"

  await bot.send_message(chat_id=ADMIN_ID, text=text)


# Admin Reply qilganda foydalanuvchiga javob yuborish
@dp.message(F.from_user.id == ADMIN_ID, F.reply_to_message)
async def reply_to_user(message: types.Message):
  try:
    replied_text = message.reply_to_message.text or ""

    # Matn ichidan ID: sonini muntazam ifoda (regex) orqali izlaymiz
    match = re.search(r"ID:\s*(\d+)", replied_text)

    if match:
      user_id = int(match.group(1))

      # Javobni yuborish
      await bot.send_message(chat_id=user_id, text=message.text)
      await message.react([types.ReactionTypeEmoji(emoji="👍")])
    else:
      await message.answer(
          "❌ ID topilmadi. Iltimos, bot yuborgan xabarga 'Reply' qiling."
      )

  except Exception as e:
    await message.answer(f"❌ Xatolik yuz berdi: {e}")


async def main():
  await dp.start_polling(bot)


if __name__ == "__main__":
  logging.basicConfig(level=logging.INFO)
  asyncio.run(main())


if __name__ == "__main__":
  logging.basicConfig(level=logging.INFO)
  asyncio.run(main())
