import asyncio
import logging

import httpx
from aiogram import types, Dispatcher
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import StatesGroup, State
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from bot.core.exceptions import MakeRequestError
from bot.api.notification import NotificationService

available_actions = ["Buy", "Sell"]

available_delay = {"m": ["10s", "30s", "1m"],
                   "h": ["5m", "15m", "30m"],
                   "d": ["1h", "3h", "6h"]}

available_end_notification = {"m": ["5m", "10m", "30m"],
                              "h": ["1h", "3h", "6h", "12h"],
                              "d": ["1d", "3d", "5d", "7d"]}


class OrderNotification(StatesGroup):
    waiting_for_ticker = State()
    waiting_for_action = State()
    waiting_for_target_price = State()
    waiting_for_end_notification = State()
    waiting_for_delay = State()
    waiting_for_event = State()


async def notify_introduce(message: types.Message):
    await message.answer("Введите TICKER акции (_например, MOEX_):", parse_mode="Markdown")
    logging.debug(f'Log from {notify_introduce}: {message.text}')
    await OrderNotification.waiting_for_ticker.set()


async def notify_waiting_for_ticker(message: types.Message, state: FSMContext):
    logging.debug(f'Log from {notify_waiting_for_ticker} {message.text}')
    if not message.text.lower():
        await message.reply("Пожалуйста, ведите TICKER акции (_например, SBER_):")
        return
    await state.update_data(ticker=message.text)
    await OrderNotification.next()
    actions_keyboard = InlineKeyboardMarkup(row_width=3)
    actions_keyboard.row(*[InlineKeyboardButton(i, callback_data=i) for i in available_actions])
    await message.answer("Теперь выберите действие, при достижении цены:", parse_mode="Markdown",
                         reply_markup=actions_keyboard)


async def notify_waiting_for_action(callback_query: types.CallbackQuery, state: FSMContext):
    logging.debug(f'Log from {notify_waiting_for_action}: {callback_query.message}')
    await state.update_data(action=callback_query.data)
    await OrderNotification.next()
    logging.debug(f'Log from {notify_waiting_for_action}: {callback_query.message.text}')
    # await callback_query.answer(callback_query.id)
    await callback_query.message.answer("Теперь выберите ожидаемую цену (_например, 200.5_):", parse_mode="Markdown")


async def notify_waiting_for_target_price(message: types.Message, state: FSMContext):
    logging.debug(f'Log from {notify_waiting_for_target_price}: {message.text}')
    if not message.text:
        await message.reply("Пожалуйста, введите ожидаемую цену (_например, 200.5_):", parse_mode="Markdown")
        return
    await state.update_data(price=message.text.lower())
    await OrderNotification.next()
    end_notification_keyboard = InlineKeyboardMarkup(row_width=3)
    for names in available_end_notification.values():
        end_notification_keyboard.row(*[InlineKeyboardButton(i, callback_data=i) for i in names])
    await message.answer("Теперь выберите как долго отслеживать цену (_m - мин., h - часы, d - дни., _):",
                         parse_mode="Markdown", reply_markup=end_notification_keyboard)


async def notify_waiting_for_end_notification(callback_query: types.CallbackQuery, state: FSMContext):
    logging.debug(f'Log from {notify_waiting_for_end_notification}: {callback_query.message.text}')
    await state.update_data(end_notification=callback_query.data)
    await OrderNotification.next()
    logging.debug(f'Log from {notify_waiting_for_end_notification}: {callback_query.message.text}')
    delay_keyboard = InlineKeyboardMarkup(row_width=3)
    delay_keyboard.row(*[InlineKeyboardButton(i, callback_data=i)
                         for i in available_delay.get(callback_query.data[-1])])
    await callback_query.message.answer("Теперь выберите с какой периодчностью отслеживать цену "
                                        "(_s - сек., m - мин., h - часы_):",
                                        parse_mode="Markdown", reply_markup=delay_keyboard)


async def notify_waiting_for_delay(callback_query: types.CallbackQuery, state: FSMContext):
    logging.debug(f'Log from {notify_waiting_for_delay}: {callback_query.data}')
    await state.update_data(delay=callback_query.data)
    await OrderNotification.next()
    await callback_query.message.answer("Можете ввести описание события, которое произойдет "
                                        "по достижению цены "
                                        "(_Например: Цена достигла месячного минимума!_):",
                                        parse_mode="Markdown")


async def notify_waiting_for_event(message: types.Message, state: FSMContext):
    try:
        logging.debug(f'Log from {notify_waiting_for_event}: {message.text}')
        await state.update_data(event=message.text)
        data = await state.get_data()
        data['chatId'] = message.from_user.id
        asyncio.create_task(NotificationService().create_notification(tg_notification=data))
        logging.debug(f'Log from {notify_waiting_for_event}: {data}')
    except (MakeRequestError, httpx.ConnectError) as err:
        await message.answer(f'Не удалось создать уведомление.\n'
                             f'Пожалуйста, попробуйте позднее...')
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
