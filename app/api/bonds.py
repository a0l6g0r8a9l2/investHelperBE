from fastapi import (APIRouter, status)

from app.models.models import BondsRs, BondFilter
from app.services.bonds import Bonds

router = APIRouter()


@router.get("/",
            response_model_exclude_none=True,
            status_code=status.HTTP_200_OK,
            response_model=BondsRs,
            response_model_exclude_unset=True,
            response_model_by_alias=False,
            tags=["bonds"])
async def get_bonds():
    default_filter = BondFilter()
    bonds = Bonds(bonds_filter=default_filter)
    bonds_list = await bonds.list()
    return bonds_list
