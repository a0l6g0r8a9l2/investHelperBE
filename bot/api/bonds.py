import asyncio
import json
import logging
from typing import List, Union, Dict, Optional

import httpx
from httpx import Response
from pydantic import ValidationError

from bot.api.base import ApiRequest
from bot.core.exceptions import MakeRequestError
from bot.core.logging import setup_logging
from bot.models.models import Bond

setup_logging()
logger = logging.getLogger(__name__)


class BondsService(ApiRequest):
    base_path = '/bonds'

    async def raw_bonds_list(self) -> Response:
        async with httpx.AsyncClient() as client:
            response = await client.get(self.url, headers=self.headers)
            logging.debug(
                f'Log from {self.__class__.__name__}: url: {self.url}, status: {response.status_code}')
            if response.status_code != 200:
                raise MakeRequestError(f'HTTP error with: {response.status_code}')
            else:
                return response

    async def list(self) -> List[Bond]:
        response = await self.raw_bonds_list()
        obj_list: list = json.loads(response.text)
        bonds_list = []
        for item in obj_list:
            try:
                bond = Bond(**item)
            except ValidationError as ve:
                logging.error(f'Passing obj: {item}. Error: {ve}')
            else:
                bonds_list.append(bond)
        logging.debug(f'Bonds list contain {len(bonds_list)} items')
        return bonds_list

    @staticmethod
    def pop_better(bonds_list: List[Bond]) -> Dict[str, Union[Bond, List[Bond]]]:
        better_yield = max([bond.effectiveYield for bond in bonds_list])
        for num, bond in enumerate(bonds_list):
            if bond.effectiveYield == better_yield:
                result = {"better_choice": bonds_list.pop(num), "other_list": bonds_list}
                logging.debug(f'Better choice: {result}')
                return result
