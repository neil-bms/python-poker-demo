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

        # Blinds
        self.small_blind = 10
        self.big_blind = 20

        # This tracks who is the dealer. We'll rotate it each new hand.
        self.dealer_position = 0

        self.setup_gui()
        self.start_eeg_thread()

        # Instead of giving each player 1000 chips in a loop,
        # we do it once here so chips persist across hands.
        self.num_players = 4
        self.players_data = []
        for i in range(self.num_players):
            self.players_data.append({
                'chips': 1000,         # starting stack
                'in_game': True,       # if they haven't busted
                'has_folded': False,
                'current_bet': 0,
                'cards': [],
                'card_imgs': []
            })

        # We'll map self.players_data into the UI later in setup_gui()
        self.start_game()

    def setup_gui(self):
        # Load images
        self.load_images()

        # Create canvas for the table
        self.canvas = tk.Canvas(self.root, width=800, height=600, bg="green")
        self.canvas.pack()

        # Draw poker table
        self.canvas.create_image(400, 300, image=self.table_img)

        # Place player avatars (positions are fixed for simplicity)
        positions = [(400, 500), (100, 300), (700, 300), (400, 100)]
        names = [self.player_name, "Computer 1", "Computer 2", "Computer 3"]
        self.players = []
        for i, pos in enumerate(positions):
            # Create player avatar
            avatar = self.canvas.create_image(pos[0], pos[1], image=self.player_avatar_img)

            # Create username text
            name_text = self.canvas.create_text(
                pos[0],
                pos[1] + 40,
                text=names[i],
                fill="black",
                font=("Arial", 12)
            )
            # Put a rectangle behind the username for clarity
            nt_bbox = self.canvas.bbox(name_text)  # (x1, y1, x2, y2)
            name_rect = self.canvas.create_rectangle(
                nt_bbox,
                fill="white",
                outline="black"
            )
            # Make sure the text is above the rectangle
            self.canvas.tag_raise(name_text, name_rect)

            # Create chips text
            chips_text = self.canvas.create_text(
                pos[0],
                pos[1] + 55,
                text=f"Chips: 1000",
                fill="yellow",
                font=("Arial", 12)
            )

            self.players.append({
                'avatar': avatar,
                'name_text': name_text,
                'name_rect': name_rect,  # store reference if you want to update color, etc.
                'chips_text': chips_text,
                'position': pos
            })

        # Community cards and chip holders
        self.community_cards_imgs = []
        self.chip_labels = []

        # Status label (for displaying actions like "Computer 2 folds", etc.)
        self.status_label = tk.Label(self.root, text="", font=("Arial", 14), bg="green", fg="white")
        self.status_label.pack(side=tk.BOTTOM, pady=5)

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
                    img = Image.open(img_path).resize((72, 96))
                    self.card_images[card_name] = ImageTk.PhotoImage(img)
                else:
                    missing_images = True

        # Load back of card image
        self.card_back_img = ImageTk.PhotoImage(Image.open("images/cards/back.png").resize((72, 96)))

        if missing_images:
            messagebox.showwarning("Warning", "Some card images are missing. Please check console output.")

    def create_betting_controls(self):
        # Betting controls frame
        self.controls_frame = tk.Frame(self.root)
        self.controls_frame.pack(pady=10)

        # Bet amount scale
        self.bet_scale = tk.Scale(self.controls_frame, from_=10, to=1000, variable=self.bet_amount,
                                  orient=tk.HORIZONTAL, label="Bet Amount")
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
        """Start (or restart) a new hand."""
        self.deck = self.create_deck()
        self.pot = 0
        self.current_bet = 0

        # Deal cards
        self.deal_cards()

        # Post blinds
        self.post_blinds()

        # Pre-flop
        self.game_round = 'pre-flop'

        # Pre-flop: first to act is left of the big blind
        self.set_initial_player_turn(preflop=True)

        # We track how many actions since last raise
        self.actions_since_last_raise = 0

        # Start betting
        self.start_betting_round()

    def post_blinds(self):
        """Deduct small and big blinds from the appropriate players."""
        sb_idx = (self.dealer_position + 1) % self.num_players
        bb_idx = (self.dealer_position + 2) % self.num_players

        # Small blind
        sb_amount = min(self.players_data[sb_idx]['chips'], self.small_blind)
        self.players_data[sb_idx]['chips'] -= sb_amount
        self.players_data[sb_idx]['current_bet'] = sb_amount
        self.pot += sb_amount

        # Big blind
        bb_amount = min(self.players_data[bb_idx]['chips'], self.big_blind)
        self.players_data[bb_idx]['chips'] -= bb_amount
        self.players_data[bb_idx]['current_bet'] = bb_amount
        self.pot += bb_amount

        # The current_bet (the bet everyone must match) is the big blind
        self.current_bet = bb_amount

        # Update their chip displays
        self.update_player_chips_display(sb_idx)
        self.update_player_chips_display(bb_idx)

    def set_initial_player_turn(self, preflop=True):
        """
        Pre-flop: The first player to act is left of the big blind (UTG).
        Post-flop: The first player to act is left of the dealer.
        """
        if preflop:
            # left of the big blind
            self.player_turn = (self.dealer_position + 3) % self.num_players
        else:
            # left of dealer
            self.player_turn = (self.dealer_position + 1) % self.num_players

    def create_deck(self):
        suits = ['hearts', 'diamonds', 'clubs', 'spades']
        ranks = ['2', '3', '4', '5', '6', '7', '8', '9', '10', 'jack', 'queen', 'king', 'ace']
        deck = [rank + '_of_' + suit for suit in suits for rank in ranks]
        random.shuffle(deck)
        return deck

    def deal_cards(self):
        """Deal two cards to each player. Clear old community cards, etc."""
        # Clear old community cards from the canvas
        for img_info in self.community_cards_imgs:
            self.canvas.delete(img_info['id'])
        self.community_cards_imgs = []
        self.community_cards = []

        # Reset everyone's per-hand data
        for i, p_data in enumerate(self.players_data):
            p_data['has_folded'] = False
            p_data['current_bet'] = 0
            p_data['cards'] = []
            for card_info in p_data['card_imgs']:
                self.canvas.delete(card_info['id'])
            p_data['card_imgs'] = []

        # Actually deal
        for i, p_data in enumerate(self.players_data):
            if p_data['chips'] <= 0:
                # If a player is busted, skip dealing them cards
                p_data['in_game'] = False
                continue
            else:
                p_data['in_game'] = True

            # Two cards from the deck
            card1 = self.deck.pop()
            card2 = self.deck.pop()
            p_data['cards'] = [card1, card2]

            # Place images on the table
            x_offset = -40 if i == 0 else -20
            if i == 0:
                # Show player's own cards
                card_image1 = self.get_card_image(card1)
                card_image2 = self.get_card_image(card2)
                cid1 = self.canvas.create_image(
                    self.players[i]['position'][0] + x_offset,
                    self.players[i]['position'][1] - 50,
                    image=card_image1
                )
                cid2 = self.canvas.create_image(
                    self.players[i]['position'][0] + x_offset + 30,
                    self.players[i]['position'][1] - 50,
                    image=card_image2
                )
                p_data['card_imgs'] = [
                    {'id': cid1, 'image': card_image1},
                    {'id': cid2, 'image': card_image2}
                ]
            else:
                # Show back of card for opponents
                cid1 = self.canvas.create_image(
                    self.players[i]['position'][0] + x_offset,
                    self.players[i]['position'][1] - 50,
                    image=self.card_back_img
                )
                cid2 = self.canvas.create_image(
                    self.players[i]['position'][0] + x_offset + 30,
                    self.players[i]['position'][1] - 50,
                    image=self.card_back_img
                )
                p_data['card_imgs'] = [
                    {'id': cid1, 'image': self.card_back_img},
                    {'id': cid2, 'image': self.card_back_img}
                ]

            # Update chips display
            self.update_player_chips_display(i)

        self.update_pot_display()

    def get_card_image(self, card_name):
        card_image = self.card_images.get(card_name, None)
        if card_image:
            return card_image
        else:
            # Fallback if missing
            return self.card_back_img

    def update_pot_display(self):
        """Display the pot text (with a box behind it) at a slightly higher position."""
        # If we already have a pot_text or pot_rect, remove them
        if hasattr(self, 'pot_text'):
            self.canvas.delete(self.pot_text)
        if hasattr(self, 'pot_rect'):
            self.canvas.delete(self.pot_rect)

        # Move the pot a bit higher to avoid overlap
        x, y = 400, 220
        self.pot_text = self.canvas.create_text(x, y, text=f"Pot: ${self.pot}",
                                                fill="white", font=("Arial", 16))

        # Create a rectangle behind the pot text
        pt_bbox = self.canvas.bbox(self.pot_text)  # (x1, y1, x2, y2)
        self.pot_rect = self.canvas.create_rectangle(
            pt_bbox,
            fill="darkblue",
            outline="white",
            width=2
        )
        # Raise the pot text above the rectangle
        self.canvas.tag_raise(self.pot_text, self.pot_rect)

    def start_betting_round(self):
        # Identify active players
        self.active_players = [i for i, p in enumerate(self.players_data)
                               if p['in_game'] and not p['has_folded'] and p['chips'] > 0]
        self.player_action()

    def player_action(self):
        """Decides whose turn it is and enables/disables user interface accordingly."""
        # If we go beyond the last index, wrap around
        if self.player_turn >= self.num_players:
            self.player_turn = 0

        p_data = self.players_data[self.player_turn]

        # If folded/out of chips/not in game, skip them
        if (not p_data['in_game']) or p_data['has_folded'] or (p_data['chips'] <= 0):
            self.player_turn += 1
            self.player_action()
            return

        # Human player's turn is index 0
        if self.player_turn == 0:
            self.enable_betting_controls()
        else:
            self.disable_betting_controls()
            # Random delay for simulating "thinking time"
            delay_ms = random.randint(3, 8) * 1000
            self.root.after(delay_ms, self.computer_action_step)

    def enable_betting_controls(self):
        # If current bet is 0, there's nothing to call, so "Check" is valid, "Call" is not
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
        p_data = self.players_data[0]
        call_amount = self.current_bet - p_data['current_bet']
        if call_amount > p_data['chips']:
            call_amount = p_data['chips']  # all-in

        p_data['chips'] -= call_amount
        p_data['current_bet'] += call_amount
        self.pot += call_amount
        self.update_pot_display()
        self.update_player_chips_display(0)
        self.disable_betting_controls()

        self.actions_since_last_raise += 1
        self.player_turn += 1
        self.next_action()

    def player_check(self):
        p_data = self.players_data[0]
        if self.current_bet > p_data['current_bet']:
            messagebox.showwarning("Warning", "You cannot check here—you must call, raise, or fold.")
            return

        self.status_label.config(text="You check.")
        self.disable_betting_controls()

        self.actions_since_last_raise += 1
        self.player_turn += 1
        self.next_action()

    def player_raise(self):
        p_data = self.players_data[0]
        amount = self.bet_amount.get()
        total_bet = self.current_bet + amount
        bet_diff = total_bet - p_data['current_bet']

        if bet_diff > p_data['chips']:
            messagebox.showwarning("Warning", "Not enough chips for that raise!")
            return

        # Deduct from user
        p_data['chips'] -= bet_diff
        p_data['current_bet'] = total_bet
        # Update pot
        self.pot += bet_diff
        # New current bet
        self.current_bet = total_bet

        self.update_pot_display()
        self.update_player_chips_display(0)
        self.disable_betting_controls()

        # This is a raise—reset since last raise
        self.actions_since_last_raise = 0

        self.player_turn += 1
        self.next_action()

    def player_fold(self):
        p_data = self.players_data[0]
        p_data['has_folded'] = True
        self.disable_betting_controls()

        self.actions_since_last_raise += 1
        self.player_turn += 1
        self.next_action()

    def computer_action_step(self):
        """
        This function handles the computer's betting logic.
        We also display the amount called or raised in the status message.
        """
        p_data = self.players_data[self.player_turn]
        comp_name = f"Computer {self.player_turn}"

        call_amount = self.current_bet - p_data['current_bet']
        if call_amount > p_data['chips']:
            call_amount = p_data['chips']  # all-in

        # Very simple weighted logic
        if self.current_bet == 0:
            # If nobody bet yet, 80% chance check, 20% chance raise
            action = random.choices(['check', 'raise'], weights=[80, 20])[0]
        else:
            # If there's a bet, 70% call, 20% fold, 10% raise
            action = random.choices(['call', 'fold', 'raise'], weights=[70, 20, 10])[0]

        if action == 'call':
            p_data['chips'] -= call_amount
            p_data['current_bet'] += call_amount
            self.pot += call_amount
            self.update_player_chips_display(self.player_turn)
            # Show the amount called in the status
            self.status_label.config(text=f"{comp_name} calls {call_amount}.")
            self.actions_since_last_raise += 1

        elif action == 'check':
            self.status_label.config(text=f"{comp_name} checks.")
            self.actions_since_last_raise += 1

        elif action == 'raise':
            raise_amount = min(random.randint(10, 50), p_data['chips'])
            total_bet = self.current_bet + raise_amount
            bet_diff = total_bet - p_data['current_bet']
            p_data['chips'] -= bet_diff
            p_data['current_bet'] = total_bet
            self.pot += bet_diff
            self.current_bet = total_bet
            self.update_player_chips_display(self.player_turn)
            # Show the raise amount and new total in the status
            self.status_label.config(
                text=f"{comp_name} raises {raise_amount} (to {total_bet})."
            )
            # This is a new raise
            self.actions_since_last_raise = 0

        elif action == 'fold':
            p_data['has_folded'] = True
            self.status_label.config(text=f"{comp_name} folds.")
            self.actions_since_last_raise += 1

        self.update_pot_display()
        self.player_turn += 1
        self.next_action()

    def update_player_chips_display(self, idx):
        self.canvas.itemconfig(
            self.players[idx]['chips_text'],
            text=f"Chips: {self.players_data[idx]['chips']}"
        )

    def next_action(self):
        # 1) Check if only one player remains
        active_players = [i for i, p in enumerate(self.players_data)
                          if p['in_game'] and not p['has_folded'] and p['chips'] > 0]
        if len(active_players) == 1:
            winner_idx = active_players[0]
            self.players_data[winner_idx]['chips'] += self.pot
            self.update_player_chips_display(winner_idx)
            messagebox.showinfo("Round Over",
                                f"{self.get_player_name(winner_idx)} wins the pot of ${self.pot}!")
            self.status_label.config(text="")
            self.end_of_hand()
            return

        # 2) If every active player has acted since the last raise, end the betting round
        if self.actions_since_last_raise >= len(active_players):
            self.game_round_progress()
            return

        # 3) Otherwise, go to next player
        self.player_action()

    def get_player_name(self, idx):
        if idx == 0:
            return "You"
        else:
            return f"Computer {idx}"

    def game_round_progress(self):
        # Reset current bets
        for p_data in self.players_data:
            p_data['current_bet'] = 0

        if self.game_round == 'pre-flop':
            self.game_round = 'flop'
            self.deal_community_cards(3)
            # Post-flop: first to act is left of dealer
            self.set_initial_player_turn(preflop=False)

        elif self.game_round == 'flop':
            self.game_round = 'turn'
            self.deal_community_cards(1)
            self.set_initial_player_turn(preflop=False)

        elif self.game_round == 'turn':
            self.game_round = 'river'
            self.deal_community_cards(1)
            self.set_initial_player_turn(preflop=False)

        elif self.game_round == 'river':
            self.showdown()
            return

        # Prepare for next betting round
        self.current_bet = 0
        self.actions_since_last_raise = 0
        self.start_betting_round()

    def deal_community_cards(self, number):
        for _ in range(number):
            card = self.deck.pop()
            self.community_cards.append(card)
            x = 250 + len(self.community_cards) * 75
            y = 300
            card_image = self.get_card_image(card)
            cid = self.canvas.create_image(x, y, image=card_image)
            self.community_cards_imgs.append({'id': cid, 'image': card_image})

    def showdown(self):
        active_players = [i for i, p in enumerate(self.players_data)
                          if p['in_game'] and not p['has_folded'] and p['chips'] > 0]

        # Reveal opponents' cards
        for i in active_players:
            if i != 0:  # skip human (already sees own)
                p_data = self.players_data[i]
                # Remove back-of-card images
                for img_info in p_data['card_imgs']:
                    self.canvas.delete(img_info['id'])
                # Show actual cards
                x_offset = -20
                card1, card2 = p_data['cards']
                card_image1 = self.get_card_image(card1)
                card_image2 = self.get_card_image(card2)
                cid1 = self.canvas.create_image(
                    self.players[i]['position'][0] + x_offset,
                    self.players[i]['position'][1] - 50,
                    image=card_image1
                )
                cid2 = self.canvas.create_image(
                    self.players[i]['position'][0] + x_offset + 30,
                    self.players[i]['position'][1] - 50,
                    image=card_image2
                )
                p_data['card_imgs'] = [
                    {'id': cid1, 'image': card_image1},
                    {'id': cid2, 'image': card_image2}
                ]

        # Evaluate each active player's best "score"
        best_score = None
        winners = []
        for i in active_players:
            score = self.evaluate_hand(self.players_data[i]['cards'] + self.community_cards)
            if not best_score or score[0] > best_score[0]:
                best_score = score
                winners = [i]
            elif score[0] == best_score[0]:
                winners.append(i)

        # Split pot if tie
        share = self.pot // len(winners)
        for w_idx in winners:
            self.players_data[w_idx]['chips'] += share
            self.update_player_chips_display(w_idx)

        names = ", ".join(self.get_player_name(idx) for idx in winners)
        messagebox.showinfo("Showdown", f"{names} win(s) the pot of ${self.pot}!")
        self.status_label.config(text="")

        self.end_of_hand()

    def end_of_hand(self):
        """Rotate the dealer, start a new hand, but keep chip counts."""
        self.dealer_position = (self.dealer_position + 1) % self.num_players
        self.start_game()

    def evaluate_hand(self, cards):
        """
        Very simple: 
        (7) four of a kind, (6) full house, (3) three of a kind,
        (2) two pairs, (1) one pair, (0) high card
        """
        ranks = [c.split('_of_')[0] for c in cards]
        rank_counts = {}
        for r in ranks:
            rank_counts[r] = rank_counts.get(r, 0) + 1
        counts = list(rank_counts.values())
        if 4 in counts:
            return (7,)
        elif 3 in counts and 2 in counts:
            return (6,)
        elif 3 in counts:
            return (3,)
        elif counts.count(2) == 2:
            return (2,)
        elif 2 in counts:
            return (1,)
        else:
            return (0,)

    def start_eeg_thread(self):
        # Start a background thread to simulate EEG data updates
        threading.Thread(target=self.update_eeg_data, daemon=True).start()

    def update_eeg_data(self):
        """
        This simulates EEG color changes for the player at index 0
        (the human). For demonstration, we randomly pick a color each time.
        """
        while True:
            eeg_value = random.randint(0, 100)
            if eeg_value < 33:
                self.eeg_color = "green"
            elif eeg_value < 66:
                self.eeg_color = "orange"
            else:
                self.eeg_color = "red"
            self.canvas.itemconfig(self.players[0]['name_text'], fill=self.eeg_color)
            time.sleep(1)

if __name__ == "__main__":
    root = tk.Tk()
    game = PokerGame(root)
    root.mainloop()
