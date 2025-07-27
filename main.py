import requests
from items_functions import get_cape_data_by_id, get_cape_data_by_name,get_cape_id_by_name, ALL_CAPE_ITEMS

BASE_URL = "https://europe.albion-online-data.com/api/v2/stats/prices/"

TAXES: float = 6.5

SELECTED_ITEM: str = "Heretic Cape"
BASE_CAPE_SELECTED_CITY: str = "Lymhurst"
ARTIFACT_SELECTED_CITY: str = "Lymhurst"
HEART_SELECTED_CITY: str = "Lymhurst"



def get_active_ids_by_cape_type(cape_type: str) -> tuple[list[str], list[str], list[str], list[str]]:
    cape_name_list = [name for name in ALL_CAPE_ITEMS if name.split(' ', 1)[1].split('.')[0] == cape_type]
    cape_id_list = []
    base_cape_id_list = set()
    crests_id_list = set()
    hearts_id_list = set()
    for cape in cape_name_list:
        cape_id = get_cape_id_by_name(cape)
        cape_id_list.append(cape_id)
        data = ALL_CAPE_ITEMS[cape]
        base_cape_id_list.add(data["base_cape"])
        crests_id_list.add(data["crest"])
        hearts_id_list.add(data["heart"]["id"])
    crests_id_list = sorted(crests_id_list)
    hearts_id_list = sorted(hearts_id_list)
    base_cape_id_list = sorted(base_cape_id_list)
    return cape_id_list, base_cape_id_list, crests_id_list, hearts_id_list

def get_sell_prices_min(item_ids: list[str], city: str) -> dict:
    item_str = ",".join(item_ids).replace(" ", "")
    url = f"{BASE_URL}{item_str}?locations={city}&qualities=1"
    response = requests.get(url)
    data = response.json()
    prices = {}
    for item in data:
        item_id = item.get("item_id")
        sell_price_min = item.get("sell_price_min")
        prices[item_id] = sell_price_min
    return prices

def get_buy_prices_max(item_ids: list[str], city: str) -> dict:
    item_str = ",".join(item_ids).replace(" ", "")
    url = f"{BASE_URL}{item_str}?locations={city}&qualities=1"
    response = requests.get(url)
    data = response.json()
    prices = {}
    for item in data:
        item_id = item.get("item_id")
        buy_price_max = item.get("buy_price_max")
        prices[item_id] = buy_price_max
    return prices

def get_heart_quantity_for_cape(cape_id: str) -> int:
    for name in ALL_CAPE_ITEMS:
        if get_cape_id_by_name(name) == cape_id:
            return ALL_CAPE_ITEMS[name]["heart"]["quantity"]
    return 1 #default if not found

def get_profit(cape_price: int, base_cape_price: int, crest_price: int, heart_price: int, heart_quantity: int) -> int:
    profit = cape_price-(base_cape_price+crest_price+(heart_price*heart_quantity))
    profit_after_taxes = round(profit * ((100-TAXES)/100))
    return profit_after_taxes

def get_profit_percentage(cape_price: int, base_cape_price: int, crest_price: int, heart_price: int, heart_quantity: int) -> float:
    total_cost = get_total_cost(base_cape_price, crest_price, heart_price, heart_quantity)
    if total_cost == 0:
        return 0.0
    profit = cape_price - total_cost
    profit_after_taxes = round(profit * ((100-TAXES)/100))
    return round((profit_after_taxes / total_cost) * 100, 2)

def get_total_cost(base_cape_price: int, crest_price: int, heart_price: int, heart_quantity: int) -> int:
    total_price = base_cape_price + crest_price + (heart_price * heart_quantity)
    return total_price




def get_row_from_cape_id(cape_id, base_cape_prices, crest_prices, heart_prices, cape_prices) -> list:
    base_cape_id = crest_id = heart_id = None
    heart_quantity = 0
    for name, data in ALL_CAPE_ITEMS.items():
        if get_cape_id_by_name(name) == cape_id:
            base_cape_id = data["base_cape"]
            crest_id = data["crest"]
            heart_id = data["heart"]["id"]
            heart_quantity = data["heart"].get("quantity", 1)
            break
    base_cape_price = base_cape_prices.get(base_cape_id, 0) or 0
    crest_price = crest_prices.get(crest_id, 0) or 0
    heart_price = heart_prices.get(heart_id, 0) or 0
    cape_price = cape_prices.get(cape_id, 0) or 0
    total_price = get_total_cost(base_cape_price, crest_price, heart_price, heart_quantity)
    profit = get_profit(cape_price, base_cape_price, crest_price, heart_price, heart_quantity)
    profit_percent = get_profit_percentage(cape_price, base_cape_price, crest_price, heart_price, heart_quantity)
    return [crest_price, heart_price, base_cape_price, total_price, profit, profit_percent]


    
def main():
    cape_ids, base_cape_ids, crest_ids, heart_ids = get_active_ids_by_cape_type(SELECTED_ITEM)
    cape_prices: dict = get_buy_prices_max(cape_ids, "Black Market")
    base_cape_prices: dict = get_sell_prices_min(base_cape_ids, BASE_CAPE_SELECTED_CITY)
    crest_prices: dict = get_sell_prices_min(crest_ids, BASE_CAPE_SELECTED_CITY)
    heart_prices: dict = get_sell_prices_min(heart_ids, BASE_CAPE_SELECTED_CITY)
    for cape_id in cape_ids:
        row = get_row_from_cape_id(cape_id, base_cape_prices, crest_prices, heart_prices, cape_prices)
        if row is not None:
            print(row)
            



if __name__ == "__main__":
    main()
