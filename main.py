import asyncio
import logging
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import CommandStart

BOT_TOKEN = "8915045293:AAE44Drwj2LtvCcOugkQRGRgjW0bxnjJ5_Y"
ADMIN_ID = 6035361698  # Telegram ID raqamingiz

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()


@dp.message(CommandStart())
async def start_handler(message: types.Message):
  if message.from_user.id == ADMIN_ID:
    await message.answer(
        "Xush kelibsiz, Admin! Foydalanuvchiga javob berish uchun uning xabariga 'Reply' qiling."
    )
  else:
    await message.answer(
        "Assalomu alaykum! Xabaringizni yozib qoldiring, tez orada javob beramiz."
    )


# Foydalanuvchidan xabar kelganda Adminga ID bilan birga yuborish
@dp.message(F.from_user.id != ADMIN_ID)
async def forward_to_admin(message: types.Message):
  user = message.from_user
  text = (
      f"📩 **Yangi xabar!**\n"
      f"👤 **Ism:** {user.full_name}\n"
      f"🆔 **ID:** `{user.id}`\n\n"
      f"💬 **Xabar:** {message.text or '[Fayl/Rasm/Ovozli xabar]'}"
  )

  # Adminga foydalanuvchi ID si ko'rinadigan qilib yuboramiz
  await bot.send_message(
      chat_id=ADMIN_ID, text=text, parse_mode="Markdown"
  )


# Admin Reply qilganda javob yuborish
@dp.message(F.from_user.id == ADMIN_ID, F.reply_to_message)
async def reply_to_user(message: types.Message):
  try:
    # Reply qilingan xabardan foydalanuvchi ID sini ajratib olamiz
    replied_text = message.reply_to_message.text
    if "🆔 **ID:**" in replied_text:
      user_id = int(replied_text.split("🆔 **ID:** `")[1].split("`")[0])

      # Javobni foydalanuvchiga yuborish
      await bot.send_message(chat_id=user_id, text=message.text)
      await message.react([types.ReactionTypeEmoji(emoji="👍")])
    else:
      await message.answer(
          "❌ Xatolik: Javob berish uchun bot yuborgan xabarga 'Reply' qiling."
      )
  except Exception as e:
    await message.answer(f"❌ Xabar yuborishda xatolik: {e}")


async def main():
  await dp.start_polling(bot)


if __name__ == "__main__":
  logging.basicConfig(level=logging.INFO)
  asyncio.run(main())