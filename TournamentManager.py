from dataclasses import dataclass
import math
from typing import Self
from PyQt6.QtWidgets import QGraphicsItem, QWidget
import yaml
import os

from BotWidget import BotWidget

@dataclass
class Player:
    id: int
    name: str

    def export(self):
        raw: dict = {}
        raw["id"] = self.id
        raw["name"] = self.name

        return raw

@dataclass
class Round:
    ...

@dataclass
class Bracket:
    ...

@dataclass
class Match:
    id: str
    player1: Player | None | int
    player2: Player | None | int

    winner: Player | None
    loser: Player | None

    player1_ref: str
    player2_ref: str

    player1_from: Self | None
    player2_from: Self | None

    winner_to: Self | None = None
    loser_to: Self | None = None

    is_bye: bool = False

    is_grand_final: bool = False

    order: int = 0

    item: QGraphicsItem = None
    round: Round = None
    bracket: Bracket = None

    def export(self):
        raw: dict = {}
        raw["id"] = self.id

        if self.player1_ref == "" and not self.is_bye:
            raw["player1"] = self.player1.id
            raw["player2"] = self.player2.id

        elif self.player1_ref == "" and self.is_bye:
            raw["player1"] = self.player1.id
            raw["player2"] = 0

        elif self.player1_ref != "" and not self.is_bye:
            raw["player1_from"] = self.player1_ref
            raw["player2_from"] = self.player2_ref

        else:
            raw["player1_from"] = self.player1_ref
            raw["player2_from"] = ""
            

        raw["winner"] = self.winner.id if self.winner is not None else 0
        raw["bye"] = self.is_bye

        return raw

    def getPlayer1Infos(self):
        if self.player1 is None:
            return '??', '?', False

        if self.player1 == 0:
            return '-', '-', True

        return self.player1.name, f"{self.player1.id}", self.winner is self.player1

    def getPlayer2Infos(self):
        if self.player2 is None:
            return '??', '?', False

        if self.player2 == 0:
            return '-', '-', False

        return self.player2.name, f"{self.player2.id}", self.winner is self.player2

    def can_eliminate(self, player2: bool, reset: bool):
        if self.is_grand_final and reset:
            if player2:
                return True 

            if self.id == "GF2":
                return True

            return False

        if self.bracket.name == "loser":
            return True

        return False

    def setWinner(self, player: Player):
        if self.player1 is player:
            self.winner = self.player1
            self.loser = self.player2

        else:
            self.winner = self.player2
            self.loser = self.player1


@dataclass
class GrandFinals:
    matches: list[Match]
    reset: bool

    def export(self):
        raw: dict = {}
        raw["matches"] = []
        raw["reset"] = self.reset

        for mat in self.matches:
            raw["matches"].append(mat.export())

        return raw

@dataclass
class Round:
    id: int
    matches: list[Match]
    bracket: Bracket = None

    def export(self):
        raw: dict = {}
        raw["round"] = self.id
        raw["matches"] = []

        for mat in self.matches:
            raw["matches"].append(mat.export())

        return raw

@dataclass
class Bracket:
    name: str
    rounds: list[Round]

    def export(self):
        raw: dict = {}
        raw["rounds"] = []

        for round in self.rounds:
            raw["rounds"].append(round.export())

        return raw

@dataclass
class Tournament:
    name: str
    type: str
    brackets: dict[str, Bracket]
    players: list[Player]
    grand_finals: GrandFinals
    all_matches: dict[str, Match]
    ordered_matches: list[Match]
    current: Match = None
    last: Match = None

    arena: QWidget = None
    view: QWidget = None

    def export(self):
        raw: Dict = {}

        raw["tournament"] = {}
        raw["tournament"]["name"] = self.name
        raw["tournament"]["type"] = self.type

        raw["players"] = []

        for player in self.players:
            raw["players"].append(player.export())

        raw["brackets"] = {}

        for bracket in self.brackets:
            raw["brackets"][bracket] = self.brackets[bracket].export()

        raw["grand_finals"] = self.grand_finals.export()

        return raw
    
    def setBots(self):
        players = self.arena.game_manager.players

        widget1: BotWidget = players[0].widget
        widget2: BotWidget = players[1].widget
        
        widget1.playerBot.setCurrentText(self.current.player1.name)
        widget2.playerBot.setCurrentText(self.current.player2.name)

    def GFReset(self):
        mat = Match("GF2", self.current.player2, self.current.player1, None, None, "winner:GF1", "loser:GF1", self.current, self.current, is_grand_final=True)

        self.current.winner_to = mat
        self.current.loser_to = mat

        self.all_matches[mat.id] = mat
        self.ordered_matches.append(mat)
        self.grand_finals.matches.append(mat)

        self.view.addGFMatch(mat)
        
    def setWinnerAndNext(self, player: Player):
        self.current.setWinner(player)

        if self.current.is_grand_final and self.grand_finals.reset and len(self.grand_finals.matches) < 2 and self.current.winner is self.current.player2:
            self.GFReset()
        
        idx = self.ordered_matches.index(self.current) + 1

        if self.current.winner_to is not None:
            Tournament._get_loser_and_link_players(self.current.winner_to)
            self.current.winner_to.item.update()

        if self.current.loser_to is not None:
            Tournament._get_loser_and_link_players(self.current.loser_to)
            self.current.loser_to.item.update()


        self.last = self.current

        while idx < len(self.ordered_matches):
            if self.ordered_matches[idx].is_bye:
                idx += 1
                continue

            self.current = self.ordered_matches[idx]
            break
        
        if self.current.player1 is None or self.current.player2 is None:
            Tournament._get_loser_and_link_players(self.current)

        self.current.item.update()
        self.last.item.update()

        self.setBots()

        print(f"Match {self.last.id} has been won by {player.name}. Current match is now {self.current.id}")

    def reset(self):
        self.current = self.all_matches["W1"]
        self.last = None

        wb_rounds = self.brackets["winner"].rounds
        lb_rounds = self.brackets["loser"].rounds
        
        for i in range(len(wb_rounds)):
            for mat in wb_rounds[i].matches:
                mat.winner = None
                mat.loser = None
                mat.item = None
                
                if i != 0:
                    mat.player1 = None
                    mat.player2 = None if not mat.is_bye else 0

        for i in range(len(lb_rounds)):
            for mat in lb_rounds[i].matches:
                mat.winner = None
                mat.loser = None
                mat.item = None
                mat.player1 = None
                mat.player2 = None if not mat.is_bye else 0

        self.view.resetGF()
        
        if len(self.grand_finals.matches) > 1:
            del self.grand_finals.matches[1]

        gf_mat = self.grand_finals.matches[0]

        gf_mat.player1 = None
        gf_mat.player2 = None
        gf_mat.winner = None
        gf_mat.loser = None
        gf_mat.item = None

        self.view.setup_view()


    @staticmethod
    def from_txt(data: list[str]):
        name = data[0].strip()

        players_strings = data[1].strip().split(',')
        players: list[Player] = []

        for i in range(len(players_strings)):
            player = players_strings[i]
            players.append(Player(i+1, player))

        n = len(players)

        min_exp = math.ceil(math.log2(n))

        s = 2**min_exp

        b = s - n

        all_matches: dict[str, Match] = {}

        winner_bracket = Bracket("winner", [])
        loser_bracket = Bracket("loser", [])
        
        # ======== Winner bracket ===========

        m_id = 1

        # Round 1

        i = 0
        rnd = Round(1, [], bracket=winner_bracket)
        winner_bracket.rounds.append(rnd)

        while i < n:
            if i + 1 < n - b:
                p1 = players[i]
                p2 = players[i+1]

                mat = Match(f"W{m_id}", p1, p2, None, None, "", "", None, None, is_bye=False, round=rnd, bracket=winner_bracket)

                i += 2
            
            else:
                mat = Match(f"W{m_id}", players[i], 0, None, None, "", "", None, None, is_bye=True, round=rnd, bracket=winner_bracket)

                i += 1


            all_matches[mat.id] = mat
            winner_bracket.rounds[0].matches.append(mat)
            m_id += 1

        # Next rounds

        n_rounds = 2**(min_exp - 2)

        ref_id = 1

        for i in range(1, min_exp):
            rnd = Round(i + 1, [], bracket=winner_bracket)
            winner_bracket.rounds.append(rnd)

            for _ in range(n_rounds):
                mat = Match(f"W{m_id}", None, None, None, None, f"winner:W{ref_id}", f"winner:W{ref_id + 1}", None, None, is_bye=False, round=rnd, bracket=winner_bracket)

                all_matches[mat.id] = mat
                winner_bracket.rounds[i].matches.append(mat)

                ref_id += 2
                m_id += 1

            n_rounds //= 2


        # ======== Loser bracket ========


        m_id = 1

        ref_id = 1

        l = math.ceil((n - b) / 2)
        n_matches = math.ceil(l/2)

        rnd = Round(1, [], bracket=loser_bracket)
        loser_bracket.rounds.append(rnd)

        for i in range(n_matches):
            if i == n_matches - 1 and l % 2 == 1:
                mat = Match(f"L{m_id}", None, 0, None, None, f"loser:W{ref_id}", "", None, None, is_bye=True, round=rnd, bracket=loser_bracket)

                ref_id += 1

            else:
                mat = Match(f"L{m_id}", None, None, None, None, f"loser:W{ref_id}", f"loser:W{ref_id + 1}", None, None, is_bye=False, round=rnd, bracket=loser_bracket)

                ref_id += 2

            all_matches[mat.id] = mat
            loser_bracket.rounds[0].matches.append(mat)

            m_id += 1

        for i in range(1, 2 * (min_exp - 1)):
            r = i + 1
            
            rnd = Round(r, [], loser_bracket)
            loser_bracket.rounds.append(rnd)

            loser_pool: list[str] = [f"winner:{mat.id}" for mat in loser_bracket.rounds[i - 1].matches]

            if r % 2 == 0:
                winner_idx = (i // 2) + 1

                l = len(loser_bracket.rounds[i - 1].matches) + len(winner_bracket.rounds[winner_idx].matches)

                n_matches = math.ceil(l/2)

                winner_pool: list[str] = [f"loser:{mat.id}" for mat in winner_bracket.rounds[winner_idx].matches]
        
                larger_pool = loser_pool if len(loser_pool) >= len(winner_pool) else winner_pool
                smaller_pool = loser_pool if len(loser_pool) <= len(winner_pool) else winner_pool

                offset = 0

                for j in range(len(smaller_pool)):
                    mat = Match(f"L{m_id}", None, None, None, None, loser_pool[j], winner_pool[j], None, None, is_bye=False, round=rnd, bracket=loser_bracket)

                    all_matches[mat.id] = mat
                    loser_bracket.rounds[i].matches.append(mat)

                    m_id += 1
                    offset += 1

                remaining = [larger_pool[j + offset] for j in range(len(larger_pool) - offset)]

                for j in range(len(remaining)):
                    mat = Match(f"L{m_id}", None, 0, None, None, remaining[j], "", None, None, is_bye=True, round=rnd, bracket=loser_bracket)

                    all_matches[mat.id] = mat
                    loser_bracket.rounds[i].matches.append(mat)

                    m_id += 1

            else:
                for j in range(0, len(loser_pool), 2):
                    if j + 1 < len(loser_pool):
                        mat = Match(f"L{m_id}", None, None, None, None, loser_pool[j], loser_pool[j+1], None, None, is_bye=False, round=rnd, bracket=loser_bracket)
                    
                    else:
                        mat = Match(f"L{m_id}", None, 0, None, None, loser_bracket[j], "", None, None, is_bye=True, round=rnd, bracket=loser_bracket)

                    all_matches[mat.id] = mat
                    loser_bracket.rounds[i].matches.append(mat)

                    m_id += 1


        # ======== Grand Finals ========

        gf_mat = Match("GF1", None, None, None, None, f"winner:{winner_bracket.rounds[-1].matches[-1].id}", f"winner:{loser_bracket.rounds[-1].matches[-1].id}", None, None, is_bye=False, is_grand_final=True)

        all_matches[gf_mat.id] = gf_mat

        gf = GrandFinals([gf_mat], True)

        Tournament._link_all_matches(all_matches)

        ordered = Tournament._compute_match_order(all_matches, { "winner": winner_bracket, "loser": loser_bracket }, gf)

        last, current = Tournament._get_current_match(ordered)

        brackets = {
            "winner": winner_bracket,
            "loser": loser_bracket
        }

        return Tournament(name, "double_elimination", brackets, players, gf, all_matches, ordered, current, last)

        
    #----------------------- YAML ----------------------    
    

    @staticmethod
    def from_dict(raw: dict):
        name = raw["tournament"]["name"]
        type = raw["tournament"]["type"]
        players_raw = raw["players"]
        players: list[Player] = []
        all_matches: dict[str, Match] = {}

        for player in players_raw:
            players.append(Player(
                player["id"],
                player["name"]
            ))

        
        brackets_dict = raw["brackets"]
        brackets: dict[str, Bracket] = {}

        for bracket_name in brackets_dict:
            bracket = Bracket(bracket_name, [])
            brackets[bracket_name] = bracket
            rounds_dict = brackets_dict[bracket_name]

            for r in rounds_dict["rounds"]:
                matches_dict = r["matches"]
                round = Round(r["round"], [], bracket=bracket)

                matches = Tournament._get_matches_from_dict(matches_dict, players, all_matches, round, bracket)

                round.matches = matches

                bracket.rounds.append(round)

        grand_finals_dict = raw["grand_finals"]

        grand_finals_matches = Tournament._get_matches_from_dict(grand_finals_dict["matches"], players, all_matches, gf=True)
        
        grand_finals = GrandFinals(grand_finals_matches, grand_finals_dict["reset"])

        Tournament._link_all_matches(all_matches)

        ordered = Tournament._compute_match_order(all_matches, brackets, grand_finals)

        last, current = Tournament._get_current_match(ordered)
        
        return Tournament(name, type, brackets, players, grand_finals, all_matches, ordered, current, last)


    @staticmethod
    def _get_player_from_dict(players: list[Player], id: int):
        if id == 0:
            return None

        for player in players:
            if player.id == id:
                return player

    @staticmethod
    def _get_match_from_dict(m: dict, players: list[Player], round: Round = None, bracket: Bracket = None, gf: bool = False):
        if gf:
            return Match(m["id"], None, None, Tournament._get_player_from_dict(players, m["winner"]), None, m["player1_from"], m["player2_from"], None, None, is_grand_final=True)

        if "player1" in m:
            player1 = Tournament._get_player_from_dict(players, m["player1"])
            player2 = Tournament._get_player_from_dict(players, m["player2"]) if not m["bye"] else 0

            return Match(m["id"], player1, player2, Tournament._get_player_from_dict(players, m["winner"]), None, "", "", None, None, is_bye=m["bye"], round=round, bracket=bracket)

        if not m["bye"]:
            return Match(m["id"], None, None, Tournament._get_player_from_dict(players, m["winner"]), None, m["player1_from"], m["player2_from"], None, None, round=round, bracket=bracket)

        return Match(m["id"], None, 0, Tournament._get_player_from_dict(players, m["winner"]), None, m["player1_from"], "", None, None, is_bye=True, round=round, bracket=bracket)

    @staticmethod
    def _get_matches_from_dict(matches_dict: list[dict], players: list[Player], all_matches: dict[str, Match], round: Round = None, bracket: Bracket = None, gf: bool = False):
        matches: list[Match] = []

        for m in matches_dict:
            mat = Tournament._get_match_from_dict(m, players, round, bracket, gf)

            matches.append(mat)
            all_matches[mat.id] = mat
            

        return matches

    @staticmethod
    def _parse_player_origin(player_origin: str, all_matches: dict[str, Match]):
        parts = player_origin.split(":")

        key = parts[0]
        match_id = parts[1]

        mat = all_matches[match_id]

        return key, mat

    @staticmethod
    def _get_loser_and_link_players(mat: Match):
        if mat.player1 is None or mat.player2 is None:
            player1_key = mat.player1_ref.split(':')[0]

            if player1_key == "winner":
                mat.player1 = mat.player1_from.winner

            else:
                mat.player1 = Tournament._get_loser_and_link_players(mat.player1_from)

        if mat.player2 is None:
            player2_key = mat.player2_ref.split(':')[0] if not mat.is_bye else None

            if not mat.is_bye and player2_key == "winner":
                mat.player2 = mat.player2_from.winner

            elif not mat.is_bye:
                mat.player2 = Tournament._get_loser_and_link_players(mat.player2_from)

        
        if mat.is_bye:
            mat.winner = mat.player1

        if mat.winner is None or mat.is_bye:
            return None

        if mat.loser is not None:
            return mat.loser

        if mat.winner is mat.player1:
            return mat.player2

        if mat.winner is mat.player2:
            return mat.player1

    @staticmethod
    def _link_all_matches(all_matches: dict[str, Match]):
        for match_id in all_matches:
            mat = all_matches[match_id]

            if mat.player1_ref != "":
                key1, mat1 = Tournament._parse_player_origin(mat.player1_ref, all_matches)

                if mat.player2_ref != "":
                    key2, mat2 = Tournament._parse_player_origin(mat.player2_ref, all_matches)

                else:
                    mat2 = None
                    key2 = None

                mat.player1_from = mat1
                mat.player2_from = mat2

                if key1 == "winner":
                    mat.player1_from.winner_to = mat

                else:
                    mat.player1_from.loser_to = mat

                if key2 is not None:
                    if key2 == "winner":
                        mat.player2_from.winner_to = mat

                    else:
                        mat.player2_from.loser_to = mat
        
        for match_id in all_matches:
            mat = all_matches[match_id]
            
            mat.loser = Tournament._get_loser_and_link_players(mat)

    @staticmethod
    def _compute_match_order(all_matches: dict[str, Match], brackets: dict[str, Bracket], grand_finals: GrandFinals):
        ordered: list[Match] = []

        wb_rounds = brackets["winner"].rounds
        lb_rounds = brackets["loser"].rounds

        for i in range(len(wb_rounds[0].matches)):
            ordered.append(all_matches[f"W{i + 1}"])

        for i in range(len(lb_rounds[0].matches)):
            ordered.append(all_matches[f"L{i + 1}"])

        w_idx = len(wb_rounds[0].matches) + 1
        l_idx = len(lb_rounds[0].matches) + 1

        wr = 1
        lr = 1

        while wr < len(wb_rounds) - 1:
            for _ in range(len(wb_rounds[wr].matches)):
                ordered.append(all_matches[f"W{w_idx}"])

                w_idx += 1

            wr += 1

            for _ in range(2):
                for _ in range(len(lb_rounds[lr].matches)):
                    ordered.append(all_matches[f"L{l_idx}"])
                    l_idx += 1

                lr += 1

        if wr < len(wb_rounds):
            for i in range(len(wb_rounds[-1].matches)):
                ordered.append(all_matches[f"W{w_idx}"])
                w_idx += 1

            for i in range(len(lb_rounds[-1].matches)):
                ordered.append(all_matches[f"L{l_idx}"])
                l_idx += 1
        
        for i in range(len(grand_finals.matches)):
            ordered.append(all_matches[f"GF{i + 1}"])

        return ordered

    @staticmethod
    def _get_current_match(matches: list[Match]):
        current = None
        last = None

        for idx, m in enumerate(matches):
            if m.winner is None or idx == len(matches) - 1:
                current = m
                
                if idx > 0:
                    last = matches[idx-1]

                break

        return last, current


class TournamentManager:
    TOURNAMENT_DIRECTORY = os.path.join(os.path.abspath(os.path.dirname(__file__)), "Data", "tournaments")
    DEFAULT_TOURNAMENT = os.path.join(TOURNAMENT_DIRECTORY, "double_elimination.txt")

    def __init__(self) -> None:
        self.tournament: Tournament = None 
        self.path: Optional[str] = None
        self.load_file(self.DEFAULT_TOURNAMENT)

    def load_file(self, path):
        if path.strip() == "":
            return False

        if not os.path.exists(path):
            print(f"File '{path}' not found")
            return False

        if not os.path.isfile(path):
            print(f"'{path}' is not a file")
            return False

        ext = os.path.splitext(path)[1]

        if ext not in (".yaml", ".txt"):
            print(f"Unsupported extension '{ext}'")
            return False

        if ext == ".yaml":
            with open(path, 'r') as f:
                raw = yaml.load(f, Loader=yaml.SafeLoader)
                self.tournament = Tournament.from_dict(raw)
            

        elif ext == ".txt":
            with open(path, 'r') as f:
                data = f.readlines()
                self.tournament = Tournament.from_txt(data)

        return True


    def export(self, path):
        raw = self.tournament.export()
        
        with open(path, 'w') as f:
            yaml.dump(raw, f, yaml.SafeDumper)
