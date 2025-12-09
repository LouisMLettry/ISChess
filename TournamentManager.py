from dataclasses import dataclass
import math
from typing import Self
import yaml
import os

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

    is_bye: bool = False

    is_grand_final: bool = False

    order: int = 0

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

    def getPlayer1Name(self):
        if self.player1 is None:
            return '?'

        if self.player1 == 0:
            return '-'

        return self.player1.name

    def getPlayer2Name(self):
        if self.player2 is None:
            return '?'

        if self.player2 == 0:
            return '-'

        return self.player2.name


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
        winner_bracket.rounds.append(Round(1, []))

        while i < n:
            if i + 1 < n - b:
                p1 = players[i]
                p2 = players[i+1]

                mat = Match(f"W{m_id}", p1, p2, None, None, "", "", None, None, False)

                i += 2
            
            else:
                mat = Match(f"W{m_id}", players[i], 0, None, None, "", "", None, None, True)

                i += 1


            all_matches[mat.id] = mat
            winner_bracket.rounds[0].matches.append(mat)
            m_id += 1

        # Next rounds

        n_rounds = 2**(min_exp - 2)

        ref_id = 1

        for i in range(1, min_exp):
            winner_bracket.rounds.append(Round(i + 1, []))

            for _ in range(n_rounds):
                mat = Match(f"W{m_id}", None, None, None, None, f"winner:W{ref_id}", f"winner:W{ref_id + 1}", None, None, False)

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

        loser_bracket.rounds.append(Round(1, []))

        for i in range(n_matches):
            if i == n_matches - 1 and l % 2 == 1:
                mat = Match(f"L{m_id}", None, None, None, None, f"loser:W{ref_id}", "", None, None, True)

                ref_id += 1

            else:
                mat = Match(f"L{m_id}", None, None, None, None, f"loser:W{ref_id}", f"loser:W{ref_id + 1}", None, None, False)

                ref_id += 2

            all_matches[mat.id] = mat
            loser_bracket.rounds[0].matches.append(mat)

            m_id += 1

        for i in range(1, 2 * (min_exp - 1)):
            r = i + 1

            loser_bracket.rounds.append(Round(r, []))

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
                    mat = Match(f"L{m_id}", None, None, None, None, loser_pool[j], winner_pool[j], None, None, False)

                    all_matches[mat.id] = mat
                    loser_bracket.rounds[i].matches.append(mat)

                    m_id += 1
                    offset += 1

                remaining = [larger_pool[j + offset] for j in range(len(larger_pool) - offset)]

                for j in range(len(remaining)):
                    mat = Match(f"L{m_id}", None, None, None, None, remaining[j], "", None, None, True)

                    all_matches[mat.id] = mat
                    loser_bracket.rounds[i].matches.append(mat)

                    m_id += 1

            else:
                for j in range(0, len(loser_pool), 2):
                    if j + 1 < len(loser_pool):
                        mat = Match(f"L{m_id}", None, None, None, None, loser_pool[j], loser_pool[j+1], None, None, False)
                    
                    else:
                        mat = Match(f"L{m_id}", None, None, None, None, loser_bracket[j], "", None, None, True)

                    all_matches[mat.id] = mat
                    loser_bracket.rounds[i].matches.append(mat)

                    m_id += 1


        # ======== Grand Finals ========

        gf_mat = Match("GF1", None, None, None, None, f"winner:{winner_bracket.rounds[-1].matches[-1].id}", f"winner:{loser_bracket.rounds[-1].matches[-1].id}", None, None, False, True)

        all_matches[gf_mat.id] = gf_mat

        gf = GrandFinals([gf_mat], True)

        Tournament._link_all_matches(all_matches)

        ordered = Tournament._compute_match_order(all_matches)

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
            rounds_dict = brackets_dict[bracket_name]
            rounds: list[Round] = []

            for r in rounds_dict["rounds"]:
                matches_dict = r["matches"]

                matches = Tournament._get_matches_from_dict(matches_dict, players, all_matches)

                rounds.append(Round(r["round"], matches))

            brackets[bracket_name] = Bracket(bracket_name, rounds)

        grand_finals_dict = raw["grand_finals"]

        grand_finals_matches = Tournament._get_matches_from_dict(grand_finals_dict["matches"], players, all_matches)
        
        grand_finals = GrandFinals(grand_finals_matches, grand_finals_dict["reset"])

        Tournament._link_all_matches(all_matches)

        ordered = Tournament._compute_match_order(all_matches)

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
    def _get_match_from_dict(m: dict, players: list[Player], gf: bool = False):
        if gf:
            return Match(m["id"], None, None, Tournament._get_player_from_dict(players, m["winner"]), None, m["player1_from"], m["player2_from"], None, None, False, True)

        if "player1" in m:
            player1 = Tournament._get_player_from_dict(players, m["player1"])
            player2 = Tournament._get_player_from_dict(players, m["player2"]) if not m["bye"] else 0

            return Match(m["id"], player1, player2, Tournament._get_player_from_dict(players, m["winner"]), None, "", "", None, None, is_bye=m["bye"])

        if not m["bye"]:
            return Match(m["id"], None, None, Tournament._get_player_from_dict(players, m["winner"]), None, m["player1_from"], m["player2_from"], None, None, False)

        return Match(m["id"], None, 0, Tournament._get_player_from_dict(players, m["winner"]), None, m["player1_from"], "", None, None, True)

    @staticmethod
    def _get_matches_from_dict(matches_dict: list[dict], players: list[Player], all_matches: dict[str, Match]):
        matches: list[Match] = []

        for m in matches_dict:
            mat = Tournament._get_match_from_dict(m, players)

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
        if mat.player1 is None:
            player1_key = mat.player1_ref.split(':')[0]
            player2_key = mat.player2_ref.split(':')[0] if not mat.is_bye else None

            if player1_key == "winner":
                mat.player1 = mat.player1_from.winner

            else:
                mat.player1 = Tournament._get_loser_and_link_players(mat.player1_from)

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

                mat.player1_from = mat1
                mat.player2_from = mat2
        
        for match_id in all_matches:
            mat = all_matches[match_id]

            mat.loser = Tournament._get_loser_and_link_players(mat)

    @staticmethod
    def _compute_match_order(all_matches: dict[str, Match]):
        ordered: list[Match] = [m for m in all_matches.values() if m.player1_ref == ""]
        remaining: list[Match] = [m for m in all_matches.values() if m.player1_ref != ""]

        while remaining:
            progress = False

            for m in remaining:
                parents = []

                if m.player1_from is not None:
                    parents.append(m.player1_from)

                if m.player2_from is not None:
                    parents.append(m.player2_from)

                if all(parent in ordered for parent in parents):
                    m.order = len(ordered)
                    ordered.append(m)
                    remaining.remove(m)
                    progress = True

                if not progress:
                    raise RuntimeError("Graph contains a cycle")

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
    DEFAULT_TOURNAMENT = os.path.join(TOURNAMENT_DIRECTORY, "test.yaml")

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
            
            return True

        if ext == ".txt":
            with open(path, 'r') as f:
                data = f.readlines()
                self.tournament = Tournament.from_txt(data)

            return True

    def export(self, path):
        raw = self.tournament.export()
        
        with open(path, 'w') as f:
            yaml.dump(raw, f, yaml.SafeDumper)
