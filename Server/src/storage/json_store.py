import json
import os
from typing import Dict, Any
from src.models.schema import CharacterProfile

class JSONStore:
    def __init__(self, file_path: str):
        self.file_path = file_path
        self._ensure_file()

    def _ensure_file(self):
        if not os.path.exists(self.file_path):
            with open(self.file_path, 'w', encoding='utf-8') as f:
                json.dump({}, f)

    def save_profile(self, profile: CharacterProfile):
        with open(self.file_path, 'w', encoding='utf-8') as f:
            f.write(profile.model_dump_json(indent=2))

    def load_profile(self) -> Dict[str, Any]:
        with open(self.file_path, 'r', encoding='utf-8') as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return {}
