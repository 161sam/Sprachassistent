from datetime import datetime
import os
from . import BaseSkill

class TimeSkill(BaseSkill):
    intent_name = "time_query"

    def can_handle(self, text: str) -> bool:
        return any(word in text.lower() for word in ["zeit", "uhrzeit", "wie spät"])

    def handle(self, text: str) -> str:
        return f"Es ist {datetime.now().strftime('%H:%M')} Uhr."
