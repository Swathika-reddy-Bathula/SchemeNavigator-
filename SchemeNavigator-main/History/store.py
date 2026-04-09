import json
import threading
import time
from pathlib import Path
from typing import Any, Dict, List, Optional


class HistoryStore:
    def __init__(self, file_path: str = "chat_history.json"):
        self.file_path = Path(file_path)
        self.file_path.parent.mkdir(parents=True, exist_ok=True)
        self.lock = threading.Lock()
        if not self.file_path.exists():
            self._write({"conversations": []})

    def _read(self) -> Dict[str, Any]:
        with self.file_path.open("r", encoding="utf-8") as file:
            return json.load(file)

    def _write(self, data: Dict[str, Any]) -> None:
        with self.file_path.open("w", encoding="utf-8") as file:
            json.dump(data, file, ensure_ascii=False, indent=2)

    def list_conversations(self) -> List[Dict[str, Any]]:
        with self.lock:
            data = self._read()
            conversations = data.get("conversations", [])
            return sorted(
                [
                    {
                        "user_id": conversation["user_id"],
                        "title": conversation["title"],
                        "created_at": conversation["created_at"],
                        "updated_at": conversation["updated_at"],
                        "message_count": len(conversation.get("messages", [])),
                    }
                    for conversation in conversations
                ],
                key=lambda item: item["updated_at"],
                reverse=True,
            )

    def get_conversation(self, user_id: str) -> Optional[Dict[str, Any]]:
        with self.lock:
            data = self._read()
            for conversation in data.get("conversations", []):
                if conversation["user_id"] == user_id:
                    return conversation
        return None

    def create_conversation(self, user_id: str, first_user_message: str) -> Dict[str, Any]:
        now = time.time()
        conversation = {
            "user_id": user_id,
            "title": self._make_title(first_user_message),
            "created_at": now,
            "updated_at": now,
            "messages": [],
        }
        with self.lock:
            data = self._read()
            data.setdefault("conversations", []).append(conversation)
            self._write(data)
        return conversation

    def append_message(self, user_id: str, role: str, content: str) -> Dict[str, Any]:
        with self.lock:
            data = self._read()
            conversation = self._find_conversation(data, user_id)
            if conversation is None:
                raise KeyError(f"Conversation {user_id} not found.")

            conversation.setdefault("messages", []).append(
                {
                    "role": role,
                    "content": content,
                    "timestamp": time.time(),
                }
            )
            conversation["updated_at"] = time.time()
            self._write(data)
            return conversation

    def update_conversation(self, user_id: str, title: str) -> Dict[str, Any]:
        with self.lock:
            data = self._read()
            conversation = self._find_conversation(data, user_id)
            if conversation is None:
                raise KeyError(f"Conversation {user_id} not found.")

            conversation["title"] = title.strip() or conversation["title"]
            conversation["updated_at"] = time.time()
            self._write(data)
            return conversation

    def delete_conversation(self, user_id: str) -> bool:
        with self.lock:
            data = self._read()
            conversations = data.get("conversations", [])
            updated = [item for item in conversations if item["user_id"] != user_id]
            if len(updated) == len(conversations):
                return False
            data["conversations"] = updated
            self._write(data)
            return True

    def _find_conversation(self, data: Dict[str, Any], user_id: str) -> Optional[Dict[str, Any]]:
        for conversation in data.get("conversations", []):
            if conversation["user_id"] == user_id:
                return conversation
        return None

    def _make_title(self, text: str, max_length: int = 48) -> str:
        cleaned = " ".join(text.split())
        if len(cleaned) <= max_length:
            return cleaned or "New conversation"
        return f"{cleaned[:max_length - 3].rstrip()}..."
