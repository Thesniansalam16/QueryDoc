import pymupdf


def extract_pdf_pages(pdf_path):

    document = pymupdf.open(pdf_path)

    pages = []

    for page_number, page in enumerate(
        document,
        start=1
    ):

        text = page.get_text("text")

        if text and text.strip():

            pages.append({
                "page": page_number,
                "text": text.strip()
            })

    document.close()

    return pages