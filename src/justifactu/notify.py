# justifactu - Automated billing justifications
# Copyright (C) 2026  Aleix Mariné Tena (AleixMT), Carles de la Cuadra, David Romero San Millán (DavidRomeroICIQ)
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

"""Standalone entry point for sending a one-off notification email, with
optional log attachments. Unlike main.py, failures here are not caught —
they propagate as a raw exception and a non-zero exit, by design."""

import argparse
from pathlib import Path

from .mail import send_mail_authenticated
from .defines import SecretNames
from .secret import read_secret


def parse_arguments() -> argparse.Namespace:
    """Parse and validate command-line arguments for the notify entry point."""
    parser = argparse.ArgumentParser(description="Send a notification email.")

    parser.add_argument(
        "--to",
        required=False,
        default=None,
        help="Recipient email address. Defaults to the SMTP_ADMIN_EMAIL secret if omitted.",
    )

    parser.add_argument(
        "--subject",
        required=True,
        help="Email subject line.",
    )

    parser.add_argument(
        "--body",
        required=True,
        help="Email body text.",
    )

    parser.add_argument(
        "--attach",
        action="append",
        type=Path,
        default=None,
        dest="attachments",
        help="Path to a file to attach. Repeat this flag to attach multiple files"
        " (e.g. --attach a.log --attach b.log).",
    )

    return parser.parse_args()


def main() -> None:
    args = parse_arguments()
    to_email = args.to or read_secret(SecretNames.SMTP_ADMIN_EMAIL.value)
    send_mail_authenticated(
        to_email=to_email,
        subject=args.subject,
        body=args.body,
        attachment_paths=args.attachments,
    )


if __name__ == "__main__":
    main()
