from bot.models.models import NotificationMessage


class MarkdownFormatter:
    @classmethod
    def bold(cls, value: str) -> str:
        return f"*{value}*"

    @classmethod
    def italic(cls, value: str) -> str:
        return f"_{value}_\r"

    @classmethod
    def code(cls, value: str) -> str:
        return f"`{value}`"

    @classmethod
    def pre(cls, value: str) -> str:
        return f"```{value}```"

    @classmethod
    def underline(cls, value: str) -> str:
        return f"__{value}__"

    @classmethod
    def strikethrough(cls, value: str) -> str:
        return f"~{value}~"


class MarkdownMessageBuilder(MarkdownFormatter):

    def __init__(self, row_message):
        self.row_message = row_message

    def build(self) -> str:
        msg = ''
        if isinstance(self.row_message, NotificationMessage):
            message: NotificationMessage = self.row_message
            target_price = 'Целевая цена: ' + self.bold(f'{message.payload.targetPrice}')
            notify_id = 'ID: ' + self.bold(f'{message.payload.id}')
            current_price = 'Текущая цена: ' + self.bold(f'{message.payload.currentPrice}')
            asset_ticker = 'Инструмент с тикером ' + self.bold(f'{message.payload.ticker}')
            action = 'Действие: ' + self.bold(f'{message.payload.action}!')
            if message.payload.state == 'price_scheduling':
                title = self.bold(f'Шедулер создан!')
                msg = title + '\n' + asset_ticker + '\n' + notify_id + '\n' + target_price + '\n' + current_price
            elif message.payload.state == 'done':
                title = self.bold('Шедулер успешно отработал!')
                msg = title + '\n' + asset_ticker + '\n' + current_price + '\n' + target_price + '\n' + action
            elif message.payload.state == 'expired':
                title = self.bold('Время работы шедулера истекло!')
                msg = title + '\n' + notify_id + '\n' + asset_ticker + '\n' + current_price + '\n' + target_price
            elif message.payload.state == 'canceled':
                title = self.bold('Шедулер отменен!')
                msg = title + '\n' + notify_id + '\n' + asset_ticker + '\n' + current_price
        return msg
