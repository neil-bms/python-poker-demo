import tkinter as tk
from tkinter import messagebox
from PIL import Image, ImageTk
import random
import threading
import time
import os

class PokerGame:
    def __init__(self, root):
        self.root = root
        self.root.title("Texas Hold'em Poker Game")
        self.player_name = "You"
        self.eeg_color = "black"
        self.setup_gui()
        self.start_eeg_thread()
        self.start_game()

    def setup_gui(self):
        # Load images
        self.load_images()

        # Create canvas for the table
        self.canvas = tk.Canvas(self.root, width=800, height=600, bg="green")
        self.canvas.pack()

        # Draw poker table
        self.canvas.create_image(400, 300, image=self.table_img)

        # Place player avatars
        positions = [(400, 500), (100, 300), (700, 300), (400, 100)]
        self.player_positions = positions
        self.players = []
        names = [self.player_name, "Computer 1", "Computer 2", "Computer 3"]
        for i, pos in enumerate(positions):
            avatar = self.canvas.create_image(pos[0], pos[1], image=self.player_avatar_img)
            name_text = self.canvas.create_text(pos[0], pos[1]+40, text=names[i], fill="black", font=("Arial", 12))
            chips_text = self.canvas.create_text(pos[0], pos[1]+55, text=f"Chips: 1000", fill="yellow", font=("Arial", 12))
            self.players.append({
                'avatar': avatar,
                'name_text': name_text,
                'chips_text': chips_text,
                'position': pos,
                'cards': [],
                'card_imgs': [],
                'chips': 1000,
                'in_game': True,
                'has_folded': False,
                'current_bet': 0
            })

        # Create card and chip holders
        #self.card_images = {}
        self.community_cards_imgs = []
        self.chip_labels = []

        # Betting controls
        self.bet_amount = tk.IntVar(value=10)
        self.create_betting_controls()

    def load_images(self):
        # Load table image
        self.table_img = ImageTk.PhotoImage(Image.open("images/poker_table.png").resize((800, 600)))

        # Load player avatar image
        self.player_avatar_img = ImageTk.PhotoImage(Image.open("images/player_avatar.png").resize((50, 50)))

        # Load card images
        self.card_images = {}
        suits = ['hearts', 'diamonds', 'clubs', 'spades']
        ranks = ['2', '3', '4', '5', '6', '7', '8', '9', '10', 'jack', 'queen', 'king', 'ace']
        missing_images = False
        for suit in suits:
            for rank in ranks:
                card_name = f"{rank}_of_{suit}"
                img_path = f"images/cards/{card_name}.png"
                if os.path.exists(img_path):
                    print(f"FOUND IT: {card_name}")
                    img = Image.open(img_path).resize((72, 96))
                    self.card_images[card_name] = ImageTk.PhotoImage(img)
                else:
                    print(f"Image not found: {img_path}")
                    missing_images = True

        # Load back of card image
        self.card_back_img = ImageTk.PhotoImage(Image.open("images/cards/back.png").resize((72, 96)))

        if missing_images:
            messagebox.showwarning("Warning", "Some card images are missing. Please check the console output for details.")
        print("Keys in self.card_images:")
        for key in self.card_images.keys():
            print(f"'{key}'")

    def create_betting_controls(self):
        # Betting controls frame
        self.controls_frame = tk.Frame(self.root)
        self.controls_frame.pack(pady=10)

        # Bet amount scale
        self.bet_scale = tk.Scale(self.controls_frame, from_=10, to=1000, variable=self.bet_amount, orient=tk.HORIZONTAL, label="Bet Amount")
        self.bet_scale.pack(side=tk.LEFT, padx=10)

        # Betting buttons
        self.call_button = tk.Button(self.controls_frame, text="Call", command=self.player_call)
        self.call_button.pack(side=tk.LEFT, padx=5)

        self.check_button = tk.Button(self.controls_frame, text="Check", command=self.player_check)
        self.check_button.pack(side=tk.LEFT, padx=5)

        self.raise_button = tk.Button(self.controls_frame, text="Raise", command=self.player_raise)
        self.raise_button.pack(side=tk.LEFT, padx=5)

        self.fold_button = tk.Button(self.controls_frame, text="Fold", command=self.player_fold)
        self.fold_button.pack(side=tk.LEFT, padx=5)

    def start_game(self):
        self.deck = self.create_deck()
        self.pot = 0
        self.current_bet = 0
        self.game_round = 'pre-flop'
        self.deal_cards()

    def create_deck(self):
        suits = ['hearts', 'diamonds', 'clubs', 'spades']
        ranks = ['2', '3', '4', '5', '6', '7', '8', '9', '10', 'jack', 'queen', 'king', 'ace']
        deck = [rank + '_of_' + suit for suit in suits for rank in ranks]
        random.shuffle(deck)
        return deck

    def deal_cards(self):
        # Clear previous cards
        for player in self.players:
            for card in player['card_imgs']:
                self.canvas.delete(card)
            player['cards'] = []
            player['card_imgs'] = []
            player['has_folded'] = False
            player['current_bet'] = 0
            player['in_game'] = True

    # Deal two cards to each player
        for i, player in enumerate(self.players):
            card1 = self.deck.pop()
            card2 = self.deck.pop()
            player['cards'] = [card1, card2]
            x_offset = -40 if i == 0 else -20
            if i == 0:
                # Show player's own cards
                card_image1 = self.get_card_image(card1)
                card_image2 = self.get_card_image(card2)
                card_img_id1 = self.canvas.create_image(player['position'][0]+x_offset, player['position'][1]-50, image=card_image1)
                card_img_id2 = self.canvas.create_image(player['position'][0]+x_offset+30, player['position'][1]-50, image=card_image2)
                # Store both the canvas image IDs and the PhotoImage objects
                player['card_imgs'] = [
                    {'id': card_img_id1, 'image': card_image1},
                    {'id': card_img_id2, 'image': card_image2}
                ]
            else:
                # Show back of card for opponents
                card_img_id1 = self.canvas.create_image(player['position'][0]+x_offset, player['position'][1]-50, image=self.card_back_img)
                card_img_id2 = self.canvas.create_image(player['position'][0]+x_offset+30, player['position'][1]-50, image=self.card_back_img)
                player['card_imgs'] = [
                    {'id': card_img_id1, 'image': self.card_back_img},
                    {'id': card_img_id2, 'image': self.card_back_img}
                ]
            # Update chips display
            self.canvas.itemconfig(player['chips_text'], text=f"Chips: {player['chips']}")


        # Clear community cards
        self.community_cards = []
        for img in self.community_cards_imgs:
            self.canvas.delete(img)
        self.community_cards_imgs = []

        # Reset betting variables
        self.pot = 0
        self.current_bet = 0
        self.update_pot_display()
        self.game_round = 'pre-flop'
        self.player_turn = 0  # Index of current player's turn

        # Start the betting round
        self.start_betting_round()

    def get_card_image(self, card_name):
        print(f"Looking for: '{card_name}'")
        print(f"Current keys in self.card_images: {list(self.card_images.keys())}")
        card_image = self.card_images.get(card_name)
        if card_image:
            return card_image
        else:
            print(f"Card image not found for '{card_name}', using back of card.")
            return self.card_back_img


    def update_pot_display(self):
        # Update pot display
        if hasattr(self, 'pot_text'):
            self.canvas.delete(self.pot_text)
        self.pot_text = self.canvas.create_text(400, 250, text=f"Pot: ${self.pot}", fill="white", font=("Arial", 16))

    def start_betting_round(self):
        self.betting_done = False
        self.active_players = [i for i, p in enumerate(self.players) if p['in_game'] and not p['has_folded']]
        self.last_raised = None
        self.last_bet = 0
        self.player_turn = 0
        self.player_action()

    def player_action(self):
        if self.player_turn >= len(self.players):
            self.player_turn = 0

        player = self.players[self.player_turn]

        if player['has_folded'] or not player['in_game']:
            self.player_turn += 1
            self.player_action()
            return

        if self.player_turn == 0:
            # It's the human player's turn
            self.enable_betting_controls()
        else:
            # Computer player's turn
            self.disable_betting_controls()
            self.root.after(1000, self.computer_action)
            return

    def enable_betting_controls(self):
        if self.current_bet == 0:
            self.call_button.config(state=tk.DISABLED)
            self.check_button.config(state=tk.NORMAL)
        else:
            self.call_button.config(state=tk.NORMAL)
            self.check_button.config(state=tk.DISABLED)
        self.raise_button.config(state=tk.NORMAL)
        self.fold_button.config(state=tk.NORMAL)
        self.bet_scale.config(state=tk.NORMAL)

    def disable_betting_controls(self):
        self.call_button.config(state=tk.DISABLED)
        self.check_button.config(state=tk.DISABLED)
        self.raise_button.config(state=tk.DISABLED)
        self.fold_button.config(state=tk.DISABLED)
        self.bet_scale.config(state=tk.DISABLED)

    def player_call(self):
        call_amount = self.current_bet - self.players[0]['current_bet']
        if call_amount > self.players[0]['chips']:
            call_amount = self.players[0]['chips']
        self.players[0]['chips'] -= call_amount
        self.players[0]['current_bet'] += call_amount
        self.pot += call_amount
        self.update_pot_display()
        self.update_player_chips_display(0)
        self.disable_betting_controls()
        self.player_turn += 1
        self.next_action()

    def player_check(self):
        if self.current_bet > 0 and self.players[0]['current_bet'] < self.current_bet:
            messagebox.showwarning("Warning", "You cannot check, you must call, raise, or fold.")
            return
        self.disable_betting_controls()
        self.player_turn += 1
        self.next_action()

    def player_raise(self):
        amount = self.bet_amount.get()
        total_bet = self.current_bet + amount
        bet_diff = total_bet - self.players[0]['current_bet']
        if bet_diff > self.players[0]['chips']:
            messagebox.showwarning("Warning", "You don't have enough chips to raise that amount!")
            return
        self.players[0]['chips'] -= bet_diff
        self.pot += bet_diff
        self.players[0]['current_bet'] = total_bet
        self.current_bet = total_bet
        self.last_raised = self.player_turn
        self.update_pot_display()
        self.update_player_chips_display(0)
        self.disable_betting_controls()
        self.player_turn += 1
        self.next_action()

    def player_fold(self):
        self.players[0]['has_folded'] = True
        self.disable_betting_controls()
        self.player_turn += 1
        self.next_action()

    def computer_action(self):
        player = self.players[self.player_turn]
        # Less aggressive AI logic for demonstration
        call_amount = self.current_bet - player['current_bet']
        if call_amount > player['chips']:
            call_amount = player['chips']
        if self.current_bet == 0:
            action = random.choices(['check', 'raise'], weights=[80, 20])[0]
        else:
            action = random.choices(['call', 'fold', 'raise'], weights=[70, 20, 10])[0]

        if action == 'call':
            player['chips'] -= call_amount
            player['current_bet'] += call_amount
            self.pot += call_amount
            self.update_player_chips_display(self.player_turn)
        elif action == 'check':
            pass
        elif action == 'raise':
            raise_amount = min(random.randint(10, 50), player['chips'])
            total_bet = self.current_bet + raise_amount
            bet_diff = total_bet - player['current_bet']
            player['chips'] -= bet_diff
            self.pot += bet_diff
            player['current_bet'] = total_bet
            self.current_bet = total_bet
            self.last_raised = self.player_turn
            self.update_player_chips_display(self.player_turn)
        elif action == 'fold':
            player['has_folded'] = True

        self.update_pot_display()
        self.player_turn += 1
        self.next_action()

    def update_player_chips_display(self, player_index):
        player = self.players[player_index]
        self.canvas.itemconfig(player['chips_text'], text=f"Chips: {player['chips']}")

    def next_action(self):
        active_players = [p for p in self.players if not p['has_folded'] and p['in_game']]
        if len(active_players) == 1:
            winner = active_players[0]
            winner['chips'] += self.pot
            self.update_player_chips_display(self.players.index(winner))
            messagebox.showinfo("Round Over", f"{self.get_player_name(winner)} wins the pot of ${self.pot}!")
            self.start_game()
            return

        all_players_have_acted = all(
            (p['current_bet'] == self.current_bet or p['has_folded']) for p in self.players if p['in_game']
        )
        if all_players_have_acted and (self.last_raised is None or self.player_turn == self.last_raised):
            # Betting round is over
            self.game_round_progress()
            return

        self.player_action()

    def get_player_name(self, player):
        idx = self.players.index(player)
        return "You" if idx == 0 else f"Computer {idx}"

    def game_round_progress(self):
        # Reset current bets
        for player in self.players:
            player['current_bet'] = 0

        # Progress the game round
        if self.game_round == 'pre-flop':
            self.game_round = 'flop'
            self.deal_community_cards(3)
        elif self.game_round == 'flop':
            self.game_round = 'turn'
            self.deal_community_cards(1)
        elif self.game_round == 'turn':
            self.game_round = 'river'
            self.deal_community_cards(1)
        elif self.game_round == 'river':
            self.showdown()
            return

        # Reset betting variables
        self.current_bet = 0
        self.last_raised = None
        self.player_turn = 0
        self.start_betting_round()

    def deal_community_cards(self, number):
        for _ in range(number):
            card = self.deck.pop()
            self.community_cards.append(card)
            x = 250 + len(self.community_cards) * 75
            y = 300
            card_image = self.get_card_image(card)
            img_id = self.canvas.create_image(x, y, image=card_image)
            # Store both the canvas image ID and the PhotoImage object
            self.community_cards_imgs.append({'id': img_id, 'image': card_image})


    def showdown(self):
        active_players = [p for p in self.players if not p['has_folded'] and p['in_game']]

        # Reveal opponents' cards
        for player in self.players[1:]:
            if not player['has_folded']:
                # Remove back of card images
                for img in player['card_imgs']:
                    self.canvas.delete(img['id'])
                # Display actual cards
                x_offset = -20
                card1, card2 = player['cards']
                card_image1 = self.get_card_image(card1)
                card_image2 = self.get_card_image(card2)
                card_img_id1 = self.canvas.create_image(player['position'][0]+x_offset, player['position'][1]-50, image=card_image1)
                card_img_id2 = self.canvas.create_image(player['position'][0]+x_offset+30, player['position'][1]-50, image=card_image2)
                # Store both the canvas image IDs and the PhotoImage objects
                player['card_imgs'] = [
                    {'id': card_img_id1, 'image': card_image1},
                    {'id': card_img_id2, 'image': card_image2}
                ]

        # Evaluate hands
        best_hand = None
        winners = []
        for player in active_players:
            hand = self.evaluate_hand(player['cards'] + self.community_cards)
            if not best_hand or hand[0] > best_hand[0]:
                best_hand = hand
                winners = [player]
            elif hand[0] == best_hand[0]:
                winners.append(player)
        # Split pot if tie
        pot_share = self.pot // len(winners)
        for winner in winners:
            winner['chips'] += pot_share
            self.update_player_chips_display(self.players.index(winner))
        winner_names = ', '.join([self.get_player_name(winner) for winner in winners])
        messagebox.showinfo("Showdown", f"{winner_names} win(s) the pot of ${self.pot}!")
        self.start_game()

    def evaluate_hand(self, cards):
        # Simplified hand evaluation
        # Returns a tuple with hand strength
        # For demonstration, we'll count the number of pairs
        ranks = [card.split('_of_')[0] for card in cards]
        rank_counts = {}
        for rank in ranks:
            rank_counts[rank] = rank_counts.get(rank, 0) + 1
        counts = list(rank_counts.values())
        if 4 in counts:
            return (7, )  # Four of a kind
        elif 3 in counts and 2 in counts:
            return (6, )  # Full house
        elif 3 in counts:
            return (3, )  # Three of a kind
        elif counts.count(2) == 2:
            return (2, )  # Two pairs
        elif 2 in counts:
            return (1, )  # One pair
        else:
            return (0, )  # High card

    def start_eeg_thread(self):
        # Start a background thread to simulate EEG data updates
        threading.Thread(target=self.update_eeg_data, daemon=True).start()

    def update_eeg_data(self):
        while True:
            # Simulate reading EEG data and updating the username color
            eeg_value = random.randint(0, 100)
            if eeg_value < 33:
                self.eeg_color = "green"
            elif eeg_value < 66:
                self.eeg_color = "orange"
            else:
                self.eeg_color = "red"
            self.canvas.itemconfig(self.players[0]['name_text'], fill=self.eeg_color)
            time.sleep(1)  # Update every second

if __name__ == "__main__":
    root = tk.Tk()
    game = PokerGame(root)
    root.mainloop()
