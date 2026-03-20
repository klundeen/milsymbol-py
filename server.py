"""FastAPI server for milsymbol Python port.

Run with: uvicorn server:app --reload --port 8000
"""

from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from milsymbol import Symbol

app = FastAPI(title="milsymbol-py", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/symbol")
async def get_symbol(
    sidc: str = Query(..., description="SIDC code"),
    size: int = Query(80, description="Symbol size"),
    quantity: str = Query("", description="Quantity field"),
    type: str = Query("", description="Type field"),
    designation: str = Query("", description="Unique designation"),
):
    sym = Symbol(
        sidc,
        size=size,
        quantity=quantity,
        type=type,
        unique_designation=designation,
    )

    return JSONResponse({
        "sidc": sidc,
        "valid": sym.is_valid(),
        "svg": sym.as_svg(),
        "anchor": sym.get_anchor(),
        "size": sym.get_size(),
        "metadata": sym.get_metadata(),
    })


@app.get("/health")
async def health():
    return {"status": "ok", "version": "0.1.0"}
