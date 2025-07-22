from items_database import ALL_CAPE_ITEMS



ITEM_ID_TO_NAME = {}
for cape_name, cape_data in ALL_CAPE_ITEMS.items():
    item_id = cape_data['item_id']
    if item_id:
        ITEM_ID_TO_NAME[item_id] = cape_name

def get_cape_id_by_name(cape_name: str) -> str:
    return ALL_CAPE_ITEMS[cape_name]["item_id"]

def get_cape_data_by_id(item_id: str) -> dict:
    """Get cape data by item ID"""
    cape_name = ITEM_ID_TO_NAME[item_id]
    return ALL_CAPE_ITEMS[cape_name]

def get_cape_data_by_name(cape_name: str) -> dict:
    """Get cape data by cape name"""
    return ALL_CAPE_ITEMS[cape_name]


