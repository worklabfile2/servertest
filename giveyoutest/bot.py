# bot.py
import logging
import uuid
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    CallbackQueryHandler,
    MessageHandler,
    filters,
)
from telegram.error import BadRequest
from database import (
    setup_database,
    add_user,
    get_user,
    get_user_by_username,
    add_item,
    transfer_item,
    get_pending_transfers,
    update_transfer_status,
    get_sent_transfers,
    get_received_transfers,
    get_history,
    get_user_items,
    get_created_items,
    get_item,
    get_connection,
    get_recent_contacts,  # Новая функция для получения последних контактов
)

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Определение кнопок для главного меню
def main_menu_keyboard():
    keyboard = [
        [InlineKeyboardButton("Мои Вещи", callback_data='my_items')],
        [InlineKeyboardButton("Добавить Вещь", callback_data='add_item')],
        [InlineKeyboardButton("Передать Вещь", callback_data='transfer_item')],
        [InlineKeyboardButton("Ожидающие Передачи", callback_data='pending_transfers')],
        [InlineKeyboardButton("Другие Опции", callback_data='other_options')],
    ]
    return InlineKeyboardMarkup(keyboard)

# Клавиатура для подменю "Другие Опции"
def other_options_keyboard():
    keyboard = [
        [InlineKeyboardButton("Созданные Мною Вещи", callback_data='created_items')],
        [InlineKeyboardButton("Отправленные Передачи", callback_data='sent_transfers')],
        [InlineKeyboardButton("Полученные Передачи", callback_data='received_transfers')],
        [InlineKeyboardButton("История Вещи", callback_data='history')],
        [InlineKeyboardButton("Назад", callback_data='back_to_main')],
    ]
    return InlineKeyboardMarkup(keyboard)

# Функция обработчика ошибок
async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Логирует ошибку и отправляет сообщение пользователю с кнопкой возврата в главное меню."""
    logger.error(msg="Exception while handling an update:", exc_info=context.error)

    # Сообщение об ошибке
    error_message = "Произошла ошибка. Пожалуйста, попробуйте снова позже."

    # Определяем, как реагировать в зависимости от типа обновления
    if isinstance(update, Update) and update.effective_message:
        await update.effective_message.reply_text(
            error_message,
            reply_markup=main_menu_keyboard()
        )
    elif isinstance(update, Update) and update.callback_query:
        try:
            await update.callback_query.message.reply_text(
                error_message,
                reply_markup=main_menu_keyboard()
            )
        except Exception as e:
            logger.error(f"Не удалось отправить сообщение об ошибке пользователю: {e}")

# Команда /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    add_user(user.id, user.username, user.first_name, user.last_name)
    await update.message.reply_text(
        f"Привет, {user.first_name}! Я бот для управления передачей вещей.",
        reply_markup=main_menu_keyboard()
    )

# Обработчик нажатия кнопок главного меню
async def main_menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    user = update.effective_user

    if data == 'add_item':
        await query.edit_message_text("Введите название вещи:")
        context.user_data['action'] = 'adding_item'
        return

    elif data == 'transfer_item':
        items = get_user_items(user.id)
        if not items:
            await query.edit_message_text("У вас нет вещей для передачи.", reply_markup=main_menu_keyboard())
            return
        keyboard = []
        for item in items:
            keyboard.append([InlineKeyboardButton(f"{item[1]} ({item[0]})", callback_data=f"transfer_select_{item[0]}")])
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text("Выберите вещь для передачи:", reply_markup=reply_markup)
        return

    elif data == 'my_items':
        items = get_user_items(user.id)
        if not items:
            await query.edit_message_text("У вас нет вещей.", reply_markup=main_menu_keyboard())
            return
        message = "Ваши текущие вещи:\n"
        for item in items:
            message += f"- {item[1]} (UUID: {item[0]})\n"
        await query.edit_message_text(message, reply_markup=main_menu_keyboard())

    elif data == 'pending_transfers':
        transfers = get_pending_transfers(user.id)
        if not transfers:
            await query.edit_message_text("Нет передач, ожидающих вашего подтверждения.", reply_markup=main_menu_keyboard())
            return
        keyboard = []
        for transfer in transfers:
            transfer_id, item_name, sender_username, timestamp = transfer
            keyboard.append([
                InlineKeyboardButton(f"Принять {item_name} от @{sender_username}", callback_data=f"approve_transfer_{transfer_id}"),
                InlineKeyboardButton(f"Отклонить {item_name} от @{sender_username}", callback_data=f"reject_transfer_{transfer_id}")
            ])
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text("У вас есть передачи, ожидающие подтверждения:", reply_markup=reply_markup)

    elif data == 'other_options':
        await query.edit_message_text("Другие опции:", reply_markup=other_options_keyboard())

    elif data == 'back_to_main':
        await query.edit_message_text("Главное меню:", reply_markup=main_menu_keyboard())

    elif data == 'created_items':
        items = get_created_items(user.id)
        if not items:
            await query.edit_message_text("Вы не создали ни одной вещи.", reply_markup=other_options_keyboard())
            return
        message = "Ваши созданные вещи и текущие владельцы:\n"
        for item in items:
            item_uuid, item_name, owner_username = item
            owner = get_user_by_username(owner_username)
            if owner:
                owner_first_name = owner[2]
                owner_last_name = owner[3] if owner[3] else ""
                owner_name = f"{owner_first_name} {owner_last_name}".strip()
                owner_username_display = f"@{owner_username}" if owner_username else ""
            else:
                owner_name = "Неизвестный"
                owner_username_display = ""
            message += f"- {item_name} (UUID: {item_uuid})\n  Владелец: {owner_name} {owner_username_display}\n"
        await query.edit_message_text(message, reply_markup=other_options_keyboard())

    elif data == 'sent_transfers':
        transfers = get_sent_transfers(user.id)
        if not transfers:
            await query.edit_message_text("У вас нет отправленных передач.", reply_markup=other_options_keyboard())
            return
        message = "Отправленные передачи:\n"
        for transfer in transfers:
            transfer_id, item_uuid, item_name, receiver_username, status, timestamp = transfer
            receiver = get_user_by_username(receiver_username)
            if receiver:
                receiver_first_name = receiver[2]
                receiver_last_name = receiver[3] if receiver[3] else ""
                receiver_name = f"{receiver_first_name} {receiver_last_name}".strip()
                receiver_username_display = f"@{receiver_username}" if receiver_username else ""
            else:
                receiver_name = "Неизвестный"
                receiver_username_display = ""
            message += f"- Вещь: {item_name} (UUID: {item_uuid})\n  Получатель: {receiver_name} {receiver_username_display}\n  Статус: {status}\n  Дата: {timestamp}\n\n"
        await query.edit_message_text(message, reply_markup=other_options_keyboard())

    elif data == 'received_transfers':
        transfers = get_received_transfers(user.id)
        if not transfers:
            await query.edit_message_text("У вас нет полученных передач.", reply_markup=other_options_keyboard())
            return
        message = "Полученные передачи:\n"
        for transfer in transfers:
            transfer_id, item_uuid, item_name, sender_username, status, timestamp = transfer
            sender = get_user_by_username(sender_username)
            if sender:
                sender_first_name = sender[2]
                sender_last_name = sender[3] if sender[3] else ""
                sender_name = f"{sender_first_name} {sender_last_name}".strip()
                sender_username_display = f"@{sender_username}" if sender_username else ""
            else:
                sender_name = "Неизвестный"
                sender_username_display = ""
            message += f"- Вещь: {item_name} (UUID: {item_uuid})\n  Отправитель: {sender_name} {sender_username_display}\n  Статус: {status}\n  Дата: {timestamp}\n\n"
        await query.edit_message_text(message, reply_markup=other_options_keyboard())

    elif data == 'history':
        # Отобразить список вещей, созданных пользователем
        items = get_created_items(user.id)
        if not items:
            await query.edit_message_text("Вы не создали ни одной вещи.", reply_markup=other_options_keyboard())
            return
        keyboard = []
        for item in items:
            item_uuid, item_name, _ = item
            keyboard.append([InlineKeyboardButton(f"{item_name} ({item_uuid})", callback_data=f"view_history_{item_uuid}")])
        keyboard.append([InlineKeyboardButton("Назад", callback_data='other_options')])
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text("Выберите вещь для просмотра истории:", reply_markup=reply_markup)

    elif data.startswith('view_history_'):
        uuid_selected = data.split('_')[-1]
        history = get_history(uuid_selected)
        if not history:
            await query.edit_message_text("История не найдена для данного UUID.", reply_markup=other_options_keyboard())
            return
        message = f"История для UUID {uuid_selected}:\n"
        for record in history:
            message += f"{record[1]}: {record[0]}\n"
        await query.edit_message_text(message, reply_markup=other_options_keyboard())

    elif data.startswith('transfer_select_'):
        uuid_selected = data.split('_')[-1]
        context.user_data['transfer_uuid'] = uuid_selected

        # Предложить выбор получателя
        keyboard = [
            [InlineKeyboardButton("Выбрать из последних контактов", callback_data='choose_recent_recipient')],
            [InlineKeyboardButton("Ввести имя пользователя вручную", callback_data='enter_recipient_manually')],
            [InlineKeyboardButton("Отмена", callback_data='back_to_main')],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text("Как вы хотите выбрать получателя?", reply_markup=reply_markup)

    elif data == 'choose_recent_recipient':
        recent_contacts = get_recent_contacts(user.id)
        if not recent_contacts:
            await query.edit_message_text("Нет недавних контактов. Пожалуйста, введите имя пользователя вручную.", reply_markup=main_menu_keyboard())
            return
        keyboard = []
        for contact in recent_contacts:
            contact_user_id, contact_username, contact_first_name = contact
            keyboard.append([InlineKeyboardButton(f"{contact_first_name} (@{contact_username})", callback_data=f"select_recipient_id_{contact_user_id}")])
        keyboard.append([InlineKeyboardButton("Отмена", callback_data='back_to_main')])
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text("Выберите получателя из недавних контактов:", reply_markup=reply_markup)

    elif data.startswith('select_recipient_id_'):
        recipient_id = int(data.split('_')[-1])
        context.user_data['recipient_id'] = recipient_id
        await process_transfer(update, context)
        return

    elif data == 'enter_recipient_manually':
        await query.edit_message_text("Введите имя и @username пользователя, которому хотите передать вещь (например, Иван @ivan):")
        context.user_data['action'] = 'transferring_item'
        return

    elif data.startswith('select_recipient_'):
        recipient_username = data.split('_')[-1]
        context.user_data['recipient_username'] = recipient_username
        await process_transfer(update, context)
        return

    elif data.startswith('approve_transfer_') or data.startswith('reject_transfer_'):
        await handle_transfer_response(update, context)

    else:
        await query.edit_message_text("Неверная команда.", reply_markup=main_menu_keyboard())

# Обработчик текстовых сообщений
async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    text = update.message.text.strip()

    action = context.user_data.get('action')

    if action == 'adding_item':
        item_name = text
        if not item_name:
            await update.message.reply_text("Название вещи не может быть пустым. Попробуйте снова.", reply_markup=main_menu_keyboard())
            context.user_data.pop('action', None)
            return
        # Используем функцию add_item из database.py, которая теперь возвращает uuid
        item_uuid = add_item(item_name, user.id, user.id)  # creator_id = user.id, owner_id = user.id
        await update.message.reply_text(f"Вещь '{item_name}' добавлена с UUID: {item_uuid}", reply_markup=main_menu_keyboard())
        context.user_data.pop('action', None)

    elif action == 'transferring_item':
        receiver_input = text
        try:
            name_part, username_part = receiver_input.rsplit(" ", 1)
            if not username_part.startswith("@"):
                raise ValueError
            receiver_username = username_part[1:]  # Удалить '@'
        except ValueError:
            await update.message.reply_text("Пожалуйста, введите имя и @username в правильном формате (например, Иван @ivan).", reply_markup=main_menu_keyboard())
            context.user_data.pop('action', None)
            return

        context.user_data['recipient_username'] = receiver_username
        await process_transfer(update, context)

    else:
        await update.message.reply_text("Неизвестная команда. Пожалуйста, используйте меню для навигации.", reply_markup=main_menu_keyboard())

# Функция обработки передачи вещи
async def process_transfer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    sender_id = user.id
    uuid_selected = context.user_data.get('transfer_uuid')

    # Определение получателя
    recipient_id = context.user_data.get('recipient_id')
    recipient_username = context.user_data.get('recipient_username')

    if recipient_id:
        receiver = get_user(recipient_id)
    elif recipient_username:
        receiver = get_user_by_username(recipient_username)
    else:
        # Нет информации о получателе
        if update.message:
            await update.message.reply_text("Не удалось определить получателя.", reply_markup=main_menu_keyboard())
        elif update.callback_query:
            await update.callback_query.message.reply_text("Не удалось определить получателя.", reply_markup=main_menu_keyboard())
        context.user_data.pop('recipient_username', None)
        context.user_data.pop('recipient_id', None)
        context.user_data.pop('action', None)
        return

    if not receiver:
        if update.message:
            await update.message.reply_text("Пользователь не найден или не зарегистрирован в системе.", reply_markup=main_menu_keyboard())
        elif update.callback_query:
            await update.callback_query.message.reply_text("Пользователь не найден или не зарегистрирован в системе.", reply_markup=main_menu_keyboard())
        context.user_data.pop('recipient_username', None)
        context.user_data.pop('recipient_id', None)
        context.user_data.pop('action', None)
        return

    receiver_id, receiver_username, receiver_first_name, receiver_last_name = receiver

    # Проверка, что вещь принадлежит отправителю
    item = get_item(uuid_selected)
    if not item or item[3] != sender_id:
        if update.message:
            await update.message.reply_text("Вы не являетесь владельцем этой вещи.", reply_markup=main_menu_keyboard())
        elif update.callback_query:
            await update.callback_query.message.reply_text("Вы не являетесь владельцем этой вещи.", reply_markup=main_menu_keyboard())
        context.user_data.pop('recipient_username', None)
        context.user_data.pop('recipient_id', None)
        context.user_data.pop('action', None)
        return

    # Создание передачи и получение transfer_id
    transfer_id = transfer_item(uuid_selected, sender_id, receiver_id)

    # Получение деталей отправителя
    sender = get_user(sender_id)
    if sender:
        sender_first_name = sender[2]
        sender_last_name = sender[3] if sender[3] else ""
        sender_name = f"{sender_first_name} {sender_last_name}".strip()
        sender_username_display = f"@{sender[1]}" if sender and sender[1] else ""
    else:
        sender_name = "Неизвестный"
        sender_username_display = ""

    item_name = item[1]

    # Уведомление получателю о новой передаче
    try:
        await context.bot.send_message(
            chat_id=receiver_id,
            text=f"Пользователь {sender_name} {sender_username_display} хочет передать вам вещь '{item_name}' (UUID: {uuid_selected}).\n"
                 f"Вы можете принять или отклонить передачу.",
            reply_markup=InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("Принять", callback_data=f"approve_transfer_{transfer_id}"),
                    InlineKeyboardButton("Отклонить", callback_data=f"reject_transfer_{transfer_id}")
                ]
            ])
        )
    except Exception as e:
        logger.error(f"Не удалось отправить сообщение получателю: {e}")
        if update.message:
            await update.message.reply_text("Не удалось отправить уведомление получателю.", reply_markup=main_menu_keyboard())
        elif update.callback_query:
            await update.callback_query.message.reply_text("Не удалось отправить уведомление получателю.", reply_markup=main_menu_keyboard())
        context.user_data.pop('recipient_username', None)
        context.user_data.pop('recipient_id', None)
        context.user_data.pop('action', None)
        return

    # Уведомление отправителю о том, что передача ожидает подтверждения
    if update.message:
        await update.message.reply_text("Передача отправлена и ожидает подтверждения.", reply_markup=main_menu_keyboard())
    elif update.callback_query:
        await update.callback_query.message.reply_text("Передача отправлена и ожидает подтверждения.", reply_markup=main_menu_keyboard())

    context.user_data.pop('recipient_username', None)
    context.user_data.pop('recipient_id', None)
    context.user_data.pop('action', None)

# Обработка принятия и отклонения передач
async def handle_transfer_response(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    user = update.effective_user

    if data.startswith("approve_transfer_"):
        transfer_id = data.split("_")[-1]
        # Найти передачу по id и receiver_id и статус 'Pending Acceptance'
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT uuid FROM transfers WHERE id = ? AND receiver_id = ? AND status = "Pending Acceptance"', (transfer_id, user.id))
        transfer = cursor.fetchone()
        if not transfer:
            await query.edit_message_text("Передача уже обработана или не существует.", reply_markup=main_menu_keyboard())
            conn.close()
            return
        uuid_selected = transfer[0]
        update_transfer_status(transfer_id, 'Accepted')

        # Обновить владельца вещи
        cursor.execute('UPDATE items SET owner_id = ? WHERE uuid = ?', (user.id, uuid_selected))
        conn.commit()

        # Отправить уведомление отправителю
        cursor.execute('SELECT sender_id FROM transfers WHERE id = ?', (transfer_id,))
        sender_info = cursor.fetchone()
        if sender_info:
            sender_id = sender_info[0]
            sender = get_user(sender_id)
            if sender:
                sender_first_name = sender[2]
                sender_last_name = sender[3] if sender[3] else ""
                sender_name = f"{sender_first_name} {sender_last_name}".strip()
                sender_username = f"@{sender[1]}" if sender[1] else ""
                try:
                    await context.bot.send_message(
                        chat_id=sender_id,
                        text=f"Ваша передача вещи '{uuid_selected}' была принята пользователем @{user.username}."
                    )
                except Exception as e:
                    logger.error(f"Не удалось уведомить отправителя: {e}")
        conn.close()

        await query.edit_message_text("Передача принята.", reply_markup=main_menu_keyboard())

    elif data.startswith("reject_transfer_"):
        transfer_id = data.split("_")[-1]
        # Найти передачу по id и receiver_id и статус 'Pending Acceptance'
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT uuid FROM transfers WHERE id = ? AND receiver_id = ? AND status = "Pending Acceptance"', (transfer_id, user.id))
        transfer = cursor.fetchone()
        if not transfer:
            await query.edit_message_text("Передача уже обработана или не существует.", reply_markup=main_menu_keyboard())
            conn.close()
            return
        uuid_selected = transfer[0]
        update_transfer_status(transfer_id, 'Rejected')

        # Отправить уведомление отправителю
        cursor.execute('SELECT sender_id FROM transfers WHERE id = ?', (transfer_id,))
        sender_info = cursor.fetchone()
        if sender_info:
            sender_id = sender_info[0]
            sender = get_user(sender_id)
            if sender:
                sender_first_name = sender[2]
                sender_last_name = sender[3] if sender[3] else ""
                sender_name = f"{sender_first_name} {sender_last_name}".strip()
                sender_username = f"@{sender[1]}" if sender[1] else ""
                try:
                    await context.bot.send_message(
                        chat_id=sender_id,
                        text=f"Ваша передача вещи '{uuid_selected}' была отклонена пользователем @{user.username}."
                    )
                except Exception as e:
                    logger.error(f"Не удалось уведомить отправителя: {e}")
        conn.close()

        await query.edit_message_text("Передача отклонена.", reply_markup=main_menu_keyboard())

# Основная функция
def main():
    setup_database()

    # Используйте ваш реальный токен бота
    application = ApplicationBuilder().token('8009447746:AAGyLPQsTon9idDk5A9iDXZr8f3E19BqA34').build()

    # Обработчик команды /start
    application.add_handler(CommandHandler("start", start))

    # Обработчик нажатия кнопок
    application.add_handler(CallbackQueryHandler(main_menu_callback))

    # Обработчик текстовых сообщений
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    # Обработчик ошибок
    application.add_error_handler(error_handler)

    # Запуск бота
    application.run_polling()

if __name__ == '__main__':
    main()
