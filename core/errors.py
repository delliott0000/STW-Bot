from aiohttp import ClientResponse


class STWException(Exception):
    pass


class HTTPException(STWException):

    def __init__(
            self,
            response: ClientResponse,
            data: dict
    ):
        self.response: ClientResponse = response
        self.status: int = response.status

        self.error_code = data.get('errorCode')
        self.error_message = data.get('errorMessage')

    def __str__(self):
        return f'{self.error_code}: {self.error_message}'


class BadRequest(HTTPException):
    pass


class Unauthorized(HTTPException):
    pass


class Forbidden(HTTPException):
    pass


class NotFound(HTTPException):
    pass


class TooManyRequests(HTTPException):
    pass


class ServerError(HTTPException):
    pass


class UnknownItem(STWException):

    def __init__(
            self,
            item_id: str,
            template_id: str
    ):
        self.message = f'Unknown item!\nItem ID: `{item_id}`\nTemplate ID: `{template_id}`'

    def __str__(
            self
    ):
        return self.message


class BadItemData(STWException):

    def __init__(
            self,
            item_id: str,
            template_id: str,
            attrs: dict
    ):
        self.message = f'Malformed item!\nItem ID: `{item_id}`\nTemplate ID: `{template_id}`\nAttributes: `{attrs}`'

    def __str__(
            self
    ):
        return self.message
