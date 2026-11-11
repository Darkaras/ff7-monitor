"""
Monitor restock FINAL FANTASY VII REVELATION - Collector's Edition
Square Enix Store IT (BigCommerce). Invia una notifica Telegram.
Nessuna libreria esterna richiesta.
"""
import json
import os
import sys
import urllib.parse
import urllib.request

STORE = "https://it.store.square-enix-games.com"
PAGE = STORE + "/final-fantasy-vii-revelation"
PRODUCT_ID = "3561"
ATTR_PLATFORM = "1062"
ATTR_EDITION = "1063"

# Piattaforme da controllare: cancella le righe che non ti interessano.
PLATFORMS = {
    "1622": "PS5",
    "1624": "Xbox Series X/S",
    "1623": "Nintendo Switch 2",
}
# Edizioni da controllare (1627 = Collector's Edition).
EDITIONS = {
    "1627": "Collector's Edition",
}

STATE_FILE = "state.json"
TOKEN = os.environ.get("TELEGRAM_TOKEN", "")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")
MANUAL = os.environ.get("MANUAL_RUN", "") == "true"


def check(platform_id, edition_id):
    body = urllib.parse.urlencode({
        "action": "add",
        "product_id": PRODUCT_ID,
        f"attribute[{ATTR_PLATFORM}]": platform_id,
        f"attribute[{ATTR_EDITION}]": edition_id,
        "qty[]": "1",
    }).encode()
    req = urllib.request.Request(
        f"{STORE}/remote/v1/product-attributes/{PRODUCT_ID}",
        data=body,
        headers={
            "Content-Type": "application/x-www-form-urlencoded",
            "X-Requested-With": "XMLHttpRequest",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                          "AppleWebKit/537.36 (KHTML, like Gecko) "
                          "Chrome/130.0 Safari/537.36",
            "Referer": PAGE,
        },
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        data = json.load(r)["data"]
    price = (data.get("price") or {}).get("with_tax", {}).get("formatted", "")
    return bool(data.get("instock")) and bool(data.get("purchasable")), price.replace("‎", "")


def telegram(text):
    if not TOKEN or not CHAT_ID:
        print("Telegram non configurato:", text)
        return
    body = urllib.parse.urlencode({"chat_id": CHAT_ID, "text": text}).encode()
    urllib.request.urlopen(
        f"https://api.telegram.org/bot{TOKEN}/sendMessage", data=body, timeout=30
    )


def main():
    try:
        with open(STATE_FILE) as f:
            old = json.load(f)
    except Exception:
        old = {}

    new, lines, errors = {}, [], []
    for pid, pname in PLATFORMS.items():
        for eid, ename in EDITIONS.items():
            key = f"{pname} - {ename}"
            try:
                ok, price = check(pid, eid)
            except Exception as e:
                errors.append(f"{key}: {e}")
                new[key] = old.get(key, False)
                continue
            new[key] = ok
            stato = "DISPONIBILE" if ok else "esaurito"
            lines.append(f"{key} ({price}): {stato}")
            print(lines[-1])
            if ok and not old.get(key, False):
                telegram(f"🚨 RESTOCK! {key} è disponibile a {price}\n{PAGE}")
            elif not ok and old.get(key, False):
                telegram(f"{key} è di nuovo esaurito.")

    if MANUAL:
        msg = "Controllo manuale:\n" + "\n".join(lines)
        if errors:
            msg += "\n\nErrori:\n" + "\n".join(errors)
        telegram(msg)

    with open(STATE_FILE, "w") as f:
        json.dump(new, f, indent=2, ensure_ascii=False)

    if errors:
        print("ERRORI:", *errors, sep="\n")
        if len(errors) == len(PLATFORMS) * len(EDITIONS):
            sys.exit(1)  # tutto fallito: il workflow risulta in errore


if __name__ == "__main__":
    main()
