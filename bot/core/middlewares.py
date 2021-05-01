"""Аутентификация — пропускаем сообщения только от одного Telegram аккаунта"""
from aiogram import types
from aiogram.dispatcher.handler import CancelHandler
from aiogram.dispatcher.middlewares import BaseMiddleware

from bot.telegram.utils import MarkdownFormatter


class AccessMiddleware(BaseMiddleware):
    def __init__(self, access_id: int):
        self.access_id = access_id
        super().__init__()

    async def on_process_message(self, message: types.Message, _):
        if int(message.from_user.id) != int(self.access_id):
            header = MarkdownFormatter.bold('Access Denied') + '\n'
            msg_body = 'This is beta bot. You can request access by creating issue: ' \
                       'https://github.com/a0l6g0r8a9l2/investHelperBE/issues/new/choose'
            await message.answer(header + msg_body, parse_mode="Markdown")
            raise CancelHandler()
