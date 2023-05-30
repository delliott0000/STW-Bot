import asyncio
from math import floor
from typing import Union, Optional

from dateutil import parser

from core.errors import UnknownItem, BadItemData
from core.fortnite import Schematic, Survivor, LeadSurvivor, SurvivorSquad


class ExternalConnection:

    """
    Represents an external account linked to an Epic Games account.

    Each user currently cannot view other users' external connections.

    This is probably due to an inconsistency in how we are requesting data from Epic Games.

    This is probably fixable, but it is not a priority.
    """

    def __init__(
            self,
            account,
            data: dict
    ):
        self.account: FullEpicAccount = account

        self.id = data.get('externalAuthId')
        self.display = data.get('externalDisplayName')
        self.type = data.get('type')
        self.added = floor(parser.parse(data.get('dateAdded')).timestamp())


class PartialEpicAccount:

    """
    Represents an Epic Games account as seen publicly by another user.

    The `auth_session` does not necessarily belong to the `PartialEpicAccount` itself.

    Rather, it is the AuthSession that was used to retrieve the `PartialEpicAccount`s data.
    """

    def __init__(
            self,
            auth_session,
            data: dict
    ):
        self.auth_session = auth_session

        self.id = data.get('id') or data.get('accountId')
        self.display = data.get('displayName')

    @staticmethod
    def _dt_to_int(dt: str) -> int:
        return floor(parser.parse(dt).timestamp())

    # Thanks Epic
    async def update(self):
        data = await self.auth_session.get_other_account(epic_id=self.id)
        self.display = data.display

    async def fort_data(self) -> dict:
        return await self.auth_session.profile_request(epic_id=self.id)

    async def icon_url(self) -> Optional[str]:
        data = await self.fort_data()

        try:
            items = data['profileChanges'][0]['profile']['items']
        except KeyError:
            return

        for item in items:
            if items[item]['templateId'].startswith('CosmeticLocker'):
                try:
                    character_id = items[item]['attributes']['locker_slots_data']['slots']['Character']['items'][0][16:]
                except KeyError:
                    continue

                # Getting from Fortnite-API instead because it's easier
                character_data = await self.auth_session.client.request(
                    'get',
                    f'https://fortnite-api.com/v2/cosmetics/br/{character_id}'
                )
                try:
                    return character_data['data']['images']['icon']
                except KeyError:
                    continue

    async def fort_items(self) -> dict:
        return (await self.fort_data())['profileChanges'][0]['profile']['items']

    async def schematics(self) -> list[Schematic]:
        items = await self.fort_items()
        schematics = []

        for item in items:

            if items[item]['templateId'].startswith('Schematic:sid'):
                try:
                    schematic = Schematic(self, item, items[item]['templateId'], items[item]['attributes'])
                except UnknownItem:
                    continue

                schematics.append(schematic)

        schematics.sort(key=lambda x: x.power_level, reverse=True)
        return schematics

    async def survivors(self) -> list[Union[Survivor, LeadSurvivor]]:
        items = await self.fort_items()
        survivors = []

        for item in items:

            try:
                if items[item]['templateId'].startswith('Worker:worker'):
                    survivor = Survivor(self, item, items[item]['templateId'], items[item]['attributes'])
                elif items[item]['templateId'].startswith('Worker:manager'):
                    survivor = LeadSurvivor(self, item, items[item]['templateId'], items[item]['attributes'])
                else:
                    continue
            except (UnknownItem, BadItemData):
                continue

            survivors.append(survivor)

        survivors.sort(key=lambda x: x.base_power_level, reverse=True)
        return survivors

    @staticmethod
    def _squad_name_mapping() -> dict:
        squad_mapping = {}
        for squad_name in ('The Think Tank', 'Fire Team Alpha', 'Close Assault Squad', 'Training Team', 'EMT Squad',
                           'Corps Of Engineering', 'Gadgeteers', 'Scouting Party'):
            squad_mapping[squad_name] = {'survivors': [], 'lead': None}
        return squad_mapping

    async def survivor_squads(self) -> list[SurvivorSquad]:
        mapping = self._squad_name_mapping()

        survivors = await self.survivors()

        for survivor in survivors:
            if survivor.squad_name is not None:
                if isinstance(survivor, LeadSurvivor):
                    mapping[survivor.squad_name]['lead'] = survivor
                elif isinstance(survivor, Survivor):
                    mapping[survivor.squad_name]['survivors'].append(survivor)

        squad_list = []
        for name in mapping:
            squad = SurvivorSquad(name, lead=mapping[name]['lead'], survivors=mapping[name]['survivors'])
            squad_list.append(squad)

        return squad_list


class FriendEpicAccount(PartialEpicAccount):

    """
    Identical to `PartialEpicAccount` but also has a `mutual` attribute.
    """

    def __init__(
            self,
            auth_session,
            data: dict
    ):
        super().__init__(auth_session, data)

        self.mutual = data.get('mutual') or 0


class FullEpicAccount(PartialEpicAccount):

    """
    Represents a user's own Epic Games account. Includes public and non-public account data.

    Unlike with the parent class, the `auth_session` belongs to the Epic Games account itself.

    This allows us to access non-public account information and make updates/changes to the account.
    """

    def __init__(
            self,
            auth_session,
            data: dict
    ):
        super().__init__(auth_session, data)

        self.display_changes = data.get('numberOfDisplayNameChanges')
        self.last_display_change = self._dt_to_int(data.get('lastDisplayNameChange'))
        self.can_update_display = data.get('canUpdateDisplayName')

        self.name = data.get('name') + ' ' + data.get('lastName')
        self.birth = self._dt_to_int(data.get('dateOfBirth'))
        self.country = data.get('country')
        self.language = data.get('preferredLanguage').capitalize()

        self.email = data.get('email')
        self.verified = data.get('emailVerified')

        self.last_login = self._dt_to_int(data.get('lastLogin'))
        self.failed_logins = data.get('failedLoginAttempts')
        self.tfa_enabled = data.get('tfaEnabled')

    async def external_auths(self) -> list[ExternalConnection]:
        data = await self.auth_session.get_own_externals()

        externals = []

        for item in data:
            externals.append(ExternalConnection(self, item))

        return externals

    async def friends_list(
            self,
            friend_type: str = 'friends'
    ) -> Union[list[PartialEpicAccount], list[FriendEpicAccount]]:
        data = await self.auth_session.get_own_friend_data()

        friends_list = []
        tasks = []

        cls = PartialEpicAccount if friend_type == 'blocklist' else FriendEpicAccount

        for item in data[friend_type]:
            friend = cls(self.auth_session, item)
            friends_list.append(friend)
            tasks.append(asyncio.ensure_future(friend.update()))

        await asyncio.gather(*tasks)
        return friends_list

    async def add_friend(
            self,
            friend_id: str
    ) -> None:
        await self.auth_session.access_request(
            'post',
            self.auth_session.client.friends_requests_url.format(f'{self.id}/friends/{friend_id}')
        )

    async def del_friend(
            self,
            friend_id: str
    ) -> None:
        await self.auth_session.access_request(
            'delete',
            self.auth_session.client.friends_requests_url.format(f'{self.id}/friends/{friend_id}')
        )

    async def block(
            self,
            epic_id: str,
    ) -> None:
        await self.auth_session.access_request(
            'post',
            self.auth_session.client.friends_requests_url.format(f'{self.id}/blocklist/{epic_id}')
        )

    async def unblock(
            self,
            epic_id: str,
    ) -> None:
        await self.auth_session.access_request(
            'delete',
            self.auth_session.client.friends_requests_url.format(f'{self.id}/blocklist/{epic_id}')
        )
