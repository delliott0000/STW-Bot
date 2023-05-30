from base64 import b64encode
from time import time
import logging

from aiohttp import ClientSession, ClientResponse, ClientResponseError
from dateutil import parser

from core.errors import STWException, HTTPException, BadRequest, Unauthorized, Forbidden, NotFound, ServerError, \
    TooManyRequests
from core.accounts import PartialEpicAccount, FullEpicAccount


async def to_dict(response: ClientResponse) -> dict:
    try:
        return await response.json()
    except ClientResponseError:
        # This should only happen if we receive an empty response from Epic Games.
        # In which case it is appropriate to return an empty dictionary.
        # This will need to be re-worked to be compatible with other APIs.
        return {}


class AuthSession:

    """
    Represents an Auth session between our client and Epic Games.

    HTTP requests that require an access token should be made using the `access_request` method.

    That way we can neatly handle `Unauthorized` exceptions by attempting to renew the session and retrying.
    """

    def __init__(
            self,
            client,
            discord_id: int,
            data: dict
    ):
        self.client: EpicGamesClient = client
        self.discord_id = discord_id

        self.epic_id = self.access_token = self.refresh_token = self.access_expires_at = self.refresh_expires_at = None
        self.renew_data(data)

        self._cached_full_account = None
        self._cached_full_update_time = 0

        # True if session was killed via HTTP
        self._expired = False

    def renew_data(self, new_data: dict) -> None:
        self.epic_id: str = new_data.get('account_id')
        self.access_token: str = new_data.get('access_token')
        self.refresh_token: str = new_data.get('refresh_token')
        self.access_expires_at: float = self._dt_to_float(new_data.get('expires_at'))
        self.refresh_expires_at: float = self._dt_to_float(new_data.get('refresh_expires_at'))

    @property
    def is_active(self) -> bool:
        return (not self._expired) and self.access_expires_at > time()

    @property
    def is_expired(self) -> bool:
        return self._expired or self.refresh_expires_at < time()

    @staticmethod
    def _dt_to_float(dt: str) -> float:
        return parser.parse(dt).timestamp()

    async def renew(self) -> None:
        # Do nothing if the access token is already active
        if self.is_active is True:
            return

        response = await self.client.renew_token(self.refresh_token)
        self.renew_data(response)

    async def access_request(
            self,
            method: str,
            url: str,
            retry: bool = False,
            **kwargs
    ) -> dict:
        headers = kwargs.get('headers') or {'Authorization': f'bearer {self.access_token}'}

        try:
            return await self.client.request(
                method,
                url,
                headers=headers,
                **kwargs
            )

        except Unauthorized as unauthorized_error:

            if retry is True or self.is_expired is True:
                raise unauthorized_error

            await self.renew()
            return await self.access_request(
                method,
                url,
                retry=True,
                headers=headers,
                **kwargs
            )

    async def kill(self) -> None:
        await self.access_request(
            'delete',
            self.client.kill_token_url + f'/{self.access_token}'
        )
        self._expired = True

    async def get_own_account(self) -> FullEpicAccount:
        if self._cached_full_account is None or self._cached_full_update_time < time():
            data = await self.access_request(
                'get',
                self.client.account_requests_url.format(self.epic_id)
            )
            self._cached_full_account = FullEpicAccount(self, data)
            self._cached_full_update_time = time() + 1800
        return self._cached_full_account

    async def get_own_partial(self) -> PartialEpicAccount:
        return await self.get_other_account(epic_id=self.epic_id)

    async def get_own_friend_data(self) -> dict:
        return await self.access_request(
            'get',
            self.client.friends_requests_url.format(f'{self.epic_id}/summary')
        )

    async def get_own_externals(self) -> dict:
        return await self.access_request(
            'get',
            self.client.account_requests_url.format(self.epic_id) + '/externalAuths'
        )

    async def get_other_account(
            self,
            epic_id: str = None,
            display: str = None
    ) -> PartialEpicAccount:
        if epic_id is None and display is None:
            raise STWException('An Epic ID or display name is required.')

        url_prefix = 'displayName/' if epic_id is None else ''

        data = await self.access_request(
            'get',
            self.client.account_requests_url.format(url_prefix + (epic_id or display))
        )
        return PartialEpicAccount(self, data)

    async def profile_request(
            self,
            method: str = 'post',
            epic_id: str = None,
            route: str = 'public',
            operation: str = 'QueryPublicProfile',
            profile_id: str = 'campaign',
            json: dict = None
    ) -> dict:
        if epic_id is None:
            epic_id = self.epic_id
        if json is None:
            json = {}

        return await self.access_request(
            method,
            self.client.profile_requests_url.format(epic_id, route, operation, profile_id),
            json=json
        )


class AsyncRequestsClient:

    """
    This is a simple class for making generic HTTP requests asynchronously.

    This is intended to act as a parent class for specialised client subclasses to maintain flexibility.

    Each subclass of this should only need to be instantiated once during runtime.

    Ideally, they should also share the same `ClientSession` object as each other.
    """

    def __init__(
            self,
            session: ClientSession
    ):
        self.session: ClientSession = session

    async def request(
            self,
            method: str,
            url: str,
            **kwargs
    ) -> dict:
        async with self.session.request(
                method,
                url,
                **kwargs
        ) as response:
            data = await to_dict(response)

            logging.info(f'({response.status}) {method.upper() + "       "[:7 - len(method)]} {url}')

            # Return our data if the HTTP request was successful
            if response.status < 300:
                return data

            # Check status code, so we know which HTTP exception to raise
            elif response.status == 400:
                raise BadRequest(response, data)
            elif response.status == 401:
                raise Unauthorized(response, data)
            elif response.status == 403:
                raise Forbidden(response, data)
            elif response.status == 404:
                raise NotFound(response, data)
            elif response.status == 429:
                raise TooManyRequests(response, data)
            elif response.status >= 500:
                raise ServerError(response, data)

            # Raise generic HTTPException if all previous status codes have been exhausted
            raise HTTPException(response, data)


class EpicGamesClient(AsyncRequestsClient):

    """
    Subclass of `AsyncRequestsClient` made specifically for interacting with Epic Games' API services.

    Most requests require an access token, which should be obtained by calling `create_auth_session`.

    This will return an instance of `AuthSession`, from which the `access_request` method can be called.
    """

    def __init__(
            self,
            session: ClientSession
    ):
        super().__init__(session)

        client = 'ec684b8c687f479fadea3cb2ad83f5c6'
        secret = 'e1f31c211f28413186262d37a13fc84d'

        # Client ID:Secret for the Fortnite PC game client, encoded in base64
        # Needed to exchange an authorization code for an access token
        self.secret = b64encode(f'{client}:{secret}'.encode()).decode()

        # Base URLs for various Epic Games online services.
        self.base_epic_url = 'https://account-public-service-prod.ol.epicgames.com/account/api'
        self.base_frds_url = 'https://friends-public-service-prod.ol.epicgames.com/friends/api/v1'
        self.base_fort_url = 'https://fortnite-public-service-prod11.ol.epicgames.com/fortnite/api'

        self.user_auth_url = f'https://www.epicgames.com/id/api/redirect?clientId={client}&responseType=code'
        self.auth_exchange_url = self.base_epic_url + '/oauth/token'
        self.kill_token_url = self.base_epic_url + '/oauth/sessions/kill'

        self.account_requests_url = self.base_epic_url + '/public/account/{0}'
        self.friends_requests_url = self.base_frds_url + '/{0}'
        self.profile_requests_url = self.base_fort_url + '/game/v2/profile/{0}/{1}/{2}?profileId={3}'

    async def create_auth_session(
            self,
            auth_code: str,
            discord_id: int
    ) -> AuthSession:
        response = await self.request(
            'post',
            self.auth_exchange_url,
            headers={
                'Content-Type':
                    'application/x-www-form-urlencoded',
                'Authorization':
                    f'basic {self.secret}'
            },
            data={
                'grant_type':
                    'authorization_code',
                'code':
                    auth_code
            }
        )
        return AuthSession(self, discord_id, response)

    async def renew_token(
            self,
            refresh_token: str
    ) -> dict:
        return await self.request(
            'post',
            self.auth_exchange_url,
            headers={
                'Content-Type':
                    'application/x-www-form-urlencoded',
                'Authorization':
                    f'basic {self.secret}'
            },
            data={
                'grant_type':
                    'refresh_token',
                'refresh_token':
                    refresh_token
            }
        )
