import restate

health = restate.Service("health")


@health.handler()
async def ping(ctx: restate.Context) -> str:
    """Placeholder handler so the SDK endpoint has something to register."""
    return "ok"
