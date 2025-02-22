from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from datetime import datetime
import json
import os
import nest_asyncio
from dotenv import load_dotenv

nest_asyncio.apply()

# Загрузка переменных окружения
load_dotenv()

# Файл для хранения данных о кредитах
CREDITS_FILE = "credits.json"


# Загрузка данных о кредитах
def load_credits():
    if os.path.exists(CREDITS_FILE):
        with open(CREDITS_FILE, "r") as file:
            return json.load(file)
    return {}


# Сохранение данных о кредитах
def save_credits(credits):
    with open(CREDITS_FILE, "w") as file:
        json.dump(credits, file)


# Команда /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Привет! Я бот для напоминаний о кредитах. Используй /addcredit чтобы добавить кредит.")


# Команда /addcredit
async def add_credit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        credit_name = context.args[0]
        amount = float(context.args[1])
        due_date = context.args[2]

        # Получаем chat_id пользователя
        chat_id = str(update.message.chat_id)

        # Загружаем данные о кредитах
        credits = load_credits()

        # Если у пользователя еще нет записей, создаем для него пустой словарь
        if chat_id not in credits:
            credits[chat_id] = {}

        # Добавляем кредит
        credits[chat_id][credit_name] = {"amount": amount, "due_date": due_date}
        save_credits(credits)

        await update.message.reply_text(f"Кредит '{credit_name}' добавлен!")
    except (IndexError, ValueError):
        await update.message.reply_text("Используй: /addcredit <название> <сумма> <дата>")


# Команда /listcredits
async def list_credits(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Получаем chat_id пользователя
    chat_id = str(update.message.chat_id)

    # Загружаем данные о кредитах
    credits = load_credits()

    # Проверяем, есть ли кредиты у пользователя
    if chat_id not in credits or not credits[chat_id]:
        await update.message.reply_text("Нет активных кредитов.")
    else:
        message = "Ваши кредиты:\n"
        for name, details in credits[chat_id].items():
            message += f"{name}: {details['amount']} руб., до {details['due_date']}\n"
        await update.message.reply_text(message)


# Команда /removecredit
async def remove_credit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        credit_name = context.args[0]
        chat_id = str(update.message.chat_id)
        credits = load_credits()

        if chat_id in credits and credit_name in credits[chat_id]:
            del credits[chat_id][credit_name]
            save_credits(credits)
            await update.message.reply_text(f"Кредит '{credit_name}' удален!")
        else:
            await update.message.reply_text("Кредит не найден.")
    except IndexError:
        await update.message.reply_text("Используй: /removecredit <название>")


# Напоминание о кредитах
async def check_credits(context: ContextTypes.DEFAULT_TYPE):
    credits = load_credits()
    for chat_id, user_credits in credits.items():
        for name, details in user_credits.items():
            due_date = datetime.strptime(details["due_date"], "%Y-%m-%d")
            today = datetime.now()

            # Проверяем, осталось ли до срока 3 дня или меньше
            if 0 <= (due_date - today).days <= 3:
                await context.bot.send_message(
                    chat_id=chat_id,
                    text=f"⏰ Напоминание: кредит '{name}' на {details['amount']} руб. должен быть погашен до {details['due_date']}."
                )


# Основная функция
async def main():
    # Чтение токена из переменных окружения
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        raise ValueError("Токен бота не найден в переменных окружения!")

    # Создание приложения
    application = Application.builder().token(token).build()

    # Регистрация команд
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("addcredit", add_credit))
    application.add_handler(CommandHandler("listcredits", list_credits))
    application.add_handler(CommandHandler("removecredit", remove_credit))

    # Запуск напоминаний
    job_queue = application.job_queue
    job_queue.run_repeating(check_credits, interval=86400, first=0)  # Проверка каждый день

    # Запуск бота
    await application.run_polling()

if __name__ == "__main__":
    import asyncio


    try:
        asyncio.run(main())
    except RuntimeError as e:
        if str(e) == "Event loop is closed":
            # Если событийный цикл уже закрыт, запускаем его вручную
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(main())
        else:
            raise e
