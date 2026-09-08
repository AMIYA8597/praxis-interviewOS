class DomainClassifier:
    """
    Fast domain classifier separating questions.
    """
    DOMAINS = ["CODING", "ML", "SYSTEM_DESIGN", "BEHAVIORAL", "GENERAL"]

    def classify(self, text: str) -> str:
        text_lower = text.lower()
        if any(word in text_lower for word in ["code", "function", "array", "string", "loop"]):
            return "CODING"
        elif any(word in text_lower for word in ["model", "training", "xgboost", "accuracy"]):
            return "ML"
        elif any(word in text_lower for word in ["architecture", "scale", "database", "cache"]):
            return "SYSTEM_DESIGN"
        elif any(word in text_lower for word in ["tell me about", "conflict", "challenge", "leadership"]):
            return "BEHAVIORAL"
        return "GENERAL"
