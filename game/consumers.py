import json
import asyncio
from channels.generic.websocket import AsyncWebsocketConsumer
from asgiref.sync import sync_to_async
from .models import JapaneseSentence


class GameConsumer(AsyncWebsocketConsumer):
    game_state = {}

    async def connect(self):
        self.room_code = self.scope['url_route']['kwargs']['room_code']
        self.room_group_name = f'game_{self.room_code}'
        self.player_id = self.channel_name

        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()

        # Initialize room state
        if self.room_group_name not in self.game_state:
            self.game_state[self.room_group_name] = {
                'players': [],
                'buzzer_pressed_by': None,
                'question': None,
                'player_scores': {},
                'round_number': 0,
                'used_questions': []
            }

        room = self.game_state[self.room_group_name]
        if self.player_id not in room['players']:
            room['players'].append(self.player_id)
            room['player_scores'][self.player_id] = 0

        # Notify all players of player count
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'player_update',
                'player_count': len(room['players'])
            }
        )

        # Start game automatically when both players are connected
        if len(room['players']) == 2:
            await asyncio.sleep(1)
            await self.start_new_round()

    async def disconnect(self, close_code):
        room = self.game_state.get(self.room_group_name)
        if room:
            if self.player_id in room['players']:
                room['players'].remove(self.player_id)
                room['player_scores'].pop(self.player_id, None)

            # Clean up room if empty
            if not room['players']:
                del self.game_state[self.room_group_name]

        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

    async def receive(self, text_data):
        data = json.loads(text_data)
        msg_type = data['type']
        room = self.game_state[self.room_group_name]

        if msg_type == 'buzzer_press':
            # Only first player to press buzzer gets to answer
            if not room['buzzer_pressed_by']:
                room['buzzer_pressed_by'] = self.player_id
                await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                        'type': 'buzzer_activated',
                        'player_id': self.player_id,
                        'question': room['question']
                    }
                )

        elif msg_type == 'answer_selected':
            answer = data['answer']
            question = room['question']
            is_correct = (answer == question['correct_answer'])

            # Update scores
            if is_correct:
                room['player_scores'][self.player_id] += 1
            else:
                room['player_scores'][self.player_id] -= 1

            # Broadcast result to both players
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'round_result',
                    'is_correct': is_correct,
                    'correct_answer': question['correct_answer'],
                    'scores': room['player_scores'],
                    'answered_by': self.player_id
                }
            )

            asyncio.create_task(self.countdown_and_new_round())

    async def countdown_and_new_round(self):
        """
        Waits for 3 seconds, broadcasting a countdown, then starts a new round.
        """
        await asyncio.sleep(1) # give clients a moment to process the round result
        for i in range(3, 0, -1):
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'next_round_tick',
                    'count': i
                }
            )
            await asyncio.sleep(1)

        await self.start_new_round()

    @sync_to_async
    def get_random_sentence(self, used_questions):
        return JapaneseSentence.objects.exclude(id__in=used_questions).order_by('?').first()

    async def start_new_round(self):
        room = self.game_state[self.room_group_name]
        room['round_number'] += 1

        if room['round_number'] > 10:
            await self.end_game()
            return

        sentence_obj = await self.get_random_sentence(room['used_questions'])

        if not sentence_obj:
            await self.end_game() # End game if no more questions
            return

        room['used_questions'].append(sentence_obj.id)

        if not sentence_obj:
            return

        # Reset buzzer
        room['buzzer_pressed_by'] = None

        question_data = {
            'sentence': sentence_obj.sentence,
            'options': [
                sentence_obj.option1,
                sentence_obj.option2,
                sentence_obj.option3,
                sentence_obj.option4,
            ],
            'correct_answer': sentence_obj.correct_answer
        }
        room['question'] = question_data

        # STEP 1: Announce new round
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'round_starting',
                'scores': room['player_scores']
            }
        )

        # STEP 2: Countdown
        for i in range(3, 0, -1):
            await self.channel_layer.group_send(
                self.room_group_name,
                {'type': 'countdown_tick', 'count': i}
            )
            await asyncio.sleep(1)

        # STEP 3: Send question
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'new_question',
                'question': question_data,
                'scores': room['player_scores']
            }
        )

    # ===================== EVENT HANDLERS =====================

    async def player_update(self, event):
        await self.send(json.dumps({
            'type': 'player_update',
            'player_count': event['player_count']
        }))

    async def round_starting(self, event):
        await self.send(json.dumps({
            'type': 'round_starting',
            'scores': event['scores'],
            'my_id': self.player_id
        }))

    async def countdown_tick(self, event):
        await self.send(json.dumps({
            'type': 'countdown_tick',
            'count': event['count']
        }))

    async def new_question(self, event):
        await self.send(json.dumps({
            'type': 'new_question',
            'question': event['question'],
            'scores': event['scores'],
            'my_id': self.player_id
        }))

    async def buzzer_activated(self, event):
        await self.send(json.dumps({
            'type': 'buzzer_activated',
            'player_id': event['player_id'],
            'my_id': self.player_id,
            'question': event['question']
        }))

    async def round_result(self, event):
        await self.send(json.dumps({
            'type': 'round_result',
            'is_correct': event['is_correct'],
            'correct_answer': event['correct_answer'],
            'scores': event['scores'],
            'answered_by': event['answered_by'],
            'my_id': self.player_id
        })) 

    async def next_round_tick(self, event):
        await self.send(json.dumps({
            'type': 'next_round_tick',
            'count': event['count']
        }))

    async def end_game(self):
        room = self.game_state[self.room_group_name]
        scores = room['player_scores']
        winner = max(scores, key=scores.get) if scores else None

        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'game_over',
                'winner': winner
            }
        )

    async def game_over(self, event):
        await self.send(json.dumps({
            'type': 'game_over',
            'winner': event['winner'],
            'my_id': self.player_id
        }))
