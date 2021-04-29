import asyncio
import logging

from aiogram import types, Dispatcher
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import StatesGroup, State
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from bot.api.notification import NotificationService
from bot.api.stock import StockService
from bot.core.logging import setup_logging
from bot.models.models import StockPriceNotificationRqBot, StockPriceNotificationReadRs
from bot.telegram.utils import MarkdownFormatter, MarkdownMessageBuilder

setup_logging()
logger = logging.getLogger(__name__)

available_actions = ["Buy", "Sell"]

available_delay = {"m": ["10s", "30s", "1m"],
                   "h": ["5m", "15m", "30m"],
                   "d": ["1h", "3h", "6h"]}

available_end_notification = {"m": ["5m", "10m", "30m"],
                              "h": ["1h", "3h", "6h", "12h"],
                              "d": ["1d", "3d", "5d", "7d"]}

approve_options = ["Да", "Нет"]


def header(step: int) -> str:
    return MarkdownFormatter.italic(f'Шаг {step} из 7.') + '\n\n'


def full_message(step: int, msg_body: str) -> str:
    return header(step) + msg_body


class OrderNotification(StatesGroup):
    waiting_for_ticker = State()
    waiting_for_approve_stock = State()
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

    stocks = await StockService().find_stock_by_ticker(ticker=message.text.upper())
    logger.debug(f'Stocks: {stocks}')
    if stocks and len(stocks) > 0:
        current_stock = stocks.pop()
        logger.debug(f'Current stock: {current_stock}')
        msg_body = MarkdownMessageBuilder(current_stock).build_stock_find_message()
        logger.debug(f'Msg body: {msg_body}')
        await state.update_data(rest_stocks=stocks, ticker=message.text.upper(), current_stock=current_stock)
        await OrderNotification.waiting_for_approve_stock.set()
        approve_keyboard = InlineKeyboardMarkup(row_width=3)
        approve_keyboard.row(*[InlineKeyboardButton(i, callback_data=i) for i in approve_options])
        await message.answer(full_message(2, msg_body), parse_mode="Markdown",
                             reply_markup=approve_keyboard)
    else:
        await message.reply(f'По тикеру {message.text} ничего не найдено. Пожалуйста, поверьте привильность тикера.')


async def notify_waiting_for_approve_stock(callback_query: types.CallbackQuery, state: FSMContext):
    logger.debug(f'Log from notify_waiting_for_approve_stock: {callback_query.data}')
    if callback_query.data == "Нет":
        data = await state.get_data()
        stocks = data.get('rest_stocks')
        if stocks and len(stocks) > 0:
            current_stock = stocks.pop()
            msg_body = MarkdownMessageBuilder(current_stock).build_stock_find_message()
            approve_keyboard = InlineKeyboardMarkup(row_width=3)
            approve_keyboard.row(*[InlineKeyboardButton(i, callback_data=i) for i in approve_options])
            await callback_query.message.answer(full_message(3, msg_body), parse_mode="Markdown",
                                                reply_markup=approve_keyboard)
            await state.update_data(rest_stocks=stocks, current_stock=current_stock)
        else:
            await callback_query.message.reply(f'По тикеру {data.get("ticker")} больше ничего не найдено.')
    else:
        await OrderNotification.next()
        actions_keyboard = InlineKeyboardMarkup(row_width=3)
        actions_keyboard.row(*[InlineKeyboardButton(i, callback_data=i) for i in available_actions])
        msg_body = "Теперь выберите действие, при достижении цены:"
        await callback_query.message.answer(full_message(3, msg_body), parse_mode="Markdown",
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
    await state.update_data(targetPrice=message.text.lower())
    await OrderNotification.next()
    end_notification_keyboard = InlineKeyboardMarkup(row_width=3)
    for names in available_end_notification.values():
        end_notification_keyboard.row(*[InlineKeyboardButton(i, callback_data=i) for i in names])
    msg_body = "Теперь выберите как долго отслеживать цену (" + MarkdownFormatter.italic(
        "m - мин., h - часы, d - дни.") + "):"
    await message.answer(full_message(4, msg_body),
                         parse_mode="Markdown", reply_markup=end_notification_keyboard)


async def notify_waiting_for_end_notification(callback_query: types.CallbackQuery, state: FSMContext):
    logging.debug(f'Log from {notify_waiting_for_end_notification}: {callback_query.message.text}')
    await state.update_data(endNotification=callback_query.data)
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
        logging.debug(f'Log from notify_waiting_for_event: {message.text}')
        await state.update_data(event=message.text)
        data = await state.get_data()
        logging.debug(f'Getting data from storage in notify: {data.items()}')
        request_data = StockPriceNotificationRqBot(**data.get('current_stock').dict(),
                                                   action=data.get('action'),
                                                   targetPrice=data.get('targetPrice'),
                                                   endNotification=data.get('endNotification'),
                                                   delay=data.get('delay'),
                                                   event=data.get('event'))
        notification = await NotificationService(notification_user_data=request_data).create_notification()
        if notification:
            logging.debug(f'Log from notify_waiting_for_event, created notification: {notification}')
            notification = StockPriceNotificationReadRs(**notification)
            msg_body = MarkdownMessageBuilder(notification).build_notification_message()
            logging.debug(f'Log from notify_waiting_for_event, msg: {msg_body}')
            await message.answer(text=msg_body, parse_mode="Markdown")
        logging.debug(f'Log from notify_waiting_for_event, request_data: {request_data}')
    except Exception as err:
        err_msg = MarkdownFormatter.bold('Не удалось создать шедулер.') + '\n' + 'Пожалуйста, попробуйте позднее...'
        await message.answer(err_msg)
        logging.error(f'Error for {message.from_user.id} with args: {err.args}')
    finally:
        await state.finish()


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
    dp.register_callback_query_handler(notify_waiting_for_approve_stock,
                                       lambda c: c.data and c.data in [i for i in approve_options],
                                       state=OrderNotification.waiting_for_approve_stock
                                       )
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
