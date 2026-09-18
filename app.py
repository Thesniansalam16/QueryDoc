@app.route("/upload", methods=["POST"])
def upload_pdf():
    try:
        current_document = get_current_document()

        if current_document:
            return jsonify({
                "success": False,
                "error": "A document is already uploaded. Delete it before uploading a new PDF."
            }), 400

        if "file" not in request.files:
            return jsonify({
                "success": False,
                "error": "No PDF file selected."
            }), 400

        file = request.files["file"]

        if file.filename == "":
            return jsonify({
                "success": False,
                "error": "Please select a PDF."
            }), 400

        if not file.filename.lower().endswith(".pdf"):
            return jsonify({
                "success": False,
                "error": "Only PDF files are allowed."
            }), 400

        filename = secure_filename(file.filename)

        os.makedirs(UPLOAD_FOLDER, exist_ok=True)

        pdf_path = os.path.join(UPLOAD_FOLDER, filename)

        file.save(pdf_path)

        print("PDF saved:", pdf_path)

        result = index_pdf(
            pdf_path,
            filename
        )

        save_current_document(
            filename=filename,
            file_path=pdf_path,
            pages=result.get("pages", 0),
            chunks=result.get("chunks", 0)
        )

        return jsonify({
            "success": True,
            "message": "PDF uploaded successfully.",
            "filename": filename,
            "pages": result.get("pages", 0),
            "chunks": result.get("chunks", 0)
        }), 200

    except Exception as e:
        print("UPLOAD ERROR:", str(e))

        return jsonify({
            "success": False,
            "error": str(e)
        }), 500
