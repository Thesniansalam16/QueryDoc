import os

from flask import Flask, render_template, request, jsonify
from dotenv import load_dotenv

from rag import (
    index_pdf,
    generate_answer,
    clear_vector_database
)

from chat_history import (
    init_db,
    create_conversation,
    save_message,
    get_conversations,
    get_messages,
    delete_conversation,
    save_current_document,
    get_current_document,
    delete_current_document
)


# ============================================================
# LOAD ENVIRONMENT
# ============================================================

load_dotenv()


# ============================================================
# FLASK APP
# ============================================================

app = Flask(__name__)


# ============================================================
# CONFIGURATION
# ============================================================

UPLOAD_FOLDER = "uploads"

ALLOWED_EXTENSIONS = {"pdf"}

MAX_FILE_SIZE = 25 * 1024 * 1024  # 25 MB

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["MAX_CONTENT_LENGTH"] = MAX_FILE_SIZE


# ============================================================
# CREATE REQUIRED FOLDERS
# ============================================================

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs("vector_db", exist_ok=True)


# ============================================================
# INITIALIZE DATABASE
# ============================================================

init_db()


# ============================================================
# HELPER
# ============================================================

def allowed_file(filename):

    return (
        "." in filename
        and filename.rsplit(".", 1)[1].lower()
        in ALLOWED_EXTENSIONS
    )


# ============================================================
# HOME
# ============================================================

@app.route("/")
def home():

    return render_template("index.html")


# ============================================================
# DOCUMENT STATUS
# ============================================================

@app.route("/document", methods=["GET"])
def document_status():

    try:

        document = get_current_document()

        return jsonify({
            "success": True,
            "document": document
        })

    except Exception as e:

        print("DOCUMENT STATUS ERROR:", str(e))

        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


# ============================================================
# UPLOAD PDF
# ============================================================

@app.route("/upload", methods=["POST"])
def upload_pdf():

    try:

        # ----------------------------------------------------
        # CHECK IF DOCUMENT ALREADY EXISTS
        # ----------------------------------------------------

        current_document = get_current_document()

        if current_document:

            return jsonify({
                "success": False,
                "error": (
                    "A PDF is already uploaded. "
                    "Delete the current PDF before "
                    "uploading another document."
                )
            }), 400


        # ----------------------------------------------------
        # CHECK FILE
        # ----------------------------------------------------

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


        # ----------------------------------------------------
        # CHECK EXTENSION
        # ----------------------------------------------------

        if not allowed_file(file.filename):

            return jsonify({
                "success": False,
                "error": "Only PDF files are allowed."
            }), 400


        # ----------------------------------------------------
        # SAFE FILENAME
        # ----------------------------------------------------

        filename = os.path.basename(file.filename)

        pdf_path = os.path.join(
            app.config["UPLOAD_FOLDER"],
            filename
        )


        # ----------------------------------------------------
        # SAVE PDF
        # ----------------------------------------------------

        file.save(pdf_path)

        print("PDF SAVED:", pdf_path)


        # ----------------------------------------------------
        # INDEX PDF
        # ----------------------------------------------------

        print("INDEXING PDF...")

        result = index_pdf(
            pdf_path=pdf_path,
            document_name=filename
        )

        print("INDEX RESULT:", result)


        # ----------------------------------------------------
        # SAVE DOCUMENT METADATA
        # ----------------------------------------------------

        save_current_document(
            filename=filename,
            file_path=pdf_path,
            pages=result.get("pages", 0),
            chunks=result.get("chunks", 0)
        )


        # ----------------------------------------------------
        # RESPONSE
        # ----------------------------------------------------

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

        print("UPLOAD ERROR:")
        print(str(e))


        # Remove partially uploaded file if something failed

        try:

            if "pdf_path" in locals():

                if os.path.exists(pdf_path):

                    os.remove(pdf_path)

        except Exception:
            pass


        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


# ============================================================
# DELETE CURRENT PDF
# ============================================================

@app.route("/delete-document", methods=["DELETE"])
def delete_document():

    try:

        document = get_current_document()


        if not document:

            return jsonify({
                "success": False,
                "error": "No document is currently uploaded."
            }), 404


        # ----------------------------------------------------
        # DELETE PDF FILE
        # ----------------------------------------------------

        file_path = document["file_path"]


        if os.path.exists(file_path):

            os.remove(file_path)

            print("PDF DELETED:", file_path)


        # ----------------------------------------------------
        # DELETE VECTOR DATABASE
        # ----------------------------------------------------

        clear_vector_database()


        # ----------------------------------------------------
        # DELETE DOCUMENT METADATA
        # ----------------------------------------------------

        delete_current_document()


        return jsonify({
            "success": True,
            "message": "Document deleted successfully."
        }), 200


    except Exception as e:

        print("DELETE DOCUMENT ERROR:", str(e))

        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


# ============================================================
# CHAT
# ============================================================

@app.route("/chat", methods=["POST"])
def chat():

    try:

        # ----------------------------------------------------
        # CHECK DOCUMENT
        # ----------------------------------------------------

        document = get_current_document()


        if not document:

            return jsonify({
                "success": False,
                "error": (
                    "Please upload a PDF before "
                    "asking questions."
                )
            }), 400


        # ----------------------------------------------------
        # GET REQUEST DATA
        # ----------------------------------------------------

        data = request.get_json(silent=True) or {}

        question = data.get("question", "").strip()


        if not question:

            return jsonify({
                "success": False,
                "error": "Please enter a question."
            }), 400


        print("QUESTION:", question)


        # ----------------------------------------------------
        # GENERATE ANSWER
        # ----------------------------------------------------

        result = generate_answer(question)


        return jsonify({
            "success": True,
            "answer": result.get("answer", ""),
            "sources": result.get("sources", [])
        }), 200


    except Exception as e:

        print("CHAT ERROR:")
        print(str(e))

        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


# ============================================================
# CREATE NEW CHAT
# ============================================================

@app.route("/new-chat", methods=["POST"])
def new_chat():

    try:

        conversation_id = create_conversation()

        return jsonify({
            "success": True,
            "conversation_id": conversation_id
        }), 200


    except Exception as e:

        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


# ============================================================
# CHAT HISTORY
# ============================================================

@app.route("/history", methods=["GET"])
def history():

    try:

        conversations = get_conversations()


        result = []

        for conversation in conversations:

            result.append({
                "id": conversation[0],
                "title": conversation[1],
                "created_at": conversation[2]
            })


        return jsonify({
            "success": True,
            "conversations": result
        }), 200


    except Exception as e:

        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


# ============================================================
# GET ONE CONVERSATION
# ============================================================

@app.route("/history/<conversation_id>", methods=["GET"])
def conversation(conversation_id):

    try:

        messages = get_messages(
            conversation_id
        )


        result = []

        for message in messages:

            result.append({
                "role": message[0],
                "content": message[1],
                "created_at": message[2]
            })


        return jsonify({
            "success": True,
            "messages": result
        }), 200


    except Exception as e:

        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


# ============================================================
# DELETE CHAT HISTORY
# ============================================================

@app.route(
    "/history/<conversation_id>",
    methods=["DELETE"]
)
def remove_conversation(conversation_id):

    try:

        delete_conversation(
            conversation_id
        )


        return jsonify({
            "success": True,
            "message": "Conversation deleted."
        }), 200


    except Exception as e:

        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


# ============================================================
# RUN APPLICATION
# ============================================================

if __name__ == "__main__":

    print()
    print("=" * 60)
    print("        QUERYDOC AI")
    print("=" * 60)
    print("Server running at:")
    print("http://127.0.0.1:5000")
    print("=" * 60)
    print()

    app.run(
        host="0.0.0.0",
        port=5000,
        debug=True
    )
