"""
PayByPhone - Application de Paiement Parking
FastAPI + Jinja2 + TailwindCSS + Stripe Checkout
"""

import os
import json
from datetime import datetime, timedelta
from typing import Optional
import math
import uuid

import stripe
from dotenv import load_dotenv
from fastapi import FastAPI, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

# Load environment variables
load_dotenv()

# Stripe configuration
stripe.api_key = os.getenv("STRIPE_SECRET_KEY")
STRIPE_PUBLISHABLE_KEY = os.getenv("STRIPE_PUBLISHABLE_KEY")

# Admin configuration
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin123")

# FastAPI app
app = FastAPI(title="PayByPhone")

# Templates
templates = Jinja2Templates(directory="templates")

# In-memory session storage (no database)
sessions = {}

# Pricing: 2€ per hour
PRICING = {
    30: 1.00,
    60: 2.00,
    90: 3.00,
    120: 4.00,
    150: 5.00,
    180: 6.00,
}

# Zone mapping - Île-de-France
ZONES = {
    # Paris (75)
    "75001": {"name": "Paris 1er - Louvre", "city": "Paris"},
    "75002": {"name": "Paris 2ème - Bourse", "city": "Paris"},
    "75003": {"name": "Paris 3ème - Temple", "city": "Paris"},
    "75004": {"name": "Paris 4ème - Hôtel-de-Ville", "city": "Paris"},
    "75005": {"name": "Paris 5ème - Panthéon", "city": "Paris"},
    "75006": {"name": "Paris 6ème - Luxembourg", "city": "Paris"},
    "75007": {"name": "Paris 7ème - Palais-Bourbon", "city": "Paris"},
    "75008": {"name": "Paris 8ème - Élysée", "city": "Paris"},
    "75009": {"name": "Paris 9ème - Opéra", "city": "Paris"},
    "75010": {"name": "Paris 10ème - Entrepôt", "city": "Paris"},
    "75011": {"name": "Paris 11ème - Popincourt", "city": "Paris"},
    "75012": {"name": "Paris 12ème - Reuilly", "city": "Paris"},
    "75013": {"name": "Paris 13ème - Gobelins", "city": "Paris"},
    "75014": {"name": "Paris 14ème - Observatoire", "city": "Paris"},
    "75015": {"name": "Paris 15ème - Vaugirard", "city": "Paris"},
    "75016": {"name": "Paris 16ème - Passy", "city": "Paris"},
    "75017": {"name": "Paris 17ème - Batignolles", "city": "Paris"},
    "75018": {"name": "Paris 18ème - Butte-Montmartre", "city": "Paris"},
    "75019": {"name": "Paris 19ème - Buttes-Chaumont", "city": "Paris"},
    "75020": {"name": "Paris 20ème - Ménilmontant", "city": "Paris"},
    # Hauts-de-Seine (92)
    "92100": {"name": "Boulogne-Billancourt - Centre", "city": "Boulogne-Billancourt"},
    "92200": {"name": "Neuilly-sur-Seine - Centre", "city": "Neuilly-sur-Seine"},
    "92300": {"name": "Levallois-Perret - Centre", "city": "Levallois-Perret"},
    "92400": {"name": "Courbevoie - La Défense", "city": "Courbevoie"},
    "92500": {"name": "Rueil-Malmaison - Centre", "city": "Rueil-Malmaison"},
    "92600": {"name": "Asnières-sur-Seine - Centre", "city": "Asnières-sur-Seine"},
    "92700": {"name": "Colombes - Centre", "city": "Colombes"},
    "92800": {"name": "Puteaux - La Défense", "city": "Puteaux"},
    "92000": {"name": "Nanterre - Centre", "city": "Nanterre"},
    "92130": {"name": "Issy-les-Moulineaux - Centre", "city": "Issy-les-Moulineaux"},
    "92120": {"name": "Montrouge - Centre", "city": "Montrouge"},
    "92170": {"name": "Vanves - Centre", "city": "Vanves"},
    "92140": {"name": "Clamart - Centre", "city": "Clamart"},
    "92150": {"name": "Suresnes - Centre", "city": "Suresnes"},
    "92250": {"name": "La Garenne-Colombes - Centre", "city": "La Garenne-Colombes"},
    # Seine-Saint-Denis (93)
    "93100": {"name": "Montreuil - Centre", "city": "Montreuil"},
    "93200": {"name": "Saint-Denis - Centre", "city": "Saint-Denis"},
    "93300": {"name": "Aubervilliers - Centre", "city": "Aubervilliers"},
    "93400": {"name": "Saint-Ouen - Centre", "city": "Saint-Ouen"},
    "93500": {"name": "Pantin - Centre", "city": "Pantin"},
    "93000": {"name": "Bobigny - Centre", "city": "Bobigny"},
    "93170": {"name": "Bagnolet - Centre", "city": "Bagnolet"},
    "93260": {"name": "Les Lilas - Centre", "city": "Les Lilas"},
    "93250": {"name": "Villemomble - Centre", "city": "Villemomble"},
    "93110": {"name": "Rosny-sous-Bois - Centre", "city": "Rosny-sous-Bois"},
    # Val-de-Marne (94)
    "94200": {"name": "Ivry-sur-Seine - Centre", "city": "Ivry-sur-Seine"},
    "94300": {"name": "Vincennes - Centre", "city": "Vincennes"},
    "94400": {"name": "Vitry-sur-Seine - Centre", "city": "Vitry-sur-Seine"},
    "94100": {"name": "Saint-Maur-des-Fossés - Centre", "city": "Saint-Maur-des-Fossés"},
    "94000": {"name": "Créteil - Centre", "city": "Créteil"},
    "94500": {"name": "Champigny-sur-Marne - Centre", "city": "Champigny-sur-Marne"},
    "94800": {"name": "Villejuif - Centre", "city": "Villejuif"},
    "94700": {"name": "Maisons-Alfort - Centre", "city": "Maisons-Alfort"},
    "94130": {"name": "Nogent-sur-Marne - Centre", "city": "Nogent-sur-Marne"},
    "94250": {"name": "Gentilly - Centre", "city": "Gentilly"},
    # Val-d'Oise (95)
    "95100": {"name": "Argenteuil - Centre", "city": "Argenteuil"},
    "95200": {"name": "Sarcelles - Centre", "city": "Sarcelles"},
    "95000": {"name": "Cergy - Centre", "city": "Cergy"},
    "95300": {"name": "Pontoise - Centre", "city": "Pontoise"},
    "95400": {"name": "Villiers-le-Bel - Centre", "city": "Villiers-le-Bel"},
    "95600": {"name": "Eaubonne - Centre", "city": "Eaubonne"},
    "95800": {"name": "Cergy-le-Haut", "city": "Cergy"},
    # Yvelines (78)
    "78000": {"name": "Versailles - Centre", "city": "Versailles"},
    "78100": {"name": "Saint-Germain-en-Laye - Centre", "city": "Saint-Germain-en-Laye"},
    "78200": {"name": "Mantes-la-Jolie - Centre", "city": "Mantes-la-Jolie"},
    "78300": {"name": "Poissy - Centre", "city": "Poissy"},
    "78400": {"name": "Chatou - Centre", "city": "Chatou"},
    "78500": {"name": "Sartrouville - Centre", "city": "Sartrouville"},
    "78600": {"name": "Maisons-Laffitte - Centre", "city": "Maisons-Laffitte"},
    # Essonne (91)
    "91100": {"name": "Corbeil-Essonnes - Centre", "city": "Corbeil-Essonnes"},
    "91200": {"name": "Athis-Mons - Centre", "city": "Athis-Mons"},
    "91300": {"name": "Massy - Centre", "city": "Massy"},
    "91000": {"name": "Évry-Courcouronnes - Centre", "city": "Évry-Courcouronnes"},
    "91400": {"name": "Orsay - Centre", "city": "Orsay"},
    "91120": {"name": "Palaiseau - Centre", "city": "Palaiseau"},
    # Seine-et-Marne (77)
    "77000": {"name": "Melun - Centre", "city": "Melun"},
    "77100": {"name": "Meaux - Centre", "city": "Meaux"},
    "77200": {"name": "Torcy - Centre", "city": "Torcy"},
    "77300": {"name": "Fontainebleau - Centre", "city": "Fontainebleau"},
    "77400": {"name": "Lagny-sur-Marne - Centre", "city": "Lagny-sur-Marne"},
    "77500": {"name": "Chelles - Centre", "city": "Chelles"},
    "77600": {"name": "Bussy-Saint-Georges - Centre", "city": "Bussy-Saint-Georges"},
}


def get_zone_info(code: str) -> dict:
    """Get zone information by code"""
    if code in ZONES:
        return ZONES[code]
    return {"name": f"Zone {code}", "city": "Ville"}


def calculate_price(duration_minutes: int) -> float:
    """Calculate price based on duration - rounds up to nearest hour"""
    if duration_minutes in PRICING:
        return PRICING[duration_minutes]
    hours = math.ceil(duration_minutes / 60)
    return hours * 2.00


# ==================== ROUTES ====================

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Home page"""
    return templates.TemplateResponse("home.html", {"request": request})


@app.post("/zone")
async def process_zone(request: Request, zone_code: str = Form(...)):
    """Process zone code"""
    zone_code = zone_code.strip()
    if not zone_code:
        return templates.TemplateResponse("home.html", {
            "request": request,
            "error": "Veuillez entrer un code zone"
        })
    return RedirectResponse(f"/vehicle/{zone_code}", status_code=303)


@app.get("/vehicle/{zone_code}", response_class=HTMLResponse)
async def vehicle_page(request: Request, zone_code: str):
    """Vehicle registration page"""
    zone_info = get_zone_info(zone_code)
    return templates.TemplateResponse("vehicle.html", {
        "request": request,
        "zone_code": zone_code,
        "zone_info": zone_info
    })


@app.post("/vehicle/{zone_code}")
async def process_vehicle(
    request: Request,
    zone_code: str,
    plate: str = Form(...),
    vehicle_type: str = Form("Voiture"),
    description: str = Form("")
):
    """Process vehicle info"""
    plate = plate.strip().upper()
    if not plate:
        zone_info = get_zone_info(zone_code)
        return templates.TemplateResponse("vehicle.html", {
            "request": request,
            "zone_code": zone_code,
            "zone_info": zone_info,
            "error": "Veuillez entrer une plaque d'immatriculation"
        })
    
    # Create session in memory
    session_id = str(uuid.uuid4())[:8]
    zone_info = get_zone_info(zone_code)
    
    sessions[session_id] = {
        "id": session_id,
        "zone_code": zone_code,
        "zone_name": zone_info["name"],
        "plate": plate,
        "vehicle_type": vehicle_type,
        "duration_minutes": 0,
        "price": 0.0,
        "created_at": datetime.now(),
        "end_time": None,
        "paid": False
    }
    
    return RedirectResponse(f"/duration/{session_id}", status_code=303)


@app.get("/duration/{session_id}", response_class=HTMLResponse)
async def duration_page(request: Request, session_id: str):
    """Duration selection page"""
    if session_id not in sessions:
        return RedirectResponse("/", status_code=303)
    
    session = sessions[session_id]
    zone_info = get_zone_info(session["zone_code"])
    
    # Create a simple object for template
    class SessionObj:
        def __init__(self, data):
            for key, value in data.items():
                setattr(self, key, value)
    
    return templates.TemplateResponse("duration.html", {
        "request": request,
        "session": SessionObj(session),
        "zone_info": zone_info,
        "pricing": PRICING
    })


@app.post("/duration/{session_id}")
async def process_duration(
    request: Request,
    session_id: str,
    duration: int = Form(...)
):
    """Process duration selection"""
    if session_id not in sessions:
        return RedirectResponse("/", status_code=303)
    
    price = calculate_price(duration)
    sessions[session_id]["duration_minutes"] = duration
    sessions[session_id]["price"] = price
    
    return RedirectResponse(f"/summary/{session_id}", status_code=303)


@app.get("/summary/{session_id}", response_class=HTMLResponse)
async def summary_page(request: Request, session_id: str):
    """Payment summary page"""
    if session_id not in sessions:
        return RedirectResponse("/", status_code=303)
    
    session = sessions[session_id]
    zone_info = get_zone_info(session["zone_code"])
    end_time = datetime.now() + timedelta(minutes=session["duration_minutes"])
    
    class SessionObj:
        def __init__(self, data):
            for key, value in data.items():
                setattr(self, key, value)
    
    return templates.TemplateResponse("summary.html", {
        "request": request,
        "session": SessionObj(session),
        "zone_info": zone_info,
        "end_time": end_time,
        "stripe_key": STRIPE_PUBLISHABLE_KEY
    })


@app.post("/create-checkout-session/{session_id}")
async def create_checkout_session(request: Request, session_id: str):
    """Create Stripe Checkout session"""
    if session_id not in sessions:
        return RedirectResponse("/", status_code=303)
    
    session = sessions[session_id]
    base_url = str(request.base_url).rstrip("/")
    
    checkout_session = stripe.checkout.Session.create(
        payment_method_types=["card"],
        line_items=[{
            "price_data": {
                "currency": "eur",
                "product_data": {
                    "name": f"Stationnement - {session['zone_name']}",
                    "description": f"Plaque: {session['plate']} | Durée: {session['duration_minutes']} min",
                },
                "unit_amount": int(session["price"] * 100),
            },
            "quantity": 1,
        }],
        mode="payment",
        success_url=f"{base_url}/success/{session_id}",
        cancel_url=f"{base_url}/summary/{session_id}?cancelled=true",
    )
    
    return RedirectResponse(checkout_session.url, status_code=303)


@app.get("/success/{session_id}", response_class=HTMLResponse)
async def success_page(request: Request, session_id: str):
    """Success page with virtual ticket"""
    if session_id not in sessions:
        return RedirectResponse("/", status_code=303)
    
    session = sessions[session_id]
    
    if not session["paid"]:
        session["paid"] = True
        session["end_time"] = datetime.now() + timedelta(minutes=session["duration_minutes"])
    
    zone_info = get_zone_info(session["zone_code"])
    
    class SessionObj:
        def __init__(self, data):
            for key, value in data.items():
                setattr(self, key, value)
    
    return templates.TemplateResponse("success.html", {
        "request": request,
        "session": SessionObj(session),
        "zone_info": zone_info
    })


@app.get("/compte", response_class=HTMLResponse)
async def compte_page(request: Request):
    """Account page"""
    return templates.TemplateResponse("compte.html", {"request": request})


@app.get("/login", response_class=HTMLResponse)
async def login_redirect(request: Request):
    """Login redirects to compte"""
    return RedirectResponse("/compte", status_code=303)


@app.get("/cancel", response_class=HTMLResponse)
async def cancel_page(request: Request):
    """Payment cancelled"""
    return RedirectResponse("/", status_code=303)


@app.get("/api/price/{duration}")
async def get_price(duration: int):
    """Get price for a specific duration"""
    price = calculate_price(duration)
    return {"duration": duration, "price": price}


def serialize_sessions():
    """Serialize sessions for JSON (handle datetime objects)"""
    serialized = {}
    for sid, session in sessions.items():
        s = dict(session)
        if s.get("created_at"):
            s["created_at"] = s["created_at"].isoformat()
        if s.get("end_time"):
            s["end_time"] = s["end_time"].isoformat()
        serialized[sid] = s
    return serialized


@app.get("/admin", response_class=HTMLResponse)
async def admin_dashboard(request: Request):
    """Admin dashboard page"""
    sessions_json = json.dumps(serialize_sessions())
    zones_json = json.dumps(ZONES)
    
    return templates.TemplateResponse("admin.html", {
        "request": request,
        "sessions_json": sessions_json,
        "zones_json": zones_json,
        "admin_password": ADMIN_PASSWORD
    })


@app.get("/api/admin/sessions")
async def api_admin_sessions():
    """API endpoint for admin to get sessions data"""
    return serialize_sessions()


@app.get("/api/admin/stats")
async def api_admin_stats():
    """API endpoint for admin stats"""
    all_sessions = list(sessions.values())
    paid_sessions = [s for s in all_sessions if s.get("paid")]
    
    total_revenue = sum(s.get("price", 0) for s in paid_sessions)
    active_count = sum(
        1 for s in paid_sessions 
        if s.get("end_time") and s["end_time"] > datetime.now()
    )
    
    return {
        "total_sessions": len(all_sessions),
        "paid_sessions": len(paid_sessions),
        "active_sessions": active_count,
        "total_revenue": total_revenue,
        "zones_count": len(set(s.get("zone_code") for s in all_sessions))
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
