"""FastAPI comparison server for milsymbol-py.

Provides a REST API for the playground to compare Python and JS output
side by side. Run with:

    uvicorn server:app --reload --port 8000
"""

from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from milsymbol import Symbol

app = FastAPI(
    title="milsymbol-py",
    version="0.1.0",
    description="Military symbol SVG generation — Python port of milsymbol.js",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/symbol")
async def get_symbol(
    sidc: str = Query(..., description="SIDC code (number or letter format)"),
    size: int = Query(80, description="Symbol size (scaling factor, 100 = base)"),
    quantity: str = Query("", description="Quantity text field (C)"),
    type: str = Query("", description="Type text field (V)"),
    designation: str = Query("", description="Unique designation (T)"),
    staffComments: str = Query("", description="Staff comments (G)"),
    additionalInformation: str = Query("", description="Additional information (H)"),
    dtg: str = Query("", description="Date-time group (W)"),
    speed: str = Query("", description="Speed (Z)"),
    higherFormation: str = Query("", description="Higher formation (M)"),
    iffSif: str = Query("", description="IFF/SIF (P)"),
    altitudeDepth: str = Query("", description="Altitude/depth (X)"),
    location: str = Query("", description="Location (Y)"),
    reinforcedReduced: str = Query("", description="Reinforced/reduced (F)"),
) -> JSONResponse:
    """Generate a military symbol SVG and return it with metadata."""
    sym = Symbol(
        sidc,
        size=size,
        quantity=quantity,
        type=type,
        uniqueDesignation=designation,
        staffComments=staffComments,
        additionalInformation=additionalInformation,
        dtg=dtg,
        speed=speed,
        higherFormation=higherFormation,
        iffSif=iffSif,
        altitudeDepth=altitudeDepth,
        location=location,
        reinforcedReduced=reinforcedReduced,
    )

    return JSONResponse(
        {
            "sidc": sidc,
            "valid": sym.is_valid(),
            "svg": sym.as_svg(),
            "anchor": sym.get_anchor(),
            "size": sym.get_size(),
            "metadata": sym.get_metadata(),
        }
    )


@app.get("/health")
async def health() -> dict:
    """Health check endpoint."""
    return {"status": "ok", "version": "0.1.0"}
