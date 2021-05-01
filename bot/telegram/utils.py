from bot.models.models import StockPriceNotificationReadRs, StockRs, Bond


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

    def build_notification_message(self) -> str:
        msg = ''
        if isinstance(self.row_message, StockPriceNotificationReadRs):
            message: StockPriceNotificationReadRs = self.row_message
            target_price = 'Целевая цена: ' + self.bold(f'{message.targetPrice}')
            notify_id = 'ID: ' + self.bold(f'{message.id}')
            current_price = 'Текущая цена: ' + self.bold(f'{message.currentPrice.value} '
                                                         f'{message.currentPrice.currency_symbol}')
            asset_ticker = 'Тикер: ' + self.bold(f'{message.ticker}')
            action = 'Действие: ' + self.bold(f'{message.action}!')
            if message.state == 'in_progress':
                title = f'Шедулер работает!' + '\n'
                msg = title + '\n' + notify_id + '\n' + asset_ticker + '\n' + target_price + '\n' + current_price
            elif message.state == 'done':
                title = 'Шедулер успешно отработал!' + '\n'
                msg = title + '\n' + asset_ticker + '\n' + current_price + '\n' + target_price + '\n' + action
            elif message.state == 'disabled':
                title = 'Шедулер отменен!' + '\n'
                msg = title + '\n' + notify_id + '\n' + asset_ticker + '\n' + current_price
            else:
                title = 'Шедулер создан!' + '\n'
                msg = title + '\n' + notify_id + '\n' + asset_ticker + '\n' + target_price + '\n' + current_price
        return msg

    def build_stock_find_message(self) -> str:
        msg = ''
        if isinstance(self.row_message, StockRs):
            message: StockRs = self.row_message
            name = self.bold(f'{message.shortName}')
            asset_ticker = 'Тикер ' + self.bold(f'{message.ticker}')
            price = 'Текущая цена: ' + self.bold(f'{message.price.value}{message.price.currency_symbol}')
            if not message.assetProfile:
                msg = name + '\n' + price + '\n' + asset_ticker
            else:
                industry = 'Отрасль: ' + self.bold(f'{message.assetProfile.industry}') + '\n'
                sector = 'Сектор: ' + self.bold(f'{message.assetProfile.sector}') + '\n'
                site = f'Сайт эмитента: {message.assetProfile.site}'
                msg = name + '\n' + industry + sector + price + '\n' + asset_ticker + '\n' + site
        return msg

    def build_bond_message_body(self) -> str:
        msg_body = ''
        if isinstance(self.row_message, Bond):
            bond: Bond = self.row_message
            msg_body = f"ISIN: {bond.isin}\n" \
                       f"Название: {bond.name}\n" \
                       f"Дата офферты/погашения: {bond.expiredDate.date()}\n" \
                       f"Цена в % от номинала: {bond.price}%\n" \
                       f"Размер купона: {bond.couponPercent}%\n" \
                       f"Периодичность купона: {bond.couponPeriod}\n" \
                       f"Эффективная доходность: {bond.effectiveYield}%"
        return msg_body
