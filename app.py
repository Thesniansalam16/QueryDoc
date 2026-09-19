@app.route("/upload", methods=["POST"])
def upload_pdf():

    try:
        print("========== PDF UPLOAD START ==========")

        # Check existing document
        current_document = get_current_document()

        if current_document:
            return jsonify({
                "success": False,
                "error": (
                    "A PDF is already uploaded. "
                    "Delete the current PDF before uploading another PDF."
                )
            }), 400

        # Check file
        if "file" not in request.files:
            return jsonify({
                "success": False,
                "error": "No PDF file was received by the server."
            }), 400

        file = request.files["file"]

        if file.filename == "":
            return jsonify({
                "success": False,
                "error": "Please select a PDF file."
            }), 400

        # Check extension
        if not allowed_file(file.filename):
            return jsonify({
                "success": False,
                "error": "Only PDF files are allowed."
            }), 400

        filename = os.path.basename(file.filename)

        # Make upload folder
        os.makedirs(
            app.config["UPLOAD_FOLDER"],
            exist_ok=True
        )

        pdf_path = os.path.join(
            app.config["UPLOAD_FOLDER"],
            filename
        )

        print("Saving PDF:", pdf_path)

        # Save PDF
        file.save(pdf_path)

        print("PDF SAVED SUCCESSFULLY")
        print("Starting PDF indexing...")

        # Index PDF
        result = index_pdf(
            pdf_path=pdf_path,
            document_name=filename
        )

        print("PDF INDEXING COMPLETED")
        print("Index result:", result)

        # Save metadata
        save_current_document(
            filename=filename,
            file_path=pdf_path,
            pages=result.get("pages", 0),
            chunks=result.get("chunks", 0)
        )

        print("DOCUMENT METADATA SAVED")
        print("========== PDF UPLOAD SUCCESS ==========")

        return jsonify({
            "success": True,
            "message": "PDF uploaded and indexed successfully.",
            "document": {
                "filename": filename,
                "pages": result.get("pages", 0),
                "chunks": result.get("chunks", 0)
            }
        }), 200

    except Exception as e:

        print("========== PDF UPLOAD ERROR ==========")
        print(type(e).__name__)
        print(str(e))
        print("======================================")

        # Delete partially uploaded file
        try:
            if "pdf_path" in locals():
                if os.path.exists(pdf_path):
                    os.remove(pdf_path)
        except Exception as cleanup_error:
            print(
                "Cleanup error:",
                str(cleanup_error)
            )

        return jsonify({
            "success": False,
            "error": (
                "PDF processing failed: "
                + str(e)
            )
        }), 500
