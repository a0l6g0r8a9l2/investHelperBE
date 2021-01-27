import httpx


class PrepareRequestError(Exception):
    pass


class MakeRequestError(httpx.HTTPError):
    pass
