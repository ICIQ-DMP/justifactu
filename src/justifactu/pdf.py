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
from dataclasses import dataclass

from pypdf import PdfWriter
from pypdf.annotations import Highlight
from pypdf.errors import PyPdfError
from pypdf.generic import ArrayObject, FloatObject

from .custom_except import MergingBillWithPaymentError
from .logger import get_logger

log = get_logger(__name__)

HIGHLIGHT_COLOR = "ffff00"  # yellow
HIGHLIGHT_PADDING = 1.0  # points added around each highlighted box


@dataclass(frozen=True)
class HighlightBox:
    """An area of one page to highlight, in pdfplumber coordinates: points from
    the page's top-left corner, page counted from 0."""

    page: int
    x0: float
    top: float
    x1: float
    bottom: float


def _add_highlight(writer: PdfWriter, page_index: int, box: HighlightBox) -> None:
    """Adds a yellow highlight annotation over box on writer's page_index.
    PDF coordinates start at the bottom-left of the page's MediaBox, so the
    box is shifted and flipped vertically."""
    mediabox = writer.pages[page_index].mediabox
    x0 = float(mediabox.left) + box.x0 - HIGHLIGHT_PADDING
    x1 = float(mediabox.left) + box.x1 + HIGHLIGHT_PADDING
    y_top = float(mediabox.top) - box.top + HIGHLIGHT_PADDING
    y_bottom = float(mediabox.top) - box.bottom - HIGHLIGHT_PADDING
    quad_points = ArrayObject(
        [FloatObject(v) for v in (x0, y_top, x1, y_top, x0, y_bottom, x1, y_bottom)]
    )
    writer.add_annotation(
        page_index,
        Highlight(
            rect=(x0, y_bottom, x1, y_top),
            quad_points=quad_points,
            highlight_color=HIGHLIGHT_COLOR,
            printing=True,
        ),
    )


def merge_pdfs(
    first_pdf: Path,
    second_pdf: Path,
    output_path: Path,
    highlights: list[HighlightBox] | None = None,
) -> None:
    """Merges two PDF files into output_path, highlighting in yellow each box
    in highlights. Their pages refer to second_pdf.

    Raises MergingBillWithPaymentError if either PDF can't be read or the
    output can't be written. A partially written output is removed, so a
    later run doesn't mistake it for a finished merge."""
    try:
        writer = PdfWriter()
        writer.append(first_pdf)
        second_pdf_start = len(writer.pages)
        writer.append(second_pdf)
        for box in highlights or []:
            _add_highlight(writer, second_pdf_start + box.page, box)

        with open(output_path, "wb") as f:
            writer.write(f)
            writer.close()
    except (PyPdfError, OSError) as e:
        output_path.unlink(missing_ok=True)
        raise MergingBillWithPaymentError(
            f"Could not merge {first_pdf.name} with {second_pdf.name}: {e}"
        ) from e
