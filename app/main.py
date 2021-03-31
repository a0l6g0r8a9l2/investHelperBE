import uvicorn
from fastapi import FastAPI
from starlette.responses import RedirectResponse

from app.core import settings
from app.core.logging import setup_logging
from app import api

tags_metadata = [
    {
        'name': 'bonds',
        'description': 'Получение списка отфильтрованных облигаций',
    },
    {
        'name': 'notifications',
        'description': 'Создание уведомления об изменении цены акции',
    },
]

app = FastAPI(title="InvestAssistance",
              description="This is API for InvestAssistance",
              version="0.2.1")

app.include_router(api.router)


@app.get("/", include_in_schema=False)
def docs_redirect():
    return RedirectResponse(f"{app.root_path}/docs")


if __name__ == '__main__':
    uvicorn.run(
        'app.main:app',
        host=settings.server_host,
        port=settings.server_port,
        reload=True,
        log_config=setup_logging(),
    )
