import re, json, os

results = {}

# settings.py
with open('config/settings.py') as f:
    content = f.read()
    coins = re.findall(r'"([A-Z]{2,10})"', content)
    results['settings.py'] = sorted(set(coins))

# coins.json
if os.path.exists('config/coins.json'):
    with open('config/coins.json') as f:
        data = json.load(f)
        coins = []
        if isinstance(data, dict):
            for tier in data.values():
                if isinstance(tier, list):
                    for item in tier:
                        if isinstance(item, dict) and 'symbol' in item:
                            coins.append(item['symbol'])
                        elif isinstance(item, str):
                            coins.append(item)
        results['coins.json'] = sorted(set(coins))

# SYMBOL_MAP in technical files
for fname in ['src/technical/funding.py', 'src/technical/candle_fetcher.py']:
    if os.path.exists(fname):
        with open(fname) as f:
            content = f.read()
            coins = re.findall(r'"([A-Z]{2,10})"(?:\s*:)', content)
            results[fname] = sorted(set(coins))

# Print comparison
all_coins = sorted(set(c for v in results.values() for c in v))
print("COIN|" + "|".join(results.keys()))
for coin in all_coins:
    row = coin
    for source in results:
        row += "|" + ("YES" if coin in results[source] else "NO")
    print(row)
