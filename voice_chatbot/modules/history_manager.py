import json
from pathlib import Path
from datetime import datetime
import logging
from typing import List, Dict, Any

logger = logging.getLogger("HistoryManager")

class HistoryManager:
    def __init__(self, history_file: str = "conversation_history.json"):
        self.history_dir = Path("conversation_history")
        self.history_dir.mkdir(exist_ok=True)
        self.history_file = self.history_dir / history_file
        self.history = self._load_history()

    def _load_history(self) -> List[Dict[str, Any]]:
        """Load existing conversation history from file"""
        try:
            if self.history_file.exists():
                with open(self.history_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            return []
        except Exception as e:
            logger.error(f"Error loading history: {e}")
            return []

    def save_conversation(self, conversation: List[tuple]) -> None:
        """Save a new conversation to history"""
        try:
            # Format conversation for storage
            formatted_conv = {
                "timestamp": datetime.now().isoformat(),
                "messages": [
                    {
                        "role": msg[0],
                        "content": msg[1],
                        "audio_file": msg[2]
                    } for msg in conversation
                ]
            }
            
            # Load current history to ensure we have the latest
            self.history = self._load_history()
            
            # Add new conversation
            self.history.append(formatted_conv)
            
            # Save updated history to file
            with open(self.history_file, 'w', encoding='utf-8') as f:
                json.dump(self.history, f, indent=2, ensure_ascii=False)
                
            logger.info("Conversation saved to history")
        except Exception as e:
            logger.error(f"Error saving conversation: {e}")

    def get_all_conversations(self) -> List[Dict[str, Any]]:
        """Retrieve all conversations"""
        return self.history

    def get_recent_conversations(self, limit: int = 5) -> List[Dict[str, Any]]:
        """Retrieve recent conversations"""
        return self.history[-limit:]

    def delete_all_history(self) -> bool:
        """Delete all conversation history and associated audio files"""
        try:
            # Clear the history list
            self.history = []
            
            # Save empty history to file
            with open(self.history_file, 'w', encoding='utf-8') as f:
                json.dump(self.history, f, indent=2, ensure_ascii=False)
            
            # Delete all audio files
            audio_dir = Path("audio_history")
            if audio_dir.exists():
                for audio_file in audio_dir.glob("*.*"):
                    audio_file.unlink()
            
            logger.info("All conversation history deleted successfully")
            return True
        except Exception as e:
            logger.error(f"Error deleting history: {e}")
            return False

    def delete_conversation(self, timestamp: str) -> bool:
        """Delete a specific conversation and its audio files"""
        try:
            # Find the conversation
            conv_to_delete = None
            for conv in self.history:
                if conv['timestamp'] == timestamp:
                    conv_to_delete = conv
                    break
            
            if not conv_to_delete:
                return False
            
            # Remove conversation from history
            self.history.remove(conv_to_delete)
            
            # Delete associated audio files
            for message in conv_to_delete['messages']:
                audio_file = message.get('audio_file')
                if audio_file:
                    audio_path = Path(audio_file)
                    if audio_path.exists():
                        audio_path.unlink()
            
            # Save updated history
            with open(self.history_file, 'w', encoding='utf-8') as f:
                json.dump(self.history, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Conversation from {timestamp} deleted successfully")
            return True
        except Exception as e:
            logger.error(f"Error deleting conversation: {e}")
            return False
