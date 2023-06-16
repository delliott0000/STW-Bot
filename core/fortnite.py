from typing import Optional

# stringList is a lookup table containing values such as the names, rarities and types of items
# This is necessary as not all data can be retrieved via HTTP request, some of it is hard-coded in the game
from resources.emojis import emojis
from resources.lookup import stringList
from core.errors import UnknownItem, BadItemData


class BaseEntity:

    """
    Base Fortnite: STW entity.

    This could be a "physical" item such as a weapon/hero, or something more abstract like a quest.

    All entities have a unique item ID as well as a template ID that defines the type of item it is.

    They also have an Epic Games account that they belong to.
    """

    def __init__(
            self,
            account,
            item_id: str,
            template_id: str
    ):
        self.account = account
        self.item_id: str = item_id
        self.template_id: str = template_id

    def __eq__(
            self,
            other
    ):
        return isinstance(other, BaseEntity) and self.item_id and other.item_id and self.item_id == other.item_id


class AccountItem(BaseEntity):

    """
    Items such as schematics, heroes, account resources and crafting materials are classified as account items.

    Does not include quests or (currently) cosmetic items.

    These items have a set of attributes that vary slightly depending on the exact item type.
    """

    def __init__(
            self,
            account,
            item_id: str,
            template_id: str,
            attrs: dict
    ):
        super().__init__(account, item_id, template_id)

        # stringList does not contain every possible template ID
        # We must try out a few similar template IDs to get the details we're after
        # If the item still cannot be found then UnknownItem is raised
        for string in [
            template_id,
            template_id[:-2] + '01',
            template_id.replace('Trap:tid', 'Schematic:sid')[:-2] + '01',
            template_id.replace('Weapon:wid', 'Schematic:sid')[:-2] + '01'
        ]:
            if string in stringList['Items']:
                lookup_id = string
                break
        else:
            raise UnknownItem(item_id, template_id)

        self.name: str = stringList['Items'][lookup_id]['name']
        self.rarity: str = stringList['Items'][lookup_id]['rarity']
        self.type: str = stringList['Item Types'][stringList['Items'][lookup_id]['type']]

        self.level: int = attrs.get('level', 1)
        self.favourite: bool = attrs.get('favorite', False)

        self.tier: int = int(template_id[-1]) if template_id[-1].isdigit() else 1


class Recyclable(AccountItem):

    """
    Any item that can be recycled.

    Includes schematics/heroes/survivors as well as inventory items like weapons and traps.
    """

    async def recycle(self):
        await self.account.auth_session.profile_request(
            route='client',
            operation='RecycleItem',
            profile_id='campaign',
            json={
                "targetItemId":
                    self.item_id
            }
        )


class Upgradable(Recyclable):

    """
    Any item that can be upgraded and evolved.

    All upgradable items can also be recycled, but not necessarily vice versa, hence the class inheritance.
    """

    async def upgrade(self) -> None:
        await self.account.auth_session.profile_request(
            route='client',
            operation='UpgradeItem',
            profile_id='campaign',
            json={
                "targetItemId":
                    self.item_id
            }
        )
        self.level += 1

    async def evolve(self, index: int = 0) -> None:
        await self.account.auth_session.profile_request(
            route='client',
            operation='ConvertItem',
            profile_id='campaign',
            json={
                "targetItemId":
                    self.item_id,
                "conversionIndex":
                    index
            }
        )
        self.tier += 1


class Schematic(Upgradable):

    """
    Represents an in-game schematic, which is used to craft weapons or traps.

    This class is NOT the same as weapon/trap inventory items.
    """

    def __init__(
            self,
            account,
            item_id: str,
            template_id: str,
            attrs: dict
    ):
        # Only the "ore" (brightcore/obsidian) version of each weapon template ID is stored
        # If the item is "crystal" (sunbeam/shadowshard) we must temporarily edit our template ID to perform the lookup
        try:
            super().__init__(account, item_id, template_id, attrs)
        except UnknownItem:
            super().__init__(account, item_id, template_id.replace('_crystal_', '_ore_'), attrs)
            self.template_id = template_id

        try:
            self.perks = [SchematicPerk(self, perkId) for perkId in attrs['alterations']]
        except KeyError:
            self.perks = []

    @property
    def power_level(self):
        return stringList['Item Power Levels']['Other'][self.rarity][f'{self.tier}'][f'{self.level}']

    @property
    def material(self):
        material = None
        if self.tier == 4 and '_ore_' in self.template_id:
            material = 'Obsidian'
        elif self.tier == 4:
            material = 'Shadow Shard'
        elif self.tier == 5 and '_ore_' in self.template_id:
            material = 'Brightcore'
        elif self.tier == 5:
            material = 'Sunbeam'
        return material

    def get_conversion_index(self, target_material: str):
        try:
            return 0 if self.tier != 3 else {'': 1, 'Crystal': 1, 'Ore': 0}[target_material]
        except KeyError:
            return 0


class SchematicPerk:

    """
    Represents a single perk attached to a schematic.

    Unlike most other Fortnite objects, this does not inherit from `BaseEntity`.

    This is because they only have a single `perk_id` to identify what they are.

    Currently missing the description attribute, but we can deduce the rarity from the perk ID.
    """

    def __init__(
            self,
            item: Schematic,
            perk_id: str
    ):
        self.item = item
        self.perkId = perk_id

        self.description = None

        try:
            self.rarity = ['common', 'uncommon', 'rare', 'epic', 'legendary'][int(perk_id[-1]) - 1]
        except ValueError:
            self.rarity = 'common'


class SurvivorBase(Upgradable):

    """
    The base class for all survivor account items.

    All survivors share common attributes such as personality and the squad they belong too.

    Lead survivors vary slightly from standard survivors though.

    Not to be confused with survivor characters encountered in-world during gameplay.
    """

    def __init__(
            self,
            account,
            item_id: str,
            template_id: str,
            attrs: dict
    ):
        super().__init__(account, item_id, template_id, attrs)

        try:
            self.personality, self.squad_index = [
                attrs['personality'].split('.')[-1][2:],
                attrs['squad_slot_idx']
            ]
        except KeyError:
            raise BadItemData(item_id, template_id, attrs)

        try:
            self.squad_id = attrs['squad_id']
            self.squad_name = stringList['Survivor Squads'][self.squad_id]
        except KeyError:
            self.squad_name = None
            self.squad_index = None


class Survivor(SurvivorBase):

    """
    Standard (non-leader) survivor account item.
    """

    def __init__(
            self,
            account,
            item_id: str,
            template_id: str,
            attrs: dict
    ):
        super().__init__(account, item_id, template_id, attrs)

        try:
            self.set_bonus_type = attrs['set_bonus'].split('.')[-1][2:].replace('Low', '').replace('High', '')
            self.set_bonus_data = stringList['Set Bonuses'][self.set_bonus_type]
        except KeyError:
            raise BadItemData(item_id, template_id, attrs)

    @property
    def base_power_level(self) -> int:
        return stringList['Item Power Levels']['Survivor'][self.rarity][f'{self.tier}'][f'{self.level}']


class LeadSurvivor(SurvivorBase):

    """
    Lead survivor account item.
    """

    def __init__(
            self,
            account,
            item_id: str,
            template_id: str,
            attrs: dict
    ):
        super().__init__(account, item_id, template_id, attrs)

        try:
            self.preferred_squad_name = stringList['Leads Preferred Squad'][attrs['managerSynergy']]
        except KeyError:
            raise BadItemData(item_id, template_id, attrs)

    @property
    def base_power_level(self) -> int:
        return stringList['Item Power Levels']['Lead Survivor'][self.rarity][f'{self.tier}'][f'{self.level}']


class ActiveSetBonus:

    """
    Represents a complete, active set bonus within a survivor squad.

    Not to be confused with the `Survivor.set_bonus_type` attribute.

    Multiple `Survivor`s with the same `set_bonus_type` form an `ActiveSetBonus`.

    This class does not inherit from `BaseEntity`.
    """

    def __init__(
            self,
            name: str,
            bonus: int,
            bonus_type: int,
    ):
        self.name = name
        self.bonus = bonus
        self.bonus_type = bonus_type

        self.fort_stats = {'Fortitude': 0, 'Offense': 0, 'Resistance': 0, 'Tech': 0}

        if self.bonus_type in self.fort_stats:
            self.fort_stats[self.bonus_type] += self.bonus


class SurvivorSquad:

    """
    A squad of survivors.

    This class does not inherit from `BaseEntity` because it is just an arranged group of `SurvivorBase`s.
    """

    def __init__(
            self,
            name: str,
            lead: Optional[LeadSurvivor] = None,
            survivors: list[Survivor] = None
    ):
        if survivors is None:
            survivors = []
        survivors.sort(key=lambda x: x.squad_index)

        self.name = name
        self.lead = lead
        self.survivors = survivors

    # These next two property methods are quite unreadable and need work.
    # But they work for now.

    @property
    def active_set_bonuses(self) -> list[ActiveSetBonus]:
        set_bonus_tally = {"TrapDurability": 0, "RangedDamage": 0, "MeleeDamage": 0, "TrapDamage": 0,
                           "AbilityDamage": 0, "Fortitude": 0, "Resistance": 0, "ShieldRegen": 0}

        for survivor in self.survivors:
            set_bonus_tally[survivor.set_bonus_type] += 1

        active_set_bonuses = []

        for pair in set_bonus_tally.items():

            set_bonus_name = stringList['Set Bonuses'][pair[0]]['name']
            set_bonus_points = stringList['Set Bonuses'][pair[0]]['bonus']
            set_bonus_type = stringList['Set Bonuses'][pair[0]]['bonus_type']

            for i in range(pair[1] // stringList['Set Bonuses'][pair[0]]['requirement']):
                active_set_bonuses.append(ActiveSetBonus(set_bonus_name, set_bonus_points, set_bonus_type))

        return active_set_bonuses

    @property
    def total_fort_stats(self) -> dict[str, int]:
        fort_stats = {'Fortitude': 0, 'Offense': 0, 'Resistance': 0, 'Tech': 0}

        for set_bonus in self.active_set_bonuses:
            set_bonus_fort_stats = set_bonus.fort_stats
            for stat in set_bonus_fort_stats:
                fort_stats[stat] += set_bonus_fort_stats[stat]

        survivor_point_count = 0

        if self.lead is not None:
            if self.lead.preferred_squad_name == self.name:
                survivor_point_count += self.lead.base_power_level * 2
            else:
                survivor_point_count += self.lead.base_power_level

        for survivor in self.survivors:
            power = survivor.base_power_level

            lead_bonus_increment = stringList['Lead Bonus Increment']

            if self.lead is not None and self.lead.personality == survivor.personality:
                power += lead_bonus_increment[self.lead.rarity][0]
            elif self.lead is not None:
                power += lead_bonus_increment[self.lead.rarity][1]

            survivor_point_count += power

        fort_stats[stringList['Survivor Squads FORT'][self.name]] += survivor_point_count

        return fort_stats


class AccountResource(AccountItem):

    """
    Represents an account resource, such as pure drops of rain or a survivor supercharger.

    Does not include inventory items or crafting ingredients.
    """

    def __init__(
            self,
            account,
            item_id: str,
            template_id: str,
            quantity: int,
    ):
        super().__init__(account, item_id, template_id, {})
        self.quantity = quantity

    @property
    def emoji(self):
        return emojis['resources'].get(self.name) or emojis['rarities'][self.rarity]


class MissionAlertReward(AccountResource):

    """
    Represents a single mission alert reward from a mission alert.

    These are not rewards that can be earned over and over, these are strictly one-time rewards.

    Unlike `AccountResource`, these are not "real" items, rather they're more akin to "imaginary" items.

    Hence, they do not actually have a unique item ID nor an owner account.

    These also don't necessarily have to be a "resource" as such (despite the class inheritance suggesting otherwise).

    They could also be schematics, heroes or other types of items.
    """

    def __init__(
            self,
            **kwargs
    ):
        super().__init__(None, 'None', kwargs.get('itemType'), kwargs.get('quantity'))


class MissionAlert:

    """
    Represents a mission alert.

    This does not inherit from `BaseEntity` because it has no owner account nor a template ID.
    """

    def __init__(
            self,
            **kwargs
    ):
        self.name = kwargs.get('name')
        self.theater = kwargs.get('theater')
        self.tile_theme = kwargs.get('tile_theme')
        self.alert_rewards = [MissionAlertReward(**reward) for reward in kwargs.get('alert_rewards_data', [])]

        power_data = kwargs.get('power').split(' ')
        self.power = int(power_data[0])
        self.four_player = 'Players' in power_data
