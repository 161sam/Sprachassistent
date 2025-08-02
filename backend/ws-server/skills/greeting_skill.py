from . import BaseSkill

class GreetingSkill(BaseSkill):
    intent_name = "greeting"

    def can_handle(self, text: str) -> bool:
        return any(word in text.lower() for word in ["hallo", "hi", "guten tag"])

    def handle(self, text: str) -> str:
        return "Hallo! Wie kann ich Ihnen helfen?"
