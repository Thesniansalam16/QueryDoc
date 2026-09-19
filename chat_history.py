import sqlite3
import uuid

from datetime import datetime


DB_NAME = "chat_history.db"


# ============================================================
# CONNECTION
# ============================================================

def get_connection():

    return sqlite3.connect(
        DB_NAME
    )


# ============================================================
# INITIALIZE DATABASE
# ============================================================

def init_db():

    conn = get_connection()

    cursor = conn.cursor()


    # --------------------------------------------------------
    # CONVERSATIONS
    # --------------------------------------------------------

    cursor.execute("""

        CREATE TABLE IF NOT EXISTS conversations (

            id TEXT PRIMARY KEY,

            title TEXT NOT NULL,

            created_at TEXT NOT NULL

        )

    """)


    # --------------------------------------------------------
    # MESSAGES
    # --------------------------------------------------------

    cursor.execute("""

        CREATE TABLE IF NOT EXISTS messages (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            conversation_id TEXT NOT NULL,

            role TEXT NOT NULL,

            content TEXT NOT NULL,

            created_at TEXT NOT NULL

        )

    """)


    # --------------------------------------------------------
    # CURRENT DOCUMENT
    # --------------------------------------------------------

    cursor.execute("""

        CREATE TABLE IF NOT EXISTS current_document (

            id INTEGER PRIMARY KEY CHECK (id = 1),

            filename TEXT NOT NULL,

            file_path TEXT NOT NULL,

            pages INTEGER DEFAULT 0,

            chunks INTEGER DEFAULT 0,

            uploaded_at TEXT NOT NULL

        )

    """)


    conn.commit()

    conn.close()


# ============================================================
# CREATE CONVERSATION
# ============================================================

def create_conversation(
    title="New Chat"
):

    conversation_id = str(
        uuid.uuid4()
    )


    conn = get_connection()

    cursor = conn.cursor()


    cursor.execute("""

        INSERT INTO conversations
        (
            id,
            title,
            created_at
        )

        VALUES (?, ?, ?)

    """, (

        conversation_id,

        title,

        datetime.now().isoformat()

    ))


    conn.commit()

    conn.close()


    return conversation_id


# ============================================================
# SAVE MESSAGE
# ============================================================

def save_message(
    conversation_id,
    role,
    content
):

    conn = get_connection()

    cursor = conn.cursor()


    cursor.execute("""

        INSERT INTO messages
        (
            conversation_id,
            role,
            content,
            created_at
        )

        VALUES (?, ?, ?, ?)

    """, (

        conversation_id,

        role,

        content,

        datetime.now().isoformat()

    ))


    conn.commit()

    conn.close()


# ============================================================
# GET CONVERSATIONS
# ============================================================

def get_conversations():

    conn = get_connection()

    cursor = conn.cursor()


    cursor.execute("""

        SELECT
            id,
            title,
            created_at

        FROM conversations

        ORDER BY created_at DESC

    """)


    conversations = cursor.fetchall()


    conn.close()


    return conversations


# ============================================================
# GET MESSAGES
# ============================================================

def get_messages(
    conversation_id
):

    conn = get_connection()

    cursor = conn.cursor()


    cursor.execute("""

        SELECT
            role,
            content,
            created_at

        FROM messages

        WHERE conversation_id = ?

        ORDER BY id ASC

    """, (
        conversation_id,
    ))


    messages = cursor.fetchall()


    conn.close()


    return messages


# ============================================================
# DELETE CONVERSATION
# ============================================================

def delete_conversation(
    conversation_id
):

    conn = get_connection()

    cursor = conn.cursor()


    cursor.execute("""

        DELETE FROM messages

        WHERE conversation_id = ?

    """, (
        conversation_id,
    ))


    cursor.execute("""

        DELETE FROM conversations

        WHERE id = ?

    """, (
        conversation_id,
    ))


    conn.commit()

    conn.close()


# ============================================================
# SAVE CURRENT DOCUMENT
# ============================================================

def save_current_document(
    filename,
    file_path,
    pages,
    chunks
):

    conn = get_connection()

    cursor = conn.cursor()


    cursor.execute("""

        DELETE FROM current_document

    """)


    cursor.execute("""

        INSERT INTO current_document
        (
            id,
            filename,
            file_path,
            pages,
            chunks,
            uploaded_at
        )

        VALUES
        (
            1,
            ?,
            ?,
            ?,
            ?,
            ?
        )

    """, (

        filename,

        file_path,

        pages,

        chunks,

        datetime.now().isoformat()

    ))


    conn.commit()

    conn.close()


# ============================================================
# GET CURRENT DOCUMENT
# ============================================================

def get_current_document():

    conn = get_connection()

    cursor = conn.cursor()


    cursor.execute("""

        SELECT
            filename,
            file_path,
            pages,
            chunks,
            uploaded_at

        FROM current_document

        WHERE id = 1

    """)


    document = cursor.fetchone()


    conn.close()


    if not document:

        return None


    return {

        "filename":
            document[0],

        "file_path":
            document[1],

        "pages":
            document[2],

        "chunks":
            document[3],

        "uploaded_at":
            document[4]

    }


# ============================================================
# DELETE CURRENT DOCUMENT
# ============================================================

def delete_current_document():

    conn = get_connection()

    cursor = conn.cursor()


    cursor.execute("""

        DELETE FROM current_document

        WHERE id = 1

    """)


    conn.commit()

    conn.close()
