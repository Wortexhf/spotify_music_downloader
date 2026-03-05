import asyncio
from core.bot import bot, dp
from handlers import start, help, spotify

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())