import logging
from typing import List

from aiogram import types, Dispatcher
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import StatesGroup, State
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from bot.api.bonds import BondsService
from bot.core.logging import setup_logging
from bot.models.models import Bond
from bot.telegram.utils import MarkdownFormatter as Mf

setup_logging()
logger = logging.getLogger(__name__)


class GetBondsStates(StatesGroup):
    introduce_step = State()
    next_item_step = State()


next_keyboard = InlineKeyboardMarkup(row_width=1)


def message_header(count_items: int, current_item_num: int) -> str:
    return Mf.italic(f'{current_item_num} из {count_items}.') + '\n\n'


def message_body(bond: Bond) -> str:
    msg_body = f"ISIN: {bond.isin}\n" \
               f"Название: {bond.name}\n" \
               f"Дата офферты/погашения: {bond.expiredDate.date()}\n" \
               f"Цена в % от номинала: {bond.price}%\n" \
               f"Размер купона: {bond.couponPercent}%\n" \
               f"Периодичность купона: {bond.couponPeriod}\n" \
               f"Эффективная доходность: {bond.effectiveYield}%"
    return msg_body


def full_message(count_items: int, current_item_num: int, item: Bond) -> str:
    return message_header(count_items, current_item_num) + message_body(item)


async def bonds_introduce(message: types.Message, state: FSMContext):
    bonds = BondsService()
    bonds_list = await bonds.list()
    count_items = len(bonds_list)
    better_choice, other = bonds.pop_better(bonds_list).values()
    better_choice: Bond
    other: List[Bond]
    msg = full_message(count_items, count_items, better_choice)
    await message.answer(msg,
                         parse_mode="Markdown",
                         reply_markup=next_keyboard
                         .row(InlineKeyboardButton("Следующую", callback_data=message.message_id)))
    await state.update_data(bonds_list=other, count_items=count_items)
    await GetBondsStates.next_item_step.set()


async def bonds_next_item(callback_query: types.CallbackQuery, state: FSMContext):
    storage = await state.get_data()
    logging.debug(f'Getting data from storage in bonds: {storage.items()}')
    bonds_list = storage['bonds_list']
    count_items = int(storage['count_items'])
    current_item_num = len(bonds_list)
    if len(bonds_list) > 0:
        service = BondsService()
        better_choice, other = service.pop_better(bonds_list).values()
        await state.update_data(bonds_list=other)
        msg = full_message(count_items, current_item_num, better_choice)
        await callback_query.message.answer(msg, parse_mode="Markdown")  # , reply_markup=next_keyboard
    else:
        msg = f"{Mf.bold('На сегодня это весь список подобранных облигаций!')}\n" \
              f"Список обновляется каждый день."
        await callback_query.message.answer(msg, parse_mode="Markdown")
        await state.finish()


def register_handlers_bonds(dp: Dispatcher):
    """
    Регистрация хэндлеров \n
    See example: https://mastergroosha.github.io/telegram-tutorial-2/fsm/

    :param dp: Dispatcher
    :return: None
    """
    dp.register_message_handler(bonds_introduce, commands="bonds", state="*")
    dp.register_callback_query_handler(bonds_next_item, state=GetBondsStates.next_item_step)
