import asyncio
import logging

import httpx
from aiogram import types, Dispatcher
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import StatesGroup, State
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from bot.core.exceptions import MakeRequestError
from bot.api.notification import NotificationService
from bot.telegram.utils import MarkdownFormatter

available_actions = ["Buy", "Sell"]

available_delay = {"m": ["10s", "30s", "1m"],
                   "h": ["5m", "15m", "30m"],
                   "d": ["1h", "3h", "6h"]}

available_end_notification = {"m": ["5m", "10m", "30m"],
                              "h": ["1h", "3h", "6h", "12h"],
                              "d": ["1d", "3d", "5d", "7d"]}


def header(step: int) -> str:
    return MarkdownFormatter.italic(f'Шаг {step} из 6..') + '\n\n'


def full_message(step: int, msg_body: str) -> str:
    return header(step) + msg_body


class OrderNotification(StatesGroup):
    waiting_for_ticker = State()
    waiting_for_action = State()
    waiting_for_target_price = State()
    waiting_for_end_notification = State()
    waiting_for_delay = State()
    waiting_for_event = State()


async def notify_introduce(message: types.Message):
    msg_body = "Введите TICKER акции (" + MarkdownFormatter.italic("например, MOEX") + "):"
    await message.answer(full_message(1, msg_body), parse_mode="Markdown")
    logging.debug(f'Log from {notify_introduce}: {message.text}')
    await OrderNotification.waiting_for_ticker.set()


async def notify_waiting_for_ticker(message: types.Message, state: FSMContext):
    logging.debug(f'Log from {notify_waiting_for_ticker} {message.text}')
    if not message.text.lower():
        msg_body = "Введите TICKER акции (" + MarkdownFormatter.italic("например, SBER") + "):"
        await message.reply(full_message(1, msg_body))
        return
    await state.update_data(ticker=message.text)
    await OrderNotification.next()
    actions_keyboard = InlineKeyboardMarkup(row_width=3)
    actions_keyboard.row(*[InlineKeyboardButton(i, callback_data=i) for i in available_actions])
    msg_body = "Теперь выберите действие, при достижении цены:"
    await message.answer(full_message(2, msg_body), parse_mode="Markdown",
                         reply_markup=actions_keyboard)


async def notify_waiting_for_action(callback_query: types.CallbackQuery, state: FSMContext):
    logging.debug(f'Log from {notify_waiting_for_action}: {callback_query.message}')
    await state.update_data(action=callback_query.data)
    await OrderNotification.next()
    logging.debug(f'Log from {notify_waiting_for_action}: {callback_query.message.text}')
    msg_body = "Теперь выберите ожидаемую цену (" + MarkdownFormatter.italic("например, 200.5") + "):"
    await callback_query.message.answer(full_message(3, msg_body), parse_mode="Markdown")


async def notify_waiting_for_target_price(message: types.Message, state: FSMContext):
    logging.debug(f'Log from {notify_waiting_for_target_price}: {message.text}')
    if not message.text:
        msg_body = "Теперь выберите ожидаемую цену (" + MarkdownFormatter.italic("например, 200.5") + "):"
        await message.reply(full_message(3, msg_body), parse_mode="Markdown")
        return
    await state.update_data(price=message.text.lower())
    await OrderNotification.next()
    end_notification_keyboard = InlineKeyboardMarkup(row_width=3)
    for names in available_end_notification.values():
        end_notification_keyboard.row(*[InlineKeyboardButton(i, callback_data=i) for i in names])
    msg_body = "Теперь выберите как долго отслеживать цену (" + MarkdownFormatter.italic("m - мин., h - часы, d - дни.") + "):"
    await message.answer(full_message(4, msg_body),
                         parse_mode="Markdown", reply_markup=end_notification_keyboard)


async def notify_waiting_for_end_notification(callback_query: types.CallbackQuery, state: FSMContext):
    logging.debug(f'Log from {notify_waiting_for_end_notification}: {callback_query.message.text}')
    await state.update_data(end_notification=callback_query.data)
    await OrderNotification.next()
    logging.debug(f'Log from {notify_waiting_for_end_notification}: {callback_query.message.text}')
    delay_keyboard = InlineKeyboardMarkup(row_width=3)
    delay_keyboard.row(*[InlineKeyboardButton(i, callback_data=i)
                         for i in available_delay.get(callback_query.data[-1])])
    msg_body = "Теперь выберите с какой периодчностью отслеживать цену (" + \
               MarkdownFormatter.italic("s - сек., m - мин., h - часы") + "):"
    await callback_query.message.answer(full_message(5, msg_body),
                                        parse_mode="Markdown", reply_markup=delay_keyboard)


async def notify_waiting_for_delay(callback_query: types.CallbackQuery, state: FSMContext):
    logging.debug(f'Log from {notify_waiting_for_delay}: {callback_query.data}')
    msg_body = "Можете ввести описание события, которое произойдет по достижению цены (" + \
               MarkdownFormatter.italic("Например: Цена достигла месячного минимума!") + "):"
    await state.update_data(delay=callback_query.data)
    await OrderNotification.next()
    await callback_query.message.answer(full_message(6, msg_body),
                                        parse_mode="Markdown")


async def notify_waiting_for_event(message: types.Message, state: FSMContext):
    try:
        logging.debug(f'Log from {notify_waiting_for_event}: {message.text}')
        await state.update_data(event=message.text)
        data = await state.get_data()
        data['chatId'] = message.from_user.id
        asyncio.create_task(NotificationService().create_notification(tg_notification=data))
        logging.debug(f'Log from {notify_waiting_for_event}: {data}')
    except Exception as err:
        err_msg = MarkdownFormatter.bold("Не удалось создать шедулер.") + '\n' + 'Пожалуйста, попробуйте позднее...'
        await message.answer(err_msg)
        logging.error(f'Error for {message.from_user.id} with args: {err.args}')


def register_handlers_notify(dp: Dispatcher):
    """
    Регистрация хэндлеров \n
    See example: https://mastergroosha.github.io/telegram-tutorial-2/fsm/

    :param dp: Dispatcher
    :return: None
    """
    dp.register_message_handler(notify_introduce, commands="notify", state="*")
    dp.register_message_handler(notify_waiting_for_ticker, state=OrderNotification.waiting_for_ticker,
                                content_types=types.ContentTypes.TEXT,
                                regexp='^[a-zA-Z]{1,5}$')
    dp.register_callback_query_handler(notify_waiting_for_action,
                                       lambda c: c.data and c.data in [i for i in available_actions],
                                       state=OrderNotification.waiting_for_action)
    dp.register_message_handler(notify_waiting_for_target_price, state=OrderNotification.waiting_for_target_price,
                                content_types=types.ContentTypes.TEXT,
                                regexp='^-?[0-9]+(?:\.[0-9]{1,6})?$')
    dp.register_callback_query_handler(notify_waiting_for_end_notification,
                                       lambda c: c.data and c.data in [j for _ in available_end_notification.values()
                                                                       for j in _],
                                       state=OrderNotification.waiting_for_end_notification)
    dp.register_callback_query_handler(notify_waiting_for_delay,
                                       lambda c: c.data and c.data in [j for _ in available_delay.values() for j in _],
                                       state=OrderNotification.waiting_for_delay)
    dp.register_message_handler(notify_waiting_for_event, state=OrderNotification.waiting_for_event,
                                content_types=types.ContentTypes.TEXT)
