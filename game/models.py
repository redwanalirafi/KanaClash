from django.db import models
import uuid

class GameRoom(models.Model):
    """
    Represents a game room where two players can compete.
    """
    room_code = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)
    # You can add fields to track players if you have a User model
    # player1 = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='player1')
    # player2 = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='player2')

    def __str__(self):
        return str(self.room_code)

class JapaneseSentence(models.Model):
    """
    Stores the Japanese sentence, options, and the correct answer.
    """
    sentence = models.CharField(max_length=255)
    option1 = models.CharField(max_length=100)
    option2 = models.CharField(max_length=100)
    option3 = models.CharField(max_length=100)
    option4 = models.CharField(max_length=100)
    correct_answer = models.CharField(max_length=100)

    def __str__(self):
        return self.sentence
