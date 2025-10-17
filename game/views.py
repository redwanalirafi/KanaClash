from django.shortcuts import render, redirect, get_object_or_404
from .models import GameRoom

def create_or_join_room(request):
    """
    Allows a user to create a new game room or see available rooms to join.
    """
    if request.method == 'POST':
        # Create a new room
        new_room = GameRoom.objects.create()
        return redirect('game_room', room_code=new_room.room_code)

    # For simplicity, we're just showing the option to create.
    # A more advanced version would list active rooms.
    return render(request, 'game/home.html')


def game_room(request, room_code):
    """
    The view for an individual game room.
    """
    room = get_object_or_404(GameRoom, room_code=room_code)
    return render(request, 'game/room.html', {
        'room_code': room.room_code
    })
