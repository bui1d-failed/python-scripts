import json
import requests

with open("config.json", "r", encoding="utf-8") as f:
    config = json.load(f)

rbx_cookie = config.get(".ROBLOSECURITY")
if not rbx_cookie:
    raise ValueError(".ROBLOSECURITY cookie not found in config.json")

session = requests.Session()
session.cookies.set(".ROBLOSECURITY", rbx_cookie)

token_result = session.post("https://auth.roblox.com/v1/usernames/validate", json={})
csrf_token = token_result.headers.get("x-csrf-token")
print("[*] CSRF Token:", csrf_token)

def get_user_id(username):
    r = session.get(f"https://www.roblox.com/users/profile?username={username}")
    if r.status_code != 200:
        raise ValueError("User not found")
    return int(''.join(filter(str.isdigit, r.url)))

def get_thumb(user_id):
    url = f"https://thumbnails.roblox.com/v1/users/avatar-headshot?userIds={user_id}&format=Png&size=150x150"
    d = session.get(url).json()
    return d["data"][0]["imageUrl"]

def get_servers(place_id, cursor=None):
    url = f"https://games.roblox.com/v1/games/{place_id}/servers/Public?limit=100"
    if cursor:
        url += "&cursor=" + cursor
    resp = session.get(url)
    #print("[DEBUG] get_servers status:", resp.status_code)
    #print("[DEBUG] get_servers url:", url)
    #print("[DEBUG] get_servers json:", resp.text[:500])
    return resp.json()


def fetch_thumbs(tokens):
    body = [{
        "requestId": f"0:{t}:AvatarHeadshot:150x150:png:regular",
        "type": "AvatarHeadShot",
        "targetId": 0,
        "token": t,
        "format": "png",
        "size": "150x150"
    } for t in tokens]
    headers = {
        "Content-Type": "application/json",
        "x-csrf-token": csrf_token
    }
    return session.post("https://thumbnails.roblox.com/v1/batch",
                        json=body,
                        headers=headers).json()

def snipe(place_id, username):
    user_id = get_user_id(username)
    target_thumb = get_thumb(user_id)
    print("[*] Target user id:", user_id)
    print("[*] Target thumb url:", target_thumb)

    cursor = None
    all_tokens = []
    while True:
        servers = get_servers(place_id, cursor)
        cursor = servers.get("nextPageCursor")
        for place in servers.get("data", []):
            for token in place.get("playerTokens", []):
                all_tokens.append((token, place))
        if not cursor:
            break

    chunk_size = 100
    total_thumbs = 0
    for i in range(0, len(all_tokens), chunk_size):
        chunk = all_tokens[i:i+chunk_size]
        tokens = [t for t, _ in chunk]
        thumbs = fetch_thumbs(tokens).get("data", [])
        total_thumbs += len(thumbs)
        for thumb in thumbs:
            if thumb and thumb.get("imageUrl") == target_thumb:
                token = thumb["requestId"].split(":")[1]
                place = next(p for t, p in chunk if t == token)
                # found player & return information
                job_id = place["id"]
                join_url = f"https://www.roblox.com/games/start?placeId={place_id}&launchData={place_id}/{job_id}"
                print("FOUND Job ID:", job_id)
                print("Join URL:", join_url)
                return place
    print("Player Not found")
    return None

try:
    place_id = int(input("[i] place id: "))
except ValueError:
    print("place id must be a number")
    exit()

target_username = input("[i] target username: ")
snipe(place_id, target_username)
