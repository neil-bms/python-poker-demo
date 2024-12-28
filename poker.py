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

        # We'll store the base name and append the EEG state in parentheses.
        self.base_player_name = "PokerStar121"
        self.player_name = self.base_player_name

        self.eeg_color = "black"

        # Blinds
        self.small_blind = 10
        self.big_blind = 20

        # Who is dealer
        self.dealer_position = 0

        # Setup UI
        self.setup_gui()
        self.start_eeg_thread()

        # We have 4 players total
        self.num_players = 4
        self.players_data = []
        for _ in range(self.num_players):
            self.players_data.append({
                'chips': 1000,
                'in_game': True,
                'has_folded': False,
                'current_bet': 0,
                'cards': [],
                'card_imgs': []
            })

        # Start first hand
        self.start_new_hand()

    def setup_gui(self):
        self.load_images()

        # Main canvas
        self.canvas = tk.Canvas(self.root, width=800, height=600, bg="green")
        self.canvas.pack()

        # Draw table background
        self.canvas.create_image(400, 300, image=self.table_img)

        # Player seats
        positions = [(400, 500), (100, 300), (700, 300), (400, 100)]
        names = [self.player_name, "DarkNite12", "RavensFan08", "AAWizard17"]
        self.players = []
        for i, pos in enumerate(positions):
            avatar = self.canvas.create_image(pos[0], pos[1], image=self.player_avatar_img)

            name_text = self.canvas.create_text(
                pos[0], pos[1] + 40,
                text=names[i],
                fill="black",
                font=("Arial", 12)
            )
            nt_bbox = self.canvas.bbox(name_text)
            name_rect = self.canvas.create_rectangle(nt_bbox, fill="white", outline="black")
            self.canvas.tag_raise(name_text, name_rect)

            chips_text = self.canvas.create_text(
                pos[0], pos[1] + 55,
                text="Chips: 1000",
                fill="yellow",
                font=("Arial", 12)
            )

            self.players.append({
                'avatar': avatar,
                'name_text': name_text,
                'name_rect': name_rect,
                'chips_text': chips_text,
                'position': pos
            })

        # Community cards
        self.community_cards_imgs = []
        self.community_cards = []

        # Status label
        self.status_label = tk.Label(self.root, text="", font=("Arial", 14),
                                     bg="green", fg="white")
        self.status_label.pack(side=tk.BOTTOM, pady=5)

        # Betting controls
        self.bet_amount = tk.IntVar(value=10)
        self.create_betting_controls()

    def load_images(self):
        # Table
        self.table_img = ImageTk.PhotoImage(Image.open("images/poker_table.png").resize((800, 600)))

        # Avatar
        self.player_avatar_img = ImageTk.PhotoImage(Image.open("images/player_avatar.png").resize((50, 50)))

        # Cards
        self.card_images = {}
        suits = ['hearts', 'diamonds', 'clubs', 'spades']
        ranks = ['2', '3', '4', '5', '6', '7', '8', '9', '10',
                 'jack', 'queen', 'king', 'ace']
        missing = False
        for suit in suits:
            for rank in ranks:
                cname = f"{rank}_of_{suit}"
                path = f"images/cards/{cname}.png"
                if os.path.exists(path):
                    img = Image.open(path).resize((72, 96))
                    self.card_images[cname] = ImageTk.PhotoImage(img)
                else:
                    missing = True

        self.card_back_img = ImageTk.PhotoImage(Image.open("images/cards/back.png").resize((72, 96)))

        if missing:
            messagebox.showwarning("Warning", "Some card images are missing.")

    def create_betting_controls(self):
        self.controls_frame = tk.Frame(self.root, bg="green")
        self.controls_frame.pack(pady=10)

        self.bet_scale = tk.Scale(self.controls_frame, from_=10, to=1000,
                                  variable=self.bet_amount,
                                  orient=tk.HORIZONTAL, label="Bet Amount")
        self.bet_scale.pack(side=tk.LEFT, padx=10)

        self.call_button = tk.Button(self.controls_frame, text="Call", command=self.player_call)
        self.call_button.pack(side=tk.LEFT, padx=5)

        self.check_button = tk.Button(self.controls_frame, text="Check", command=self.player_check)
        self.check_button.pack(side=tk.LEFT, padx=5)

        self.raise_button = tk.Button(self.controls_frame, text="Raise", command=self.player_raise)
        self.raise_button.pack(side=tk.LEFT, padx=5)

        self.fold_button = tk.Button(self.controls_frame, text="Fold", command=self.player_fold)
        self.fold_button.pack(side=tk.LEFT, padx=5)

    def start_new_hand(self):
        """Reset pot, deal fresh cards, post blinds, and begin the first betting round."""
        self.deck = self.create_deck()
        self.pot = 0
        self.current_bet = 0

        self.deal_cards()
        self.post_blinds()

        # Start pre-flop
        self.game_round = 'pre-flop'
        self.set_initial_player_turn(preflop=True)
        self.actions_since_last_raise = 0

        self.start_betting_round()

    def post_blinds(self):
        sb_idx = (self.dealer_position + 1) % self.num_players
        bb_idx = (self.dealer_position + 2) % self.num_players

        sb_amount = min(self.players_data[sb_idx]['chips'], self.small_blind)
        self.players_data[sb_idx]['chips'] -= sb_amount
        self.players_data[sb_idx]['current_bet'] = sb_amount
        self.pot += sb_amount

        bb_amount = min(self.players_data[bb_idx]['chips'], self.big_blind)
        self.players_data[bb_idx]['chips'] -= bb_amount
        self.players_data[bb_idx]['current_bet'] = bb_amount
        self.pot += bb_amount

        self.current_bet = bb_amount
        self.update_player_chips_display(sb_idx)
        self.update_player_chips_display(bb_idx)

        self.update_pot_display()

    def set_initial_player_turn(self, preflop=True):
        if preflop:
            # Left of the big blind
            self.player_turn = (self.dealer_position + 3) % self.num_players
        else:
            # Left of the dealer
            self.player_turn = (self.dealer_position + 1) % self.num_players

    def create_deck(self):
        suits = ['hearts', 'diamonds', 'clubs', 'spades']
        ranks = ['2', '3', '4', '5', '6', '7', '8', '9', '10',
                 'jack', 'queen', 'king', 'ace']
        deck = [f"{rank}_of_{suit}" for suit in suits for rank in ranks]
        random.shuffle(deck)
        return deck

    def deal_cards(self):
        """Deal 2 cards each and clear old community cards / images."""
        for cinfo in self.community_cards_imgs:
            self.canvas.delete(cinfo['id'])
        self.community_cards_imgs.clear()
        self.community_cards.clear()

        for i, p_data in enumerate(self.players_data):
            p_data['has_folded'] = False
            p_data['current_bet'] = 0
            p_data['cards'].clear()

            # Remove old card images
            for cimg in p_data['card_imgs']:
                self.canvas.delete(cimg['id'])
            p_data['card_imgs'].clear()

        for i, p_data in enumerate(self.players_data):
            if p_data['chips'] <= 0:
                p_data['in_game'] = False
                continue
            else:
                p_data['in_game'] = True

            c1 = self.deck.pop()
            c2 = self.deck.pop()
            p_data['cards'] = [c1, c2]

            x_offset = -40 if i == 0 else -20
            if i == 0:
                # Show player's own cards
                i1 = self.get_card_image(c1)
                i2 = self.get_card_image(c2)
                cid1 = self.canvas.create_image(
                    self.players[i]['position'][0] + x_offset,
                    self.players[i]['position'][1] - 50,
                    image=i1
                )
                cid2 = self.canvas.create_image(
                    self.players[i]['position'][0] + x_offset + 30,
                    self.players[i]['position'][1] - 50,
                    image=i2
                )
                p_data['card_imgs'] = [
                    {'id': cid1, 'image': i1},
                    {'id': cid2, 'image': i2}
                ]
            else:
                # Opponents => back-of-card
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

            self.update_player_chips_display(i)

        self.update_pot_display()

    def get_card_image(self, card_name):
        return self.card_images.get(card_name, self.card_back_img)

    def update_pot_display(self):
        if hasattr(self, 'pot_text'):
            self.canvas.delete(self.pot_text)
        if hasattr(self, 'pot_rect'):
            self.canvas.delete(self.pot_rect)

        x, y = 400, 220
        pstr = f"Pot: ${self.pot}"
        self.pot_text = self.canvas.create_text(x, y, text=pstr,
                                                fill="white", font=("Arial", 16))
        bbox = self.canvas.bbox(self.pot_text)
        self.pot_rect = self.canvas.create_rectangle(bbox, fill="darkblue", outline="white", width=2)
        self.canvas.tag_raise(self.pot_text, self.pot_rect)

    # --------------------------------------------------------------------------
    # Betting Rounds
    # --------------------------------------------------------------------------

    def start_betting_round(self):
        self.active_players = [
            i for i, p in enumerate(self.players_data)
            if p['in_game'] and not p['has_folded'] and p['chips'] > 0
        ]
        self.player_action()

    def player_action(self):
        if self.player_turn >= self.num_players:
            self.player_turn = 0

        p_data = self.players_data[self.player_turn]
        if (not p_data['in_game']) or p_data['has_folded'] or (p_data['chips'] <= 0):
            self.player_turn += 1
            self.player_action()
            return

        if self.player_turn == 0:  # human
            self.enable_betting_controls()
        else:
            self.disable_betting_controls()
            delay_ms = random.randint(2, 4) * 1000
            self.root.after(delay_ms, self.computer_action_step)

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

    # --------------------------------------------------------------------------
    # Player actions
    # --------------------------------------------------------------------------

    def player_call(self):
        pd = self.players_data[0]
        c_amt = self.current_bet - pd['current_bet']
        if c_amt > pd['chips']:
            c_amt = pd['chips']

        pd['chips'] -= c_amt
        pd['current_bet'] += c_amt
        self.pot += c_amt

        self.update_pot_display()
        self.update_player_chips_display(0)
        self.disable_betting_controls()

        self.actions_since_last_raise += 1
        self.player_turn += 1
        self.next_action()

    def player_check(self):
        pd = self.players_data[0]
        if self.current_bet > pd['current_bet']:
            messagebox.showwarning("Warning", "You cannot check here—you must call, raise, or fold.")
            return
        self.status_label.config(text="You check.")
        self.disable_betting_controls()

        self.actions_since_last_raise += 1
        self.player_turn += 1
        self.next_action()

    def player_raise(self):
        pd = self.players_data[0]
        amt = self.bet_amount.get()
        new_total = self.current_bet + amt
        diff = new_total - pd['current_bet']

        if diff > pd['chips']:
            messagebox.showwarning("Warning", "Not enough chips to raise!")
            return

        pd['chips'] -= diff
        pd['current_bet'] = new_total
        self.pot += diff
        self.current_bet = new_total

        self.update_pot_display()
        self.update_player_chips_display(0)
        self.disable_betting_controls()

        self.actions_since_last_raise = 0
        self.player_turn += 1
        self.next_action()

    def player_fold(self):
        pd = self.players_data[0]
        pd['has_folded'] = True
        self.disable_betting_controls()

        self.actions_since_last_raise += 1
        self.player_turn += 1
        self.next_action()

    # --------------------------------------------------------------------------
    # Computer actions
    # --------------------------------------------------------------------------

    def computer_action_step(self):
        pd = self.players_data[self.player_turn]
        comp_names = ["DarkNite12", "RavensFan08", "AAWizard17"]
        cname = comp_names[self.player_turn - 1]

        call_amt = self.current_bet - pd['current_bet']
        if call_amt > pd['chips']:
            call_amt = pd['chips']

        if self.current_bet == 0:
            # 80% check, 20% raise
            action = random.choices(['check', 'raise'], weights=[80, 20])[0]
        else:
            # 70% call, 20% fold, 10% raise
            action = random.choices(['call', 'fold', 'raise'], weights=[70, 20, 10])[0]

        if action == 'call':
            pd['chips'] -= call_amt
            pd['current_bet'] += call_amt
            self.pot += call_amt
            self.update_player_chips_display(self.player_turn)
            self.status_label.config(text=f"{cname} calls ${call_amt}.")
            self.actions_since_last_raise += 1

        elif action == 'check':
            self.status_label.config(text=f"{cname} checks.")
            self.actions_since_last_raise += 1

        elif action == 'raise':
            r_amt = min(random.randint(10, 50), pd['chips'])
            new_total = self.current_bet + r_amt
            diff = new_total - pd['current_bet']
            pd['chips'] -= diff
            pd['current_bet'] = new_total
            self.pot += diff
            self.current_bet = new_total
            self.update_player_chips_display(self.player_turn)
            self.status_label.config(text=f"{cname} raises ${r_amt} (to ${new_total}).")
            self.actions_since_last_raise = 0

        elif action == 'fold':
            pd['has_folded'] = True
            self.status_label.config(text=f"{cname} folds.")
            self.actions_since_last_raise += 1

        self.update_pot_display()
        self.player_turn += 1
        self.next_action()

    # --------------------------------------------------------------------------
    # Round Flow
    # --------------------------------------------------------------------------

    def update_player_chips_display(self, idx):
        self.canvas.itemconfig(
            self.players[idx]['chips_text'],
            text=f"Chips: {self.players_data[idx]['chips']}"
        )

    def next_action(self):
        active = [
            i for i, p in enumerate(self.players_data)
            if p['in_game'] and not p['has_folded'] and p['chips'] > 0
        ]

        # 1) If only one player remains
        if len(active) == 1:
            winner_idx = active[0]

            # *** Approach: Reveal all, then forcibly WAIT so user can see ***
            self.reveal_all_computers_and_pause(lambda: self.finish_single_player_win(winner_idx))
            return

        # 2) If every active player has acted => next street or showdown
        if self.actions_since_last_raise >= len(active):
            self.game_round_progress()
            return

        # 3) Otherwise, next player's turn
        self.player_action()

    def finish_single_player_win(self, winner_idx):
        """Award pot, show message, end the hand AFTER letting user see the flipped cards."""
        self.players_data[winner_idx]['chips'] += self.pot
        self.update_player_chips_display(winner_idx)

        w_name = self.get_player_name(winner_idx)
        messagebox.showinfo("Round Over", f"{w_name} wins the pot of ${self.pot}!")
        self.status_label.config(text="")
        self.end_of_hand()

    def reveal_all_computers_and_pause(self, after_callback):
        """
        1) Reveal all computer hole cards immediately.
        2) Force the GUI to update, so user actually sees the flipping.
        3) Wait ~2 seconds, then call the provided callback (awarding pot, starting new hand, etc.)
        """
        self.reveal_all_computer_cards()
        
        # Force the canvas to redraw with new images
        self.root.update_idletasks()

        # Wait 2 seconds so the user can see the cards
        self.root.after(2000, after_callback)

    def reveal_all_computer_cards(self):
        """
        Reveal hole cards for every computer (indexes 1..3).
        """
        for i in range(1, self.num_players):
            p_data = self.players_data[i]
            # Remove any back-of-card images
            for cimg in p_data['card_imgs']:
                self.canvas.delete(cimg['id'])
            p_data['card_imgs'].clear()

            if len(p_data['cards']) < 2:
                continue

            c1, c2 = p_data['cards']
            ci1 = self.get_card_image(c1)
            ci2 = self.get_card_image(c2)

            x_offset = -20
            cid1 = self.canvas.create_image(
                self.players[i]['position'][0] + x_offset,
                self.players[i]['position'][1] - 50,
                image=ci1
            )
            cid2 = self.canvas.create_image(
                self.players[i]['position'][0] + x_offset + 30,
                self.players[i]['position'][1] - 50,
                image=ci2
            )
            p_data['card_imgs'] = [
                {'id': cid1, 'image': ci1},
                {'id': cid2, 'image': ci2}
            ]

    def get_player_name(self, idx):
        if idx == 0:
            return self.player_name
        else:
            names = ["PokerStar121", "DarkNite12", "RavensFan08", "AAWizard17"]
            return names[idx]

    def game_round_progress(self):
        # Clear everyone's current_bet
        for p_data in self.players_data:
            p_data['current_bet'] = 0

        if self.game_round == 'pre-flop':
            self.game_round = 'flop'
            self.deal_community_cards(3)
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
            # Showdown scenario => we reveal all, then pause
            self.reveal_all_computers_and_pause(self.finish_showdown)
            return

        self.current_bet = 0
        self.actions_since_last_raise = 0
        self.start_betting_round()

    def deal_community_cards(self, number):
        """
        Place 'number' community cards near x=270..570,
        so that 5 total appear in a row near the center of the table.
        """
        base_x = 270
        spacing = 75
        for _ in range(number):
            card = self.deck.pop()
            self.community_cards.append(card)

            idx = len(self.community_cards) - 1
            x = base_x + idx * spacing
            y = 300

            cimg = self.get_card_image(card)
            cid = self.canvas.create_image(x, y, image=cimg)
            self.community_cards_imgs.append({'id': cid, 'image': cimg})

    def finish_showdown(self):
        """Actually evaluate hands, award pot, then end the hand (after a brief pause)."""
        active_players = [
            i for i, p in enumerate(self.players_data)
            if p['in_game'] and not p['has_folded'] and p['chips'] > 0
        ]

        # Evaluate best hand(s)
        best_score = None
        winners = []
        for i in active_players:
            combined = self.players_data[i]['cards'] + self.community_cards
            score = self.evaluate_hand(combined)
            if best_score is None or score[0] > best_score[0]:
                best_score = score
                winners = [i]
            elif score[0] == best_score[0]:
                winners.append(i)

        # Split pot if tie
        share = self.pot // len(winners)
        for w_idx in winners:
            self.players_data[w_idx]['chips'] += share
            self.update_player_chips_display(w_idx)

        names_str = ", ".join(self.get_player_name(idx) for idx in winners)
        messagebox.showinfo("Showdown", f"{names_str} win(s) the pot of ${self.pot}!")
        self.status_label.config(text="")

        self.end_of_hand()

    def showdown(self):
        """(Deprecated) We'll rely on game_round_progress -> finish_showdown instead."""
        pass

    def end_of_hand(self):
        self.dealer_position = (self.dealer_position + 1) % self.num_players
        self.start_new_hand()

    def evaluate_hand(self, cards):
        """
        Very basic ranking:
          7 = four of a kind
          6 = full house
          3 = three of a kind
          2 = two pairs
          1 = one pair
          0 = high card
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

    # --------------------------------------------------------------------------
    # EEG Thread
    # --------------------------------------------------------------------------
    def start_eeg_thread(self):
        threading.Thread(target=self.simulated_eeg_reader, daemon=True).start()

    def simulated_eeg_reader(self):
        """
        Print EEG data to the console and update the player's (index=0) 
        name color and label text with the detected emotional state.
        """
        states = [
            ("Focused", 0.6),
            ("Calm", 0.125),
            ("Anxious", 0.125),
            ("Relaxed", 0.125),
        ]
        s_names, weights = zip(*states)

        color_map = {
            "Focused": "red",
            "Calm": "blue",
            "Anxious": "orange",
            "Relaxed": "thistle"
        }

        print("Starting random emotional state and power band generator...\n")
        try:
            while True:
                st = random.choices(s_names, weights=weights, k=1)[0]
                pband = [
                    round(random.uniform(0.46, 0.54), 16),
                    round(random.uniform(0.46, 0.54), 16),
                    round(random.uniform(0.46, 0.54), 16),
                ]
                print("-" * 60)
                print(f"Detected Emotional State: {st}")
                print(f"Average power per band : {pband}")
                print("-" * 60)

                new_color = color_map.get(st, "black")
                self.player_name = f"{self.base_player_name} ({st})"

                self.canvas.itemconfig(self.players[0]['name_text'],
                                       text=self.player_name,
                                       fill=new_color)
                nt_bbox = self.canvas.bbox(self.players[0]['name_text'])
                self.canvas.coords(self.players[0]['name_rect'], nt_bbox)

                time.sleep(3)
        except KeyboardInterrupt:
            print("\nProgram interrupted by user. Exiting...")

if __name__ == "__main__":
    root = tk.Tk()
    game = PokerGame(root)
    root.mainloop()
