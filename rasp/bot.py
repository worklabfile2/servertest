from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (Application, CommandHandler, CallbackQueryHandler,
                          ConversationHandler)

# Обновленные параметры
LANG_SUBGROUP, LAB_SUBGROUP = range(2)
user_data = {}

# Список подгрупп иностранного языка с преподавателями
LANG_GROUPS = {
    "подгр.а1": "Гуминская О.П.",
    "подгр.а2": "Черник Наталья Николаевна",
    "подгр.а3": "Кирильчик Татьяна Казимировна",
    "подгр.а4": "Малашенко Елена Александровна",
    "подгр.нем.яз": "Масленкова Владислава Павловна",
}

# Функция старта
async def start(update: Update, context):
    keyboard = [
        [InlineKeyboardButton(f"{group} ({teacher})", callback_data=group)]
        for group, teacher in LANG_GROUPS.items()
    ]
    await update.message.reply_text(
        "Выберите вашу подгруппу для иностранного языка (преподаватель указан в скобках):",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )
    return LANG_SUBGROUP

# Выбор подгруппы для иностранного языка
async def lang_subgroup_selected(update: Update, context):
    query = update.callback_query
    user_id = query.from_user.id
    lang_group = query.data
    teacher = LANG_GROUPS[lang_group]
    user_data[user_id] = {"lang_subgroup": lang_group, "lang_teacher": teacher}
    await query.answer()
    keyboard = [
        [InlineKeyboardButton("подгр.1", callback_data='подгр.1')],
        [InlineKeyboardButton("подгр.2", callback_data='подгр.2')],
    ]
    await query.edit_message_text(
        text=(
            f"Вы выбрали подгруппу {lang_group} для иностранного языка с преподавателем {teacher}.\n"
            "Теперь выберите вашу подгруппу для лабораторных занятий:"
        ),
        reply_markup=InlineKeyboardMarkup(keyboard),
    )
    return LAB_SUBGROUP

# Выбор подгруппы для лабораторных занятий
async def lab_subgroup_selected(update: Update, context):
    query = update.callback_query
    user_id = query.from_user.id
    lab_group = query.data
    user_data[user_id]["lab_subgroup"] = lab_group
    await query.answer()
    await query.edit_message_text(
        text=(
            f"Настройка завершена!\n\n"
            f"Ваши данные:\n"
            f"Иностранный язык: {user_data[user_id]['lang_subgroup']} "
            f"(Преподаватель: {user_data[user_id]['lang_teacher']})\n"
            f"Лабораторные занятия: {lab_group}"
        )
    )
    # Запланируйте уведомления здесь
    return ConversationHandler.END

# Функция отмены
async def cancel(update: Update, context):
    await update.message.reply_text("Настройка отменена.")
    return ConversationHandler.END

def main():
    # Вставьте сюда токен вашего бота
    TOKEN = "7876563684:AAHEPHfcPS54FR1UFlaazA51T3-mwVJTFwE"

    # Создаем приложение
    application = Application.builder().token(TOKEN).build()

    # Добавляем ConversationHandler
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            LANG_SUBGROUP: [CallbackQueryHandler(lang_subgroup_selected)],
            LAB_SUBGROUP: [CallbackQueryHandler(lab_subgroup_selected)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    application.add_handler(conv_handler)

    # Запускаем бота
    application.run_polling()

if __name__ == "__main__":
    main()
