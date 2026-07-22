import json
import os
import secrets

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OWNERS_FILE = os.path.join(BASE_DIR, "workspace_owners.json")


def _load_owners():
    if not os.path.exists(OWNERS_FILE):
        return {}
    with open(OWNERS_FILE, "r") as f:
        return json.load(f)


def _save_owners(data):
    with open(OWNERS_FILE, "w") as f:
        json.dump(data, f, indent=2)


def register_workspace(workspace_id: str) -> str:
    """
    STEP: Naya workspace register karta hai aur ek random secret owner_key deta hai.
    WHY: Ye tabhi call hoga jab koi user 'Create Workspace' dabayega —
    is workspace ka 'owner' wahi banega, aur sirf usी ke paas ye key hogi.
    """
    owners = _load_owners()
    owner_key = secrets.token_hex(16)
    owners[workspace_id] = owner_key
    _save_owners(owners)
    return owner_key


def is_owner(workspace_id: str, owner_key: str) -> bool:
    """
    STEP: Check karta hai ki di gayi owner_key is workspace ke liye sahi hai ya nahi.
    WHY: Delete endpoint isi function se verify karega ki request bhejne
    wala asli creator hai ya sirf ek joined member.
    """
    owners = _load_owners()
    stored_key = owners.get(workspace_id)
    return stored_key is not None and stored_key == owner_key