import hashlib

def hash_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def hash_list(items):
    h = hashlib.sha256()
    for item in items:
        h.update(item.encode("utf-8"))
    return h.hexdigest()
