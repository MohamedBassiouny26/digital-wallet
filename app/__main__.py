import asyncio
import os

import hypercorn
import hypercorn.asyncio
import restate

from app.health import health

app = restate.app(services=[health])


def main() -> None:
    conf = hypercorn.Config()
    conf.bind = [f"0.0.0.0:{os.getenv('PORT', '9080')}"]
    asyncio.run(hypercorn.asyncio.serve(app, conf))  # type: ignore[arg-type]


if __name__ == "__main__":
    main()
