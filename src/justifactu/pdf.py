import re
from pathlib import Path

from pypdf import PdfReader

from justifactu.logger import get_logger

log = get_logger(__name__)


def parse_sap_id_from_bill(pdf_path: Path) -> str:
    query_str = r"Fra. \d{10}"
    # restricting the search with the beginning of the year, which appears in the line that
    # we are interested in, which contains the date.
    pattern = re.compile(query_str, re.MULTILINE)

    reader = PdfReader(pdf_path)

    for page_num, page in enumerate(reader.pages):
        # Get text of the page
        text = page.extract_text()
        print("text is: " + text)
        if not text:
            continue

        match = pattern.search(text)
        if not match:
            continue

        return match.group(0).replace("\n", "")

    raise ValueError(f"No SAP ID found in {pdf_path}")
