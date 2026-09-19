import fitz


def extract_pdf_pages(pdf_path):

    pages = []

    document = fitz.open(pdf_path)


    try:

        for page_number in range(
            len(document)
        ):

            page = document[
                page_number
            ]


            text = page.get_text(
                "text"
            )


            pages.append({

                "page":
                    page_number + 1,

                "text":
                    text

            })


    finally:

        document.close()


    return pages
