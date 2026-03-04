import asyncio
from core.bot import bot, dp
from handlers import start, help

async def main():
    print("Bot started!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())