import requests
import time
import re

BOT_TOKEN = '7585977578:AAFxo3T5s5kaOOu0eiG3wiWkO_lD8poYkjk'
BASE_URL = f'https://api.telegram.org/bot{BOT_TOKEN}'

ALLOWED_GROUPS = ['donghuasone555', 'dOnGhUaSoNe555', 'daoofdonghua2DFanChat', 'daoofdonghuafanchat', 'error21092']


ALLOWED_LINK_PATTERNS = [
    r'https://t\.me/daoofdonghua\S*',
    r'https://t\.me/DaoOfDonghua\S*',
    r'https://t.me/DAO_MMS10',
    r'https://t.me/DAO_MMS6',
    r'https://t.me/DAO_MMS9',
    r'https://t.me/btth2021BTTH2025',
    r'https://t.me/Alchemysupremedod',
    r'https://t.me/Therebirtheoftangsan',
    r'https://t.me/AllchineseanimeS',
    r'https://t.me/MrStone007',
    r'https://t.me/AllchineseanimeS',
    r'https://cutt.ly/PwF5lMPd',
    r'https://t.me/DiamondStore899',
    r'https://t.me/daoofdonghua2DFanChat',
    r'https://t.me/dOnGhUaSoNe555'
    r'https://t.me/daoofdonghuafanchat'
]


def normalize_link(text):
    match = re.search(r'(https://t\.me/|t\.me/)(\w+)', text, re.IGNORECASE)
    if match:
        return f"https://t.me/{match.group(2)}"
    return None

def is_allowed_link(text):
    normalized_link = normalize_link(text)
    if normalized_link:
        for pattern in ALLOWED_LINK_PATTERNS:
            if re.search(pattern, normalized_link, re.IGNORECASE):
                return True
    return False

def get_updates(offset=None):
    url = f'{BASE_URL}/getUpdates'
    params = {'timeout': 10, 'offset': offset}
    response = requests.get(url, params=params)
    if response.status_code == 200:
        return response.json().get('result', [])
    return []

def delete_message(chat_id, message_id):
    url = f'{BASE_URL}/deleteMessage'
    params = {'chat_id': chat_id, 'message_id': message_id}
    requests.get(url, params=params)

def send_dm_reply(chat_id, user_text):
    reply_text = f"{user_text}"
    url = f"{BASE_URL}/sendMessage"
    params = {'chat_id': chat_id, 'text': reply_text}
    requests.get(url, params=params)

def is_admin(chat_id, user_id):
    url = f'{BASE_URL}/getChatMember'
    params = {'chat_id': chat_id, 'user_id': user_id}
    response = requests.get(url, params=params)
    if response.status_code == 200:
        status = response.json().get('result', {}).get('status', '')
        return status in ['administrator', 'creator']
    return False

def is_allowed_group(chat):
    username = chat.get('username', '').lower()
    title = chat.get('title', '').lower()
    return username in ALLOWED_GROUPS or title in ALLOWED_GROUPS

def main():
    offset = None
    while True:
        updates = get_updates(offset)
        for update in updates:
            offset = update['update_id'] + 1
            if 'message' in update:
                message = update['message']
                chat = message['chat']
                chat_id = chat['id']
                message_id = message['message_id']
                chat_type = chat['type']
                text = message.get('text', '') or message.get('caption', '')
                user_id = message.get('from', {}).get('id', 0)
                if chat_type == 'private' and text:
                    send_dm_reply(chat_id, text)
                    continue
                if not is_allowed_group(chat):
                    continue
                if message.get('is_automatic_forward'):
                    continue
                if 'sender_chat' in message and message['sender_chat'].get('type') == 'channel':
                    continue
                if text and any(word in text.lower() for word in ["https://", "t.me/"]):
                    if not is_allowed_link(text) and not is_admin(chat_id, user_id):                        
                        delete_message(chat_id, message_id)
        time.sleep(1)

if __name__ == '__main__':
    main()
    
