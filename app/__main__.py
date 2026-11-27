import asyncio
import os

import hypercorn
import hypercorn.asyncio
import restate

from app.health import health
from app.transaction_service import transaction_service
from app.accounts_service import account_service

app = restate.app(services=[health,transaction_service,account_service])


def main() -> None:
    conf = hypercorn.Config()
    conf.bind = [f"0.0.0.0:{os.getenv('PORT', '9080')}"]
    asyncio.run(hypercorn.asyncio.serve(app, conf))  # type: ignore[arg-type]


if __name__ == "__main__":
    main()
