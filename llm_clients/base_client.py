from abc import ABC, abstractmethod

class BaseClient(ABC):
    @abstractmethod
    def analyze_and_decide(self, image_base64, user_objective, current_context=None):
        """Analyze screenshot and decide on next action"""
        pass

    @abstractmethod
    def test_connection(self):
        """Test the API connection"""
