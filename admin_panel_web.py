import os
import json
from typing import List, Dict
import aiofiles

from fastapi import FastAPI, Request, HTTPException, Depends
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

DATA_DIR = os.getenv("DATA_DIR", "data")
ADMIN_TOKEN = os.getenv("ADMIN_PANEL_TOKEN", "changeme")

app = FastAPI(title="Mahiro Admin Panel")
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")


async def _load_json(path: str):
    try:
        async with aiofiles.open(path, "r", encoding="utf-8") as f:
            content = await f.read()
            return json.loads(content) if content else []
    except FileNotFoundError:
        return []
    except Exception:
        return []


async def _save_json(path: str, data):
    async with aiofiles.open(path, "w", encoding="utf-8") as f:
        await f.write(json.dumps(data, ensure_ascii=False, indent=2))


def verify_admin(request: Request):
    token = request.headers.get("X-ADMIN-TOKEN") or request.query_params.get("token")
    if token != ADMIN_TOKEN:
        raise HTTPException(status_code=401, detail="Unauthorized")


@app.get("/")
async def dashboard(request: Request, _=Depends(verify_admin)):
    donations = await _load_json(f"{DATA_DIR}/donations.json")
    balances = await _load_json(f"{DATA_DIR}/star_balances.json")

    active = [d for d in donations if not d.get("refunded")]
    refunded = [d for d in donations if d.get("refunded")]

    total_stars = sum(d.get("stars", 0) for d in active)
    total_refunded = sum(d.get("stars", 0) for d in refunded)

    context = {
        "request": request,
        "total_donations": len(donations),
        "active_donations": len(active),
        "refunded_donations": len(refunded),
        "total_stars": total_stars,
        "total_refunded": total_refunded,
        "unique_donors": len(set(d.get("user_id") for d in active)),
        "balances_count": len(balances),
    }

    return templates.TemplateResponse("admin.html", context)


@app.get("/donations")
async def view_donations(_=Depends(verify_admin)):
    donations = await _load_json(f"{DATA_DIR}/donations.json")
    return donations


@app.get("/balances")
async def view_balances(_=Depends(verify_admin)):
    balances = await _load_json(f"{DATA_DIR}/star_balances.json")
    return balances


@app.post("/refund/{transaction_id}")
async def refund(transaction_id: str, _=Depends(verify_admin)):
    donations_path = f"{DATA_DIR}/donations.json"
    balances_path = f"{DATA_DIR}/star_balances.json"

    donations = await _load_json(donations_path)
    balances = await _load_json(balances_path) or {}

    for donation in donations:
        if donation.get("transaction_id") == transaction_id:
            if donation.get("refunded"):
                raise HTTPException(status_code=400, detail="Already refunded")

            donation["refunded"] = True
            donation["refund_date"] = __import__("datetime").datetime.now().isoformat()

            user_id = str(donation.get("user_id"))
            stars = donation.get("stars", 0)
            balances[user_id] = balances.get(user_id, 0) - stars
            if balances[user_id] < 0:
                balances[user_id] = 0

            await _save_json(donations_path, donations)
            await _save_json(balances_path, balances)

            return {"status": "ok", "transaction_id": transaction_id}

    raise HTTPException(status_code=404, detail="Donation not found")
