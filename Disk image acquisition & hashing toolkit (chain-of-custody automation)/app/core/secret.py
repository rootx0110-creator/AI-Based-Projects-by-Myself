import base64
import os

SECRET_FILENAME = "custody.secret"


class CustodySecret:
    def __init__(self, data_dir: str):
        self.path = os.path.join(data_dir, SECRET_FILENAME)
        self.load_or_create()

    def load_or_create(self) -> None:
        if os.path.exists(self.path):
            with open(self.path, "r", encoding="ascii") as f:
                self.value = f.read().strip()
        else:
            self.value = base64.b64encode(os.urandom(32)).decode("ascii")
            with open(self.path, "w", encoding="ascii") as f:
                f.write(self.value)
                f.flush()
                os.fsync(f.fileno())

    def get(self) -> str:
        return self.value