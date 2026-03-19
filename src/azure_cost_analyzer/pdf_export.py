"""PDF export via Playwright (optional dependency)."""

import logging
from pathlib import Path

logger = logging.getLogger(__name__)


def export_pdf(html_path: str, pdf_path: str | None = None) -> str | None:
    """Render the HTML report to PDF using Playwright Chromium.

    Args:
        html_path: Path to the generated HTML report.
        pdf_path: Output PDF path. Defaults to same name with .pdf extension.

    Returns:
        The PDF file path on success, None on failure.
    """
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        logger.error(
            "Playwright is not installed. Install with: "
            "pip install 'azure-cost-analyzer[pdf]' && playwright install chromium"
        )
        return None

    if pdf_path is None:
        pdf_path = str(Path(html_path).with_suffix(".pdf"))

    html_uri = Path(html_path).resolve().as_uri()

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page()
            page.goto(html_uri, wait_until="networkidle")
            # Allow Plotly charts to render
            page.wait_for_timeout(2000)
            page.pdf(
                path=pdf_path,
                format="A4",
                print_background=True,
                margin={"top": "1cm", "bottom": "1cm", "left": "1cm", "right": "1cm"},
            )
            browser.close()
        logger.info("PDF exported to %s", pdf_path)
        return pdf_path
    except Exception as e:
        logger.error("PDF export failed: %s", e)
        logger.error("Ensure Chromium is installed: playwright install chromium")
        return None
