from vercel_blob import put, list_blobs
import requests

# Prefijo donde guardamos las notas
BLOB_PREFIX = "notes/"


def sanitize_filename(name: str):
    """
    Limpia el nombre del archivo para evitar
    ataques de path traversal.
    """
    return name.replace("/", "").replace("..", "")


def save_note(filename: str, content: str):
    """
    Guarda una nota en Vercel Blob.
    """

    filename = sanitize_filename(filename)

    path = f"{BLOB_PREFIX}{filename}"

    blob = put(
        path,
        content.encode("utf-8"),
        access="public"
    )

    return blob.url


def read_note(filename: str):
    """
    Lee el contenido de una nota almacenada.
    """

    filename = sanitize_filename(filename)

    path = f"{BLOB_PREFIX}{filename}"

    blobs = list_blobs(prefix=path)

    if not blobs["blobs"]:
        return None

    url = blobs["blobs"][0]["url"]

    response = requests.get(url)

    return response.text


def list_notes():
    """
    Devuelve una lista con los nombres
    de todas las notas almacenadas.
    """

    blobs = list_blobs(prefix=BLOB_PREFIX)

    return [
        blob["pathname"].replace(BLOB_PREFIX, "")
        for blob in blobs["blobs"]
    ]