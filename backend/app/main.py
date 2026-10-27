import asyncio
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from app.api.v1 import auth, bids, dashboard, health, rfqs
from app.core.config import settings
from app.websocket.manager import ws_manager

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("rfq_auction")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("British Auction RFQ Engine starting up...")
    yield
    logger.info("British Auction RFQ Engine shutting down...")


app = FastAPI(
    title=settings.APP_NAME,
    description="Enterprise Request for Quotation (RFQ) System featuring British Auction dynamic bid extensions and forced close rules.",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Permits local development on Vite / Playwright
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include REST API Routers
app.include_router(health.router, prefix="/api/v1")
app.include_router(auth.router, prefix="/api/v1")
app.include_router(rfqs.router, prefix="/api/v1")
app.include_router(bids.router, prefix="/api/v1")
app.include_router(dashboard.router, prefix="/api/v1")


# WebSocket Endpoints
@app.websocket("/ws/general")
async def websocket_general_endpoint(websocket: WebSocket):
    await ws_manager.connect_general(websocket)
    try:
        while True:
            # Keepalive listener
            await websocket.receive_text()
    except WebSocketDisconnect:
        ws_manager.disconnect_general(websocket)


@app.websocket("/ws/auctions/{rfq_id}")
async def websocket_auction_endpoint(websocket: WebSocket, rfq_id: int):
    await ws_manager.connect_auction(rfq_id, websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        ws_manager.disconnect_auction(rfq_id, websocket)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host=settings.HOST, port=settings.PORT, reload=True)
