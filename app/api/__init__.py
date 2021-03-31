from fastapi import APIRouter

from . import (
    bonds,
    notifications,
)

router = APIRouter()
router.include_router(bonds.router,
                      prefix='/bonds',
                      tags=['bonds'], )
router.include_router(notifications.router,
                      prefix='/notification',
                      tags=['notification'], )
