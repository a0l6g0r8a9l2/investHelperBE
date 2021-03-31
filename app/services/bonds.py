import logging
from abc import ABC, abstractmethod
from datetime import date, timedelta
from typing import List, Optional, Dict, Any

import apimoex
import pandas as pd
import requests
from fastapi import HTTPException
from pydantic import ValidationError
from starlette import status

from app.core.logging import setup_logging
from app.db.redis_pub import Redis
from app.models.models import BondFilter, BondsRs

# сетап конфиг и логгер
setup_logging()
logger = logging.getLogger(__name__)


class DataFetcher:
    """
    Базовый класс для получения данных из api MOEX ISS
    """

    @staticmethod
    def get_data_by_reference(request_url: str, arguments: dict, reference_name: str) -> pd.DataFrame:
        """
        Функция для получения данных по облигациям в разрезе справочника и режима торгов \n
        :param request_url: базовый урл
        :param arguments: аргументы запроса
        :param reference_name: код справчника. Например: securities, marketdata, marketdata_yields
        :return: фрэйм с данными по инстументу
        """
        with requests.Session() as session:
            iss = apimoex.ISSClient(session, request_url, arguments)
            ref_data = iss.get()
            df = pd.DataFrame(ref_data[reference_name])
            df.set_index('SECID', inplace=True)
            return df

    @staticmethod
    def fill_nan_rule(x: float, y: float):
        if x != x or x is None:  # nan check
            return y
        else:
            return x

    @staticmethod
    async def to_cache(json_data: str) -> Optional[str]:
        logging.debug(f'Called to_cache with json: {json_data}')
        redis = Redis()
        cache = await redis.save_cache(message=json_data)
        logging.debug(f'Saved to {cache}')
        return cache

    @staticmethod
    def to_json(data: pd.DataFrame) -> Optional[str]:
        data = data.reset_index()
        data.fillna(value=0, inplace=True)
        data.rename(columns={"SECID": "isin",
                             "SECNAME": "name",
                             "COUPONVALUE": "couponAmount",
                             "ACCRUEDINT": "accumulatedCouponYield",
                             "COUPONPERIOD": "couponPeriod",
                             "COUPONPERCENT": "couponPercent",
                             "PRICE": "price",
                             "NEXTCOUPON": "nextCouponDate",
                             "EXPIREDDATE": "expiredDate",
                             "YIELDTOOFFER": "yieldToOffer",
                             "EFFECTIVEYIELD": "effectiveYield"
                             }, inplace=True)
        data = data.to_json(orient="records", indent=4, date_format='iso')
        return data

    @staticmethod
    def to_dict(data: pd.DataFrame) -> List[dict]:
        data = data.reset_index()
        data.fillna(value=0, inplace=True)
        data.rename(columns={"SECID": "isin",
                             "SECNAME": "name",
                             "COUPONVALUE": "couponAmount",
                             "ACCRUEDINT": "accumulatedCouponYield",
                             "COUPONPERIOD": "couponPeriod",
                             "COUPONPERCENT": "couponPercent",
                             "PRICE": "price",
                             "NEXTCOUPON": "nextCouponDate",
                             "EXPIREDDATE": "expiredDate",
                             "YIELDTOOFFER": "yieldToOffer",
                             "EFFECTIVEYIELD": "effectiveYield"
                             }, inplace=True)
        data = data.to_dict(orient="records")
        return data


class BondsHistoryData(DataFetcher):
    """
    Класс для получения исторических данных
    """
    market = 'bonds'
    reference = 'history'
    history = ['SECID', 'NUMTRADES', 'VALUE']

    def __init__(self, bonds_filter: BondFilter):
        self.bonds_filter = bonds_filter or BondFilter()

    def enrich_history_data(self, aggregated_filtered_data: pd.DataFrame) -> pd.DataFrame:
        """
        Функция обогащает фрэйм историческими данными \n
        :param aggregated_filtered_data: предварительно отфильтрованный фрэйм с данными по облигациям
        :return: обогащенный историческими данными фрэйм
        """
        end = date.today()
        start = end - timedelta(days=self.bonds_filter.trade_history_period)
        aggregate_trades_history = pd.DataFrame()
        for index, row in aggregated_filtered_data.iterrows():
            arguments = {
                'iss.only': 'marketdata',
                f'history.columns': (','.join(self.history)),
                'from': start.strftime('%Y-%m-%d'),
                'till': end.strftime('%Y-%m-%d'),
            }
            url = f'http://iss.moex.com/iss/history/engines/stock/markets/{self.market}/boards/{row["BOARDID"]}' \
                  f'/securities/{index}.json'
            sec_history = self.get_data_by_reference(request_url=url,
                                                     arguments=arguments,
                                                     reference_name=self.reference)
            agr_row = sec_history.groupby(sec_history.index).sum()
            aggregate_trades_history = aggregate_trades_history.append(agr_row, verify_integrity=True)

        aggregated_filtered_data = aggregated_filtered_data.join(aggregate_trades_history)
        return aggregated_filtered_data

    def apply_filter(self, all_boards_data: pd.DataFrame) -> pd.DataFrame:
        """
        Функция накладывает фильтр по минимальному объему и кол-ву сделок с ценной бумагой \n
        :param all_boards_data: фрэйм с обогащенный историческими данными
        :return: итоговый фрэйм
        """
        filtered_df = all_boards_data[(all_boards_data.NUMTRADES > self.bonds_filter.min_trade_counts) &
                                      (all_boards_data.VALUE > self.bonds_filter.min_trade_volume)
                                      ]
        filtered_df = filtered_df[['SECNAME', 'COUPONVALUE', 'ACCRUEDINT', 'COUPONPERIOD', 'COUPONPERCENT',
                                   'NEXTCOUPON', 'PRICE', 'EXPIREDDATE', 'YIELDTOOFFER', 'EFFECTIVEYIELD']]
        filtered_df.sort_values(by=['PRICE', 'EFFECTIVEYIELD', 'COUPONPERCENT'], ascending=[True, False, False])
        return filtered_df


class BondsDataFetcher(DataFetcher):
    """
    Class for getting data from MOEX
    """
    market = 'bonds'
    references = ['securities', 'marketdata', 'marketdata_yields']
    securities = ['SECID', 'SECNAME', 'LOTSIZE', 'SHORTNAME', 'COUPONVALUE', 'ACCRUEDINT', 'PREVPRICE', 'COUPONPERIOD',
                  'FACEUNIT', 'BUYBACKPRICE', 'ISSUESIZEPLACED', 'LISTLEVEL', 'COUPONPERCENT', 'NEXTCOUPON',
                  'OFFERDATE', 'LOTVALUE', 'BOARDID', 'MATDATE']
    marketdata = ['SECID', 'LAST', 'DURATION', 'YIELDTOOFFER', 'YIELD']
    marketdata_yields = ['SECID', 'EFFECTIVEYIELD']

    def __init__(self, bonds_filter: BondFilter):
        self.bonds_filter = bonds_filter or BondFilter()

    def fetch_raw(self, board_codes: [List[str]]) -> pd.DataFrame:
        """
        Функция стороит дерево ссылок и извлекает по ним "сырые" данные \n
        :param board_codes: список режимов торгов для поиска
        :return: фрэйм с сырыми данными
        """
        logging.debug(f'Building reference tree..')
        fetch_tree = self.references_tree(board_codes=board_codes)
        logging.debug(f'Fetch data by reference tree..')
        fetched_data = self.get_data_by_reference_tree(fetch_tree)
        return fetched_data

    def apply_filter(self, all_boards_data: pd.DataFrame) -> pd.DataFrame:
        """
        Функция накладывает бизнес-фильтр на "сырые" данные и преобразует типы
        :param all_boards_data:
        :return:
        """
        logging.debug(f'Apply filter to raw data..')
        target_date = date.today() + timedelta(days=self.bonds_filter.period)

        all_boards_data['PRICE'] = all_boards_data.apply(lambda x: self.fill_nan_rule(x['LAST'], x['PREVPRICE']),
                                                         axis=1)
        all_boards_data['EXPIREDDATE'] = all_boards_data.apply(
            lambda x: self.fill_nan_rule(x['OFFERDATE'], x['MATDATE']),
            axis=1)

        offer_dates = pd.to_datetime(all_boards_data.EXPIREDDATE, errors='coerce')
        all_boards_data.EXPIREDDATE = offer_dates

        coupon_dates = pd.to_datetime(all_boards_data.NEXTCOUPON, errors='coerce')
        all_boards_data.NEXTCOUPON = coupon_dates

        filtered_df = all_boards_data[(all_boards_data.LISTLEVEL < 3) &
                                      (all_boards_data.COUPONPERCENT < self.bonds_filter.cb_key_rate * 2) &
                                      (all_boards_data.PRICE < self.bonds_filter.max_percent_price) &
                                      (all_boards_data.PRICE > self.bonds_filter.min_percent_price) &
                                      (all_boards_data.COUPONPERCENT > self.bonds_filter.cb_key_rate +
                                       self.bonds_filter.additional_rate) &
                                      (all_boards_data.YIELD > self.bonds_filter.cb_key_rate +
                                       self.bonds_filter.additional_rate) &
                                      (all_boards_data.EFFECTIVEYIELD > self.bonds_filter.cb_key_rate +
                                       self.bonds_filter.additional_rate) &
                                      (all_boards_data.EXPIREDDATE < pd.to_datetime(target_date, format='%Y-%m-%d'))
                                      ].sort_values('DURATION')
        return filtered_df

    def references_tree(self, board_codes: Optional[List[str]]) -> Dict[str, Dict[str, Any]]:
        """
        Функция составляет словарь урлов и параметров запросов \n
        :param board_codes: список кодов режимов торгов. Например: ['TQCB', 'TQOB']
        :return: словарь с ключами - параметрами запроса и значениями - списком требуемых полей
        для get_data_by_reference
        """
        boards_with_references = {}.fromkeys(board_codes, {}.fromkeys(self.references))
        for i in boards_with_references.values():
            i['securities'] = self.securities
            i['marketdata'] = self.marketdata
            i['marketdata_yields'] = self.marketdata_yields
        return boards_with_references

    def get_data_by_reference_tree(self, references_tree: Dict[str, Dict[str, Any]]) -> pd.DataFrame:
        """
        Функция получает собирает данные по каждому из режимов торгов и справочников\n
        :param references_tree: словарь с ключами - параметрами запроса и значениями - списком требуемых полей
        :return: агрегированный фрэйм с данными по всем режимам торгов и справочникам
        """
        all_board_data = pd.DataFrame()
        for k, v in references_tree.items():
            board_data = pd.DataFrame()
            for i, j in v.items():
                arguments = {f'{i}.columns': (','.join(j))}
                request_url = (f'https://iss.moex.com/iss/engines/stock/'
                               f'markets/{self.market}/boards/{k}/securities.json')
                ref_data = self.get_data_by_reference(request_url, arguments, i)
                if board_data.empty:
                    board_data = ref_data
                else:
                    board_data = board_data.join(ref_data, rsuffix=f'_{i}')
            if all_board_data.empty:
                all_board_data = board_data
            else:
                all_board_data = all_board_data.combine_first(board_data)
        return all_board_data


class GetAsset(ABC):
    """
    Abstract method for getting asset list from MOEX
    https://iss.moex.com/iss
    """

    @abstractmethod
    def list(self) -> Optional[List[Dict]]:
        pass


class Bonds(GetAsset):
    """
    Класс для получения списка облигаций с применением фильтра
    """

    def __init__(self, bonds_filter: BondFilter = BondFilter()):
        self.bonds_filter = bonds_filter
        self.data_fetcher = BondsDataFetcher(bonds_filter=self.bonds_filter)
        self.history_data = BondsHistoryData(bonds_filter=self.bonds_filter)

    async def list(self) -> BondsRs:
        try:
            redis = Redis()
            cached_data = await redis.get_cached()
            if cached_data:
                logging.debug(f'Returning data from cache..')
                model = BondsRs.parse_raw(cached_data)
                logging.debug(f'Model {model}')
                return model
            else:
                logging.debug(f'No cache data. Getting from exchange..')
                raw_data = self.data_fetcher.fetch_raw(self.bonds_filter.boards)
                logging.debug(f'Got row data')
                pre_filtered_data = self.data_fetcher.apply_filter(raw_data)
                logging.debug(f'Apply first filter')
                enriched_history_data = self.history_data.enrich_history_data(pre_filtered_data)
                logging.debug(f'Enrich history data')
                filtered_data = self.history_data.apply_filter(enriched_history_data)
                logging.debug(f'Apply second filter')
                data_to_model = self.data_fetcher.to_dict(filtered_data)
                model = BondsRs.parse_obj(data_to_model)
                data_to_cache = model.json()
                logging.debug(f'Json data is: {data_to_cache}')
                cache_key = await self.data_fetcher.to_cache(data_to_cache)
                logging.debug(f'Data has been cached to {cache_key}')
                return model
        except (ValueError, ValidationError) as e:
            raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR)
        except Exception as err:
            logging.error(err.args)
