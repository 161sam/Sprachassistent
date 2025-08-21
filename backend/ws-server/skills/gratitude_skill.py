from . import BaseSkill
import os

class GratitudeSkill(BaseSkill):
    intent_name = "gratitude"

    def can_handle(self, text: str) -> bool:
        return any(word in text.lower() for word in ["danke", "vielen dank"])

    def handle(self, text: str) -> str:
        return "Gern geschehen!"
