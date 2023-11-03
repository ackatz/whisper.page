import os
import hashlib
from cryptography.hazmat.primitives.ciphers.aead import ChaCha20Poly1305
from dbo.get_db_connection import get_db_connection
from functions.date_functions import ttl_create_epoch
import bleach
import base64


async def generate_whisper(whisper_content: str, ttl: str):
    ttl_epoch = await ttl_create_epoch(ttl)

    # Sanitize the whisper_content
    cleaned_whisper_content = bleach.clean(whisper_content)

    # Generate a random 256-bit (32-byte) key
    whisper_key = os.urandom(32)
    chacha = ChaCha20Poly1305(whisper_key)
    nonce = os.urandom(12)

    # Encrypt the whisper content
    encrypted_whisper_content = chacha.encrypt(
        nonce, cleaned_whisper_content.encode(), None
    )

    # Generate two SHA256 hashes for the URL
    hash1 = hashlib.sha256(encrypted_whisper_content).hexdigest()
    hash2 = hashlib.sha256(nonce + encrypted_whisper_content + ttl.encode()).hexdigest()

    # Convert whisper_key to a URL-safe string
    url_safe_whisper_key = base64.urlsafe_b64encode(whisper_key).decode()

    # Return the link to the whisper
    link = f"/{hash1}/{hash2}#{url_safe_whisper_key}"

    # Base64-encode the encrypted content and nonce
    encrypted_whisper_content_base64 = base64.b64encode(
        encrypted_whisper_content
    ).decode()
    nonce_base64 = base64.b64encode(nonce).decode()

    return link, hash1, hash2, encrypted_whisper_content_base64, ttl_epoch, nonce_base64


async def store_whisper(
    hash1: str,
    hash2: str,
    encrypted_whisper_content: str,
    ttl: str,
    destruct_upon_viewing: bool,
    nonce: bytes,
):
    with get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO whispers (hash1, hash2, encrypted_whisper_content, ttl, destruct_upon_viewing, nonce) VALUES (?, ?, ?, ?, ?, ?)",
            (
                hash1,
                hash2,
                encrypted_whisper_content,
                ttl,
                destruct_upon_viewing,
                nonce,
            ),
        )
        conn.commit()


async def retrieve_whisper(hash1: str, hash2: str):
    with get_db_connection() as conn:
        cur = conn.cursor()

        # Try to fetch the whisper directly using hash1 and hash2
        whisper = cur.execute(
            "SELECT * FROM whispers WHERE hash1 = ? AND hash2 = ?", (hash1, hash2)
        ).fetchone()

        # If a whisper is found
        if whisper:
            encrypted_whisper_content = whisper["encrypted_whisper_content"]
            ttl = whisper["ttl"]
            destruct_upon_viewing = whisper["destruct_upon_viewing"]
            nonce = whisper["nonce"]

            # Return the encrypted content along with ttl and destruct_upon_viewing flags
            return encrypted_whisper_content, ttl, destruct_upon_viewing, nonce

        raise Exception("Whisper not found")


async def destroy_whisper(hash1: str, hash2: str):
    try:
        with get_db_connection() as conn:
            cur = conn.cursor()

            cur.execute(
                "DELETE FROM whispers WHERE hash1 = ? AND hash2 = ?", (hash1, hash2)
            )
            conn.commit()

            return True

    except Exception as e:
        return False


def scheduled_destroy():
    with get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute("DELETE FROM whispers WHERE ttl < strftime('%s','now')")
        conn.commit()


if __name__ == "__main__":
    scheduled_destroy()
