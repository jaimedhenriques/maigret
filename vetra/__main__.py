"""Run the Vetra pilot with `python -m vetra`."""

import argparse
import logging
import re

from . import create_app


class _RedactInvitationTokens(logging.Filter):
    def filter(self, record):
        message = record.getMessage()
        record.msg = re.sub(r"/(candidate|api/portal)/[A-Za-z0-9_-]{32,128}", r"/\1/[redacted]", message)
        record.args = ()
        return True


def main():
    parser = argparse.ArgumentParser(description="Vetra employment verification pilot")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()
    app = create_app()
    if app.config["DEMO"] and args.host not in ("127.0.0.1", "::1", "localhost"):
        parser.error("Demo mode must bind to a loopback address.")
    logging.getLogger("werkzeug").addFilter(_RedactInvitationTokens())
    app.run(host=args.host, port=args.port, debug=False, use_reloader=False)


if __name__ == "__main__":
    main()
