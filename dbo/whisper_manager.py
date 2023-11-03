import os
import hashlib
from cryptography.hazmat.primitives.ciphers.aead import ChaCha20Poly1305
from dbo.get_db_connection import get_db_connection
from functions.date_functions import ttl_create_epoch
import bleach


async def generate_whisper(whisper_content: str, ttl: str, master_key: bytes):
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

    # Encrypt the whisper key with the master key
    master_chacha = ChaCha20Poly1305(master_key)
    encrypted_whisper_key = master_chacha.encrypt(nonce, whisper_key, None)

    # Generate two SHA256 hashes for the URL
    hash1 = hashlib.sha256(encrypted_whisper_content).hexdigest()
    hash2 = hashlib.sha256(nonce + whisper_content.encode() + ttl.encode()).hexdigest()

    # Return the link to the whisper
    link = f"/{hash1}/{hash2}"

    # Encrypt the link using the master key

    encrypted_link = master_chacha.encrypt(nonce, link.encode(), None)

    return (
        encrypted_whisper_key,
        encrypted_whisper_content,
        link,
        ttl_epoch,
        nonce,
        encrypted_link,
    )


async def store_whisper(
    link: str,
    encrypted_whisper_key: str,
    encrypted_whisper_content: str,
    ttl: str,
    destruct_upon_viewing: bool,
    nonce: bytes,
):
    with get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO whispers (link, encrypted_whisper_key, encrypted_whisper_content, ttl, destruct_upon_viewing, nonce) VALUES (?, ?, ?, ?, ?, ?)",
            (
                link,
                encrypted_whisper_key,
                encrypted_whisper_content,
                ttl,
                destruct_upon_viewing,
                nonce,
            ),
        )
        conn.commit()


async def retrieve_whisper(hash1: str, hash2: str, master_key: bytes):
    incoming_link = f"/{hash1}/{hash2}"

    with get_db_connection() as conn:
        cur = conn.cursor()
        whispers = cur.execute("SELECT * FROM whispers").fetchall()

    for whisper in whispers:
        encrypted_link = whisper["link"]
        nonce = whisper["nonce"]

        try:
            # Decrypt the link with the master key
            master_chacha = ChaCha20Poly1305(master_key)
            decrypted_link = master_chacha.decrypt(nonce, encrypted_link, None).decode()

            # Check if the decrypted link matches the incoming link
            if decrypted_link == incoming_link:
                encrypted_whisper_key = whisper["encrypted_whisper_key"]
                encrypted_whisper_content = whisper["encrypted_whisper_content"]
                ttl = whisper["ttl"]
                destruct_upon_viewing = whisper["destruct_upon_viewing"]

                # Decrypt the whisper key with the master key
                decrypted_whisper_key = master_chacha.decrypt(
                    nonce, encrypted_whisper_key, None
                )

                # Decrypt the whisper content with the decrypted whisper key
                chacha = ChaCha20Poly1305(decrypted_whisper_key)
                decrypted_content = chacha.decrypt(
                    nonce, encrypted_whisper_content, None
                ).decode()

                return decrypted_content, ttl, destruct_upon_viewing

        except Exception as e:
            continue  # Skip to the next record if decryption fails

    raise Exception("Whisper not found or unable to decrypt")


async def destroy_whisper(hash1: str, hash2: str, master_key: bytes):
    incoming_link = f"/{hash1}/{hash2}"

    with get_db_connection() as conn:
        cur = conn.cursor()
        whispers = cur.execute("SELECT * FROM whispers").fetchall()

    for whisper in whispers:
        encrypted_link = whisper["link"]
        nonce = whisper["nonce"]

        try:
            # Decrypt the link with the master key
            master_chacha = ChaCha20Poly1305(master_key)
            decrypted_link = master_chacha.decrypt(nonce, encrypted_link, None).decode()

            # Check if the decrypted link matches the incoming link
            if decrypted_link == incoming_link:
                cur.execute("DELETE FROM whispers WHERE link = ?", (encrypted_link,))
                conn.commit()

                return True

        except Exception as e:
            continue


def scheduled_destroy():
    with get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute("DELETE FROM whispers WHERE ttl < strftime('%s','now')")
        conn.commit()


if __name__ == "__main__":
    scheduled_destroy()
