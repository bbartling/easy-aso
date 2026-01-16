# rpc_app.py
import fastapi_jsonrpc as jsonrpc
from fastapi.responses import RedirectResponse
from bacpypes_server.rpc_methods import rpc

rpc_api = jsonrpc.API(title="diy-bacnet-server", version="1.0", description="The BACnet RPC Gateway for the DIY Agent Manager")
rpc_api.bind_entrypoint(rpc)


# Optional: redirect base path
@rpc_api.router.get("/")
async def root_redirect():
    return RedirectResponse("/docs")
