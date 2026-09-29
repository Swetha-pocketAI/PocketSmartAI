"""Illustrative budgeted catalog. Search links are searches, not verified listings."""
from urllib.parse import quote_plus
from .models import HomeInput, PartyInput, JewelryInput, Item, Plan

CATALOG = {
    'lights': ('LED light', 'Amazon', 800, 'https://www.amazon.in/s?k='),
    'fans': ('Ceiling fan', 'Flipkart', 2400, 'https://www.flipkart.com/search?q='),
    'tables': ('Dining table', 'IKEA', 8500, 'https://www.ikea.com/in/en/search/?q='),
    'food': ('Meal per guest', 'Swiggy', 250, 'https://www.swiggy.com/search?query='),
    'decor': ('Decoration set', 'Amazon', 1800, 'https://www.amazon.in/s?k='),
    'venue': ('Venue / stay allowance', 'OYO', 3500, 'https://www.oyorooms.com/search?search='),
    'music': ('Entertainment allowance', 'Amazon', 1500, 'https://www.amazon.in/s?k='),
    'earrings': ('Earrings', 'Flipkart', 900, 'https://www.flipkart.com/search?q='),
    'necklace': ('Necklace', 'Amazon', 1800, 'https://www.amazon.in/s?k='),
    'bracelet': ('Bracelet', 'Flipkart', 750, 'https://www.flipkart.com/search?q='),
}

def make_item(key, quantity, context=''):
    name, platform, unit_price, prefix = CATALOG[key]
    term = f'{context} {name}'.strip()
    return Item(category=key, name=name, platform=platform, quantity=quantity,
                unit_price=unit_price, subtotal=unit_price*quantity,
                search_url=prefix+quote_plus(term))

def pack(kind, budget, requests, notes):
    """Prioritize request order; include only whole units affordable in the remaining budget."""
    remaining = budget
    items = []
    for key, requested, context in requests:
        unit = CATALOG[key][2]
        count = min(requested, remaining // unit)
        if count:
            item = make_item(key, count, context)
            items.append(item)
            remaining -= item.subtotal
        if count < requested:
            notes.append(f'{CATALOG[key][0]}: {count} of {requested} fit the budget.')
    if not items:
        notes.append('No illustrative catalog items fit this budget. Increase the budget or change your choices.')
    notes.append('Prices are sample estimates in INR. Open the search links to check current products and prices.')
    return Plan(kind=kind, budget=budget, total=budget-remaining, remaining=remaining,
                items=items, notes=notes, insight='This plan prioritizes the items shown and keeps the estimate within budget.',source='demo')

def home(data: HomeInput):
    return pack('home', data.budget, [('lights', data.lights, data.style),('fans',data.fans,data.style),
                                      ('tables',data.tables,data.style)], [f'{data.room} · {data.style} style'])

def party(data: PartyInput):
    requests = [('food',data.guests,f'{data.city} {data.event_type}'),('decor',1,data.event_type)]
    if data.venue == 'External':
        requests.append(('venue',1,data.city))
    requests.append(('music',1,data.event_type))
    return pack('party',data.budget,requests,[f'{data.event_type} for {data.guests} guests in {data.city}.',
           'Food allowance is a per-guest estimate; confirm catering minimums and delivery fees.'])

def jewelry(data: JewelryInput):
    context = f'{data.occasion} {data.style} {data.outfit_color}'
    return pack('jewelry',data.budget,[('necklace',1,context),('earrings',1,context),('bracelet',1,context)],
                [f'{data.occasion} · {data.style} style'+(f' · {data.outfit_color} outfit' if data.outfit_color else '')])
