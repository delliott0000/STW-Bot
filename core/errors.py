from aiohttp import ClientResponse


class STWException(Exception):

    """
    Base exception class for all STW-related errors.
    """


class HTTPException(STWException):

    """
    HTTP exception base.

    When an HTTP request returns a status code 3xx/4xx/5xx, a subclass of `HTTPException` is raised.

    Each subclass corresponds to a specific HTTP status code.

    If the status code does not correspond to any subclass, a generic `HTTPException` is raised instead.
    """

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

    """
    Corresponds to the `400 Bad Request` status code.
    """


class Unauthorized(HTTPException):

    """
    Corresponds to the `401 Unauthorized` status code.
    """


class Forbidden(HTTPException):

    """
    Corresponds to the `403 Forbidden` status code.
    """


class NotFound(HTTPException):

    """
    Corresponds to the `404 Not Found` status code.
    """


class TooManyRequests(HTTPException):

    """
    Corresponds to the `429 Too Many Requests` status code.

    Note: Epic Games' API service may sometimes return a 403 code in place of a 429.
    """


class ServerError(HTTPException):

    """
    Raised when any `5xx` HTTP status code occurs.
    """


class UnknownItem(STWException):

    """
    Raised when attempting to instantiate a fortnite object with an unknown template ID.
    """

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

    """
    Raised when attempting to instantiate a fortnite object with invalid/malformed attribute data.
    """

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
