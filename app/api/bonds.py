import logging
import sys

from fastapi import (APIRouter, status)
from starlette.responses import JSONResponse

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
    try:
        default_filter = BondFilter()
        bonds = Bonds(bonds_filter=default_filter)
        bonds_list = await bonds.list()
        return bonds_list
    except Exception as e_err:
        tb = sys.exc_info()[2]
        logging.error(e_err.args, e_err.with_traceback(tb))
        return JSONResponse(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            content={"message": "Internal Server Error"})
