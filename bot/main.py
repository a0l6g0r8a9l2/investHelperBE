#!venv/bin/python
import asyncio
import logging

from aiogram import types, Dispatcher, Bot, executor
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from bot.core import config_data
from bot.core.logging import setup_logging
from bot.core.middlewares import AccessMiddleware
from bot.services.notification import NotificationService

setup_logging()
logger = logging.getLogger(__name__)

bot = Bot(token=config_data.get("TELEGRAM_API_TOKEN"))
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)
dp.middleware.setup(AccessMiddleware(config_data.get("TELEGRAM_ACCESS_ID")))


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


@dp.message_handler(commands="notify", state="*")
async def notify_introduce(message: types.Message):
    await message.answer("Введите TICKER акции (_например, MOEX_):", parse_mode="Markdown")
    logging.debug(f'Log from {notify_introduce}: {message.text}')
    await OrderNotification.waiting_for_ticker.set()


@dp.message_handler(state=OrderNotification.waiting_for_ticker,
                    content_types=types.ContentTypes.TEXT,
                    regexp='^[a-zA-Z]{1,5}$')
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


@dp.callback_query_handler(lambda c: c.data and c.data in [i for i in available_actions],
                           state=OrderNotification.waiting_for_action, )
async def notify_waiting_for_action(callback_query: types.CallbackQuery, state: FSMContext):
    logging.debug(f'Log from {notify_waiting_for_action}: {callback_query.message}')
    await state.update_data(action=callback_query.data)
    await OrderNotification.next()
    logging.debug(f'Log from {notify_waiting_for_action}: {callback_query.message.text}')
    await bot.answer_callback_query(callback_query.id)
    await callback_query.message.answer("Теперь выберите ожидаемую цену (_например, 200.5_):", parse_mode="Markdown")


@dp.message_handler(state=OrderNotification.waiting_for_target_price,
                    content_types=types.ContentTypes.TEXT,
                    regexp='^-?[0-9]+(?:\.[0-9]{1,6})?$')
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


@dp.callback_query_handler(lambda c: c.data and c.data in [j for _ in available_end_notification.values() for j in _],
                           state=OrderNotification.waiting_for_end_notification)
async def notify_waiting_for_end_notification(callback_query: types.CallbackQuery, state: FSMContext):
    logging.debug(f'Log from {notify_waiting_for_end_notification}: {callback_query.message.text}')
    await state.update_data(end_notification=callback_query.data)
    await OrderNotification.next()
    logging.debug(f'Log from {notify_waiting_for_end_notification}: {callback_query.message.text}')
    await bot.answer_callback_query(callback_query.id)
    delay_keyboard = InlineKeyboardMarkup(row_width=3)
    delay_keyboard.row(*[InlineKeyboardButton(i, callback_data=i)
                         for i in available_delay.get(callback_query.data[-1])])
    await callback_query.message.answer("Теперь выберите с какой периодчностью отслеживать цену "
                                        "(_s - сек., m - мин., h - часы_):",
                                        parse_mode="Markdown", reply_markup=delay_keyboard)


@dp.callback_query_handler(lambda c: c.data and c.data in [j for _ in available_delay.values() for j in _],
                           state=OrderNotification.waiting_for_delay)
async def notify_waiting_for_delay(callback_query: types.CallbackQuery, state: FSMContext):
    logging.debug(f'Log from {notify_waiting_for_delay}: {callback_query.data}')
    await state.update_data(delay=callback_query.data)
    await OrderNotification.next()
    await bot.answer_callback_query(callback_query.id)
    await bot.send_message(callback_query.from_user.id, "Можете ввести описание события, которое произойдет "
                                                        "по достижению цены "
                                                        "(_Например: Цена достигла месячного минимума!_):",
                           parse_mode="Markdown")


@dp.message_handler(state=OrderNotification.waiting_for_event, content_types=types.ContentTypes.TEXT)
async def notify_waiting_for_event(message: types.Message, state: FSMContext):
    logging.debug(f'Log from {notify_waiting_for_event}: {message.text}')
    await state.update_data(event=message.text)
    data = await state.get_data()
    data['chatId'] = message.from_user.id
    asyncio.create_task(NotificationService().create(tg_notification=data))
    logging.debug(f'Log from {notify_waiting_for_event}: {data}')


async def shutdown(dispatcher: Dispatcher):
    await dispatcher.storage.close()
    await dispatcher.storage.wait_closed()

# todo: add delete notification
# todo: add requirements.txt
# todo: add dockerfile

if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=False, on_shutdown=shutdown)
