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

from pathlib import Path

from pypdf import PdfWriter
from pypdf.errors import PyPdfError


from .custom_except import MergingBillWithPaymentError
from .logger import get_logger

log = get_logger(__name__)


def merge_pdfs(first_pdf: Path, second_pdf: Path, output_path: Path) -> None:
    """Merges two PDF files into output_path.

    Raises MergingBillWithPaymentError if either PDF can't be read or the
    output can't be written. A partially written output is removed, so a
    later run doesn't mistake it for a finished merge."""
    try:
        writer = PdfWriter()
        writer.append(first_pdf)
        writer.append(second_pdf)

        with open(output_path, "wb") as f:
            writer.write(f)
            writer.close()
    except (PyPdfError, OSError) as e:
        output_path.unlink(missing_ok=True)
        raise MergingBillWithPaymentError(
            f"Could not merge {first_pdf.name} with {second_pdf.name}: {e}"
        ) from e
