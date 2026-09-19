import os

from flask import Flask, render_template, request, jsonify
from dotenv import load_dotenv

from rag import index_pdf, generate_answer, clear_vector_database

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
# LOAD ENVIRONMENT
# =========================================================

load_dotenv()


# =========================================================
# FLASK APP
# =========================================================

app = Flask(__name__)


# =========================================================
# CONFIGURATION
# =========================================================

UPLOAD_FOLDER = "uploads"

ALLOWED_EXTENSIONS = {"pdf"}

MAX_FILE_SIZE = 25 * 1024 * 1024  # 25 MB


app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["MAX_CONTENT_LENGTH"] = MAX_FILE_SIZE


# =========================================================
# CREATE REQUIRED FOLDERS
# =========================================================

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs("vector_db", exist_ok=True)


# =========================================================
# INITIALIZE DATABASE
# =========================================================

init_db()


# =========================================================
# HELPER FUNCTIONS
# =========================================================

def allowed_file(filename):

    return (
        "." in filename
        and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS
    )


# =========================================================
# HOME
# =========================================================

@app.route("/")
def home():

    return render_template("index.html")


# =========================================================
# GET CURRENT DOCUMENT
# =========================================================

@app.route("/document", methods=["GET"])
def get_document():

    try:

        document = get_current_document()

        if not document:

            return jsonify({
                "success": True,
                "document": None
            })

        return jsonify({
            "success": True,
            "document": {
                "filename": document["filename"],
                "pages": document["pages"],
                "chunks": document["chunks"],
                "uploaded_at": document["uploaded_at"]
            }
        })

    except Exception as e:

        print("DOCUMENT ERROR:")
        print(type(e).__name__)
        print(str(e))

        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


# =========================================================
# UPLOAD PDF
# =========================================================

@app.route("/upload", methods=["POST"])
def upload_pdf():

    pdf_path = None

    try:

        print()
        print("==========================================")
        print("PDF UPLOAD START")
        print("==========================================")


        # -------------------------------------------------
        # CHECK EXISTING DOCUMENT
        # -------------------------------------------------

        current_document = get_current_document()

        if current_document:

            print("Existing document found:")
            print(current_document["filename"])

            return jsonify({
                "success": False,
                "error": (
                    "A PDF is already uploaded. "
                    "Delete the current PDF before uploading another PDF."
                )
            }), 400


        # -------------------------------------------------
        # CHECK FILE
        # -------------------------------------------------

        if "file" not in request.files:

            print("ERROR: No file received")

            return jsonify({
                "success": False,
                "error": "No PDF file was received by the server."
            }), 400


        file = request.files["file"]


        # -------------------------------------------------
        # CHECK FILE NAME
        # -------------------------------------------------

        if file.filename == "":

            print("ERROR: Empty filename")

            return jsonify({
                "success": False,
                "error": "Please select a PDF file."
            }), 400


        # -------------------------------------------------
        # CHECK EXTENSION
        # -------------------------------------------------

        if not allowed_file(file.filename):

            print("ERROR: Invalid file type")

            return jsonify({
                "success": False,
                "error": "Only PDF files are allowed."
            }), 400


        # -------------------------------------------------
        # SAFE FILE NAME
        # -------------------------------------------------

        filename = os.path.basename(file.filename)

        print("Filename:", filename)


        # -------------------------------------------------
        # CREATE UPLOAD DIRECTORY
        # -------------------------------------------------

        os.makedirs(
            app.config["UPLOAD_FOLDER"],
            exist_ok=True
        )


        # -------------------------------------------------
        # SAVE PDF
        # -------------------------------------------------

        pdf_path = os.path.join(
            app.config["UPLOAD_FOLDER"],
            filename
        )

        print("Saving PDF to:")
        print(pdf_path)


        file.save(pdf_path)


        print("PDF SAVED SUCCESSFULLY")


        # -------------------------------------------------
        # CHECK FILE EXISTS
        # -------------------------------------------------

        if not os.path.exists(pdf_path):

            raise Exception(
                "PDF file could not be saved on the server."
            )


        file_size = os.path.getsize(pdf_path)

        print("PDF size:", file_size, "bytes")


        # -------------------------------------------------
        # START PDF INDEXING
        # -------------------------------------------------

        print()
        print("Starting PDF indexing...")
        print("This may take some time for large PDFs.")


        result = index_pdf(
            pdf_path=pdf_path,
            document_name=filename
        )


        print()
        print("PDF INDEXING COMPLETED")

        print("Pages:", result.get("pages", 0))

        print("Chunks:", result.get("chunks", 0))


        # -------------------------------------------------
        # SAVE DOCUMENT INFORMATION
        # -------------------------------------------------

        save_current_document(

            filename=filename,

            file_path=pdf_path,

            pages=result.get("pages", 0),

            chunks=result.get("chunks", 0)
        )


        print("DOCUMENT METADATA SAVED")


        print()
        print("==========================================")
        print("PDF UPLOAD SUCCESS")
        print("==========================================")


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

        print()
        print("==========================================")
        print("PDF UPLOAD ERROR")
        print("==========================================")

        print("Error type:")
        print(type(e).__name__)

        print("Error message:")
        print(str(e))

        print("==========================================")


        # -------------------------------------------------
        # CLEANUP FAILED PDF
        # -------------------------------------------------

        try:

            if pdf_path:

                if os.path.exists(pdf_path):

                    os.remove(pdf_path)

                    print("Failed PDF deleted.")


        except Exception as cleanup_error:

            print("Cleanup error:")
            print(str(cleanup_error))


        return jsonify({

            "success": False,

            "error": "PDF processing failed: " + str(e)

        }), 500


# =========================================================
# DELETE CURRENT PDF
# =========================================================

@app.route("/delete-document", methods=["DELETE"])
def delete_document():

    try:

        print()
        print("==========================================")
        print("DELETE DOCUMENT")
        print("==========================================")


        document = get_current_document()


        # -------------------------------------------------
        # NO DOCUMENT
        # -------------------------------------------------

        if not document:

            return jsonify({

                "success": False,

                "error": "No PDF is currently uploaded."

            }), 404


        # -------------------------------------------------
        # DELETE PDF FILE
        # -------------------------------------------------

        file_path = document["file_path"]


        if os.path.exists(file_path):

            os.remove(file_path)

            print("PDF file deleted:", file_path)


        # -------------------------------------------------
        # DELETE VECTOR DATABASE
        # -------------------------------------------------

        print("Deleting vector database...")

        clear_vector_database()

        print("Vector database deleted.")


        # -------------------------------------------------
        # DELETE DATABASE METADATA
        # -------------------------------------------------

        delete_current_document()

        print("Document metadata deleted.")


        print("==========================================")
        print("DOCUMENT DELETE SUCCESS")
        print("==========================================")


        return jsonify({

            "success": True,

            "message": "PDF deleted successfully."

        })


    except Exception as e:

        print()
        print("DELETE DOCUMENT ERROR")

        print(type(e).__name__)

        print(str(e))


        return jsonify({

            "success": False,

            "error": str(e)

        }), 500


# =========================================================
# CHAT
# =========================================================

@app.route("/chat", methods=["POST"])
def chat():

    try:

        data = request.get_json(silent=True) or {}

        question = data.get("question", "").strip()

        conversation_id = data.get("conversation_id")


        # -------------------------------------------------
        # CHECK QUESTION
        # -------------------------------------------------

        if not question:

            return jsonify({

                "success": False,

                "error": "Please enter a question."

            }), 400


        # -------------------------------------------------
        # CHECK DOCUMENT
        # -------------------------------------------------

        document = get_current_document()

        if not document:

            return jsonify({

                "success": False,

                "error": "Please upload a PDF before asking questions."

            }), 400


        # -------------------------------------------------
        # CREATE CONVERSATION IF NEEDED
        # -------------------------------------------------

        if not conversation_id:

            title = question[:60]

            conversation_id = create_conversation(title)


        # -------------------------------------------------
        # SAVE USER MESSAGE
        # -------------------------------------------------

        save_message(

            conversation_id,

            "user",

            question

        )


        # -------------------------------------------------
        # GENERATE ANSWER
        # -------------------------------------------------

        result = generate_answer(question)


        answer = result.get(

            "answer",

            "I couldn't find this information in the uploaded document."

        )


        sources = result.get(

            "sources",

            []

        )


        # -------------------------------------------------
        # SAVE ASSISTANT MESSAGE
        # -------------------------------------------------

        save_message(

            conversation_id,

            "assistant",

            answer

        )


        # -------------------------------------------------
        # RESPONSE
        # -------------------------------------------------

        return jsonify({

            "success": True,

            "answer": answer,

            "sources": sources,

            "conversation_id": conversation_id

        })


    except Exception as e:

        print()
        print("==========================================")
        print("CHAT ERROR")
        print("==========================================")

        print(type(e).__name__)

        print(str(e))

        print("==========================================")


        return jsonify({

            "success": False,

            "error": "Something went wrong: " + str(e)

        }), 500


# =========================================================
# NEW CHAT
# =========================================================

@app.route("/new-chat", methods=["POST"])
def new_chat():

    try:

        conversation_id = create_conversation("New Chat")

        return jsonify({

            "success": True,

            "conversation_id": conversation_id

        })


    except Exception as e:

        print("NEW CHAT ERROR:", str(e))

        return jsonify({

            "success": False,

            "error": str(e)

        }), 500


# =========================================================
# GET ALL CHAT HISTORY
# =========================================================

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

        })


    except Exception as e:

        print("HISTORY ERROR:", str(e))

        return jsonify({

            "success": False,

            "error": str(e)

        }), 500


# =========================================================
# GET PARTICULAR CHAT
# =========================================================

@app.route("/history/<conversation_id>", methods=["GET"])
def conversation_history(conversation_id):

    try:

        messages = get_messages(conversation_id)


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

        })


    except Exception as e:

        print("CONVERSATION HISTORY ERROR:")
        print(str(e))


        return jsonify({

            "success": False,

            "error": str(e)

        }), 500


# =========================================================
# DELETE CHAT HISTORY
# =========================================================

@app.route("/history/<conversation_id>", methods=["DELETE"])
def remove_conversation(conversation_id):

    try:

        delete_conversation(conversation_id)


        return jsonify({

            "success": True,

            "message": "Conversation deleted successfully."

        })


    except Exception as e:

        print("DELETE CONVERSATION ERROR:")
        print(str(e))


        return jsonify({

            "success": False,

            "error": str(e)

        }), 500


# =========================================================
# FILE TOO LARGE ERROR
# =========================================================

@app.errorhandler(413)
def file_too_large(error):

    return jsonify({

        "success": False,

        "error": "File is too large. Maximum allowed size is 25 MB."

    }), 413


# =========================================================
# GENERAL ERROR HANDLER
# =========================================================

@app.errorhandler(Exception)
def handle_general_error(error):

    print()
    print("==========================================")
    print("GENERAL FLASK ERROR")
    print("==========================================")

    print(type(error).__name__)

    print(str(error))

    print("==========================================")


    return jsonify({

        "success": False,

        "error": "Server error: " + str(error)

    }), 500


# =========================================================
# LOCAL RUN
# =========================================================

if __name__ == "__main__":

    app.run(

        host="0.0.0.0",

        port=int(os.environ.get("PORT", 5000)),

        debug=True

    )
