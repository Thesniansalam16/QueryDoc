import os

from flask import (
    Flask,
    render_template,
    request,
    jsonify
)

from dotenv import load_dotenv


# =========================================================
# ENV
# =========================================================

load_dotenv()


# =========================================================
# PROJECT IMPORTS
# =========================================================

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


# =========================================================
# FLASK APP
# =========================================================

app = Flask(__name__)


# =========================================================
# CONFIG
# =========================================================

UPLOAD_FOLDER = "uploads"

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

app.config["MAX_CONTENT_LENGTH"] = (
    25 * 1024 * 1024
)

ALLOWED_EXTENSIONS = {
    "pdf"
}


os.makedirs(
    UPLOAD_FOLDER,
    exist_ok=True
)


# =========================================================
# DATABASE
# =========================================================

init_db()


# =========================================================
# HELPER
# =========================================================

def allowed_file(filename):

    return (
        "." in filename
        and
        filename.rsplit(
            ".",
            1
        )[1].lower()
        in ALLOWED_EXTENSIONS
    )


# =========================================================
# HOME
# =========================================================

@app.route("/")
def home():

    return render_template(
        "index.html"
    )


# =========================================================
# GET CURRENT DOCUMENT
# =========================================================

@app.route(
    "/document",
    methods=["GET"]
)
def get_document():

    try:

        document = get_current_document()

        return jsonify({
            "success": True,
            "document": document
        }), 200

    except Exception as e:

        print(
            "Document status error:",
            str(e)
        )

        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


# =========================================================
# UPLOAD PDF
# =========================================================

@app.route(
    "/upload",
    methods=["POST"]
)
def upload_pdf():

    try:

        # -------------------------------------------------
        # Check existing document
        # -------------------------------------------------

        current_document = (
            get_current_document()
        )

        if current_document:

            return jsonify({
                "success": False,
                "error": (
                    "A document is already uploaded. "
                    "Delete the current document "
                    "before uploading a new PDF."
                )
            }), 400


        # -------------------------------------------------
        # Check file
        # -------------------------------------------------

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


        if not allowed_file(
            file.filename
        ):

            return jsonify({
                "success": False,
                "error": (
                    "Only PDF files are allowed."
                )
            }), 400


        # -------------------------------------------------
        # Save PDF
        # -------------------------------------------------

        filename = file.filename

        pdf_path = os.path.join(
            app.config["UPLOAD_FOLDER"],
            filename
        )


        file.save(
            pdf_path
        )


        print(
            f"\nPDF uploaded: {filename}"
        )

        print(
            "Starting PDF indexing..."
        )


        # -------------------------------------------------
        # Index PDF
        # -------------------------------------------------

        result = index_pdf(
            pdf_path,
            filename
        )


        print(
            "PDF indexing completed."
        )

        print(
            f"Pages: {result.get('pages', 0)}"
        )

        print(
            f"Chunks: {result.get('chunks', 0)}"
        )


        # -------------------------------------------------
        # Save document information
        # -------------------------------------------------

        save_current_document(
            filename=filename,
            file_path=pdf_path,
            pages=result.get(
                "pages",
                0
            ),
            chunks=result.get(
                "chunks",
                0
            )
        )


        return jsonify({

            "success": True,

            "message": (
                "PDF uploaded and indexed "
                "successfully."
            ),

            "filename": filename,

            "pages": result.get(
                "pages",
                0
            ),

            "chunks": result.get(
                "chunks",
                0
            )

        }), 200


    except Exception as e:

        print(
            "\n========== UPLOAD ERROR =========="
        )

        print(
            str(e)
        )

        print(
            "==================================\n"
        )


        return jsonify({

            "success": False,

            "error": str(e)

        }), 500


# =========================================================
# DELETE CURRENT DOCUMENT
# =========================================================

@app.route(
    "/delete-document",
    methods=["DELETE"]
)
def delete_document():

    try:

        document = get_current_document()


        if not document:

            return jsonify({

                "success": False,

                "error": (
                    "No document is currently uploaded."
                )

            }), 404


        # -------------------------------------------------
        # Delete PDF file
        # -------------------------------------------------

        file_path = document[
            "file_path"
        ]


        if os.path.exists(
            file_path
        ):

            os.remove(
                file_path
            )


        # -------------------------------------------------
        # Delete vector database
        # -------------------------------------------------

        clear_vector_database()


        # -------------------------------------------------
        # Delete document metadata
        # -------------------------------------------------

        delete_current_document()


        print(
            f"Deleted document: "
            f"{document['filename']}"
        )


        return jsonify({

            "success": True,

            "message": (
                "Document deleted successfully."
            )

        }), 200


    except Exception as e:

        print(
            "\n========== DELETE ERROR =========="
        )

        print(
            str(e)
        )

        print(
            "==================================\n"
        )


        return jsonify({

            "success": False,

            "error": str(e)

        }), 500


# =========================================================
# CHAT
# =========================================================

@app.route(
    "/chat",
    methods=["POST"]
)
def chat():

    try:

        data = request.get_json(
            silent=True
        )


        if not data:

            return jsonify({

                "success": False,

                "error": (
                    "Request body is empty."
                )

            }), 400


        question = data.get(
            "question",
            ""
        ).strip()


        conversation_id = data.get(
            "conversation_id"
        )


        print(
            "\n========== CHAT REQUEST =========="
        )

        print(
            "Question:",
            question
        )

        print(
            "Conversation:",
            conversation_id
        )

        print(
            "=================================="
        )


        # -------------------------------------------------
        # Question validation
        # -------------------------------------------------

        if not question:

            return jsonify({

                "success": False,

                "error": (
                    "Please enter a question."
                )

            }), 400


        # -------------------------------------------------
        # Check document
        # -------------------------------------------------

        document = get_current_document()


        if not document:

            return jsonify({

                "success": False,

                "error": (
                    "Please upload a PDF "
                    "before asking questions."
                )

            }), 400


        # -------------------------------------------------
        # Conversation
        # -------------------------------------------------

        if not conversation_id:

            conversation_id = (
                create_conversation(
                    "New Chat"
                )
            )


        # -------------------------------------------------
        # Save user message
        # -------------------------------------------------

        save_message(
            conversation_id,
            "user",
            question
        )


        # -------------------------------------------------
        # Generate answer
        # -------------------------------------------------

        result = generate_answer(
            question
        )


        answer = result.get(
            "answer",
            (
                "I couldn't find this information "
                "in the uploaded document."
            )
        )


        sources = result.get(
            "sources",
            []
        )


        # -------------------------------------------------
        # Save assistant message
        # -------------------------------------------------

        save_message(
            conversation_id,
            "assistant",
            answer
        )


        return jsonify({

            "success": True,

            "conversation_id":
                conversation_id,

            "answer":
                answer,

            "sources":
                sources

        }), 200


    except Exception as e:

        print(
            "\n========== CHAT ERROR =========="
        )

        print(
            str(e)
        )

        print(
            "================================\n"
        )


        return jsonify({

            "success": False,

            "error": str(e)

        }), 500


# =========================================================
# NEW CHAT
# =========================================================

@app.route(
    "/new-chat",
    methods=["POST"]
)
def new_chat():

    try:

        conversation_id = (
            create_conversation(
                "New Chat"
            )
        )


        return jsonify({

            "success": True,

            "conversation_id":
                conversation_id

        }), 200


    except Exception as e:

        print(
            "New chat error:",
            str(e)
        )


        return jsonify({

            "success": False,

            "error": str(e)

        }), 500


# =========================================================
# CHAT HISTORY
# =========================================================

@app.route(
    "/history",
    methods=["GET"]
)
def history():

    try:

        conversations = (
            get_conversations()
        )


        result = []


        for conversation in conversations:

            result.append({

                "id":
                    conversation[0],

                "title":
                    conversation[1],

                "created_at":
                    conversation[2]

            })


        return jsonify({

            "success": True,

            "conversations":
                result

        }), 200


    except Exception as e:

        print(
            "History error:",
            str(e)
        )


        return jsonify({

            "success": False,

            "error": str(e)

        }), 500


# =========================================================
# GET CONVERSATION
# =========================================================

@app.route(
    "/history/<conversation_id>",
    methods=["GET"]
)
def conversation(
    conversation_id
):

    try:

        messages = get_messages(
            conversation_id
        )


        result = []


        for message in messages:

            result.append({

                "role":
                    message[0],

                "content":
                    message[1],

                "created_at":
                    message[2]

            })


        return jsonify({

            "success": True,

            "conversation_id":
                conversation_id,

            "messages":
                result

        }), 200


    except Exception as e:

        print(
            "Conversation error:",
            str(e)
        )


        return jsonify({

            "success": False,

            "error": str(e)

        }), 500


# =========================================================
# DELETE CHAT
# =========================================================

@app.route(
    "/history/<conversation_id>",
    methods=["DELETE"]
)
def remove_conversation(
    conversation_id
):

    try:

        delete_conversation(
            conversation_id
        )


        return jsonify({

            "success": True,

            "message":
                "Conversation deleted."

        }), 200


    except Exception as e:

        print(
            "Delete error:",
            str(e)
        )


        return jsonify({

            "success": False,

            "error": str(e)

        }), 500


# =========================================================
# FILE SIZE ERROR
# =========================================================

@app.errorhandler(413)
def file_too_large(error):

    return jsonify({

        "success": False,

        "error": (
            "PDF is too large. "
            "Maximum size is 25 MB."
        )

    }), 413


# =========================================================
# RUN
# =========================================================

if __name__ == "__main__":

    app.run(
        host="127.0.0.1",
        port=5000,
        debug=True
    )
