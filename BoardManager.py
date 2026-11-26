import os
import re
from typing import Optional

import numpy as np

from PieceManager import PieceManager


class BoardManager:
    BOARD_DIRECTORY = os.path.join(os.path.abspath(os.path.dirname(__file__)), "Data", "maps")
    DEFAULT_BOARD = os.path.join(BOARD_DIRECTORY, "default.brd")

    def __init__(self):
        self.board: np.array = np.array([], dtype='O')
        self.path: Optional[str] = None
        self.player_order: str = "0w01b2"
        self.available_colors: list[str] = []
        self.pieces = []
        self.load_file(self.DEFAULT_BOARD)

    @staticmethod
    def get_string_board(board):
        res = []
        for r in board:
            line = []
            for c in r:
                if type(c) is str:
                    line.append(c)
                else:
                    line.append(c.string())
            res.append(line)
        return res

    def post_load(self):
        """
        Callback called after loading a board

        Builds a list of available player colors used on the board
        """

        new_board = np.empty_like(self.board, dtype=object)
        self.pieces = []

        self.available_colors = []
        for y in range(self.board.shape[0]):
            for x in range(self.board.shape[1]):
                if self.board[y, x] in ("", "XX"):
                    new_board[y, x] = self.board[y, x]
                    continue

                piece_type, color = self.board[y, x]
                if color not in self.available_colors:
                    self.available_colors.append(color)

                piece = PieceManager.get_piece(color, piece_type)
                new_board[y, x] = piece
                
                self.pieces.append(piece)

        self.board = new_board

    def load_file(self, path: str) -> bool:
        """
        Load a board from a file

        =================
        Supported formats
        =================

        ------------------------
        Board description (.brd)
        ------------------------

        Starts with the player sequence on a line, then the board layout,
        one row per line with comma-separated tile descriptions.

        Each tile is described with two characters:

        - The piece type: king (k), queen (q), knight (n), bishop (b), rook (r), pawn (p)
        - The piece color: white (w), blue (b), red (r), yellow (y)

        If the tile is empty, use ``--``

        *Example*::

            0w01b2
            rw,nw,bw,kw,qw,bw,nw,rw
            pw,pw,pw,pw,pw,pw,pw,pw
            --,--,--,--,--,--,--,--
            --,--,--,--,--,--,--,--
            --,--,--,--,--,--,--,--
            --,--,--,--,--,--,--,--
            pb,pb,pb,pb,pb,pb,pb,pb
            rb,nb,bb,kb,qb,bb,nb,rb

        ----------
        FEN (.fen)
        ----------

        Only contains a single line describing the board layout in `FEN`_

        *Example*::

            rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1

        .. _FEN: https://en.wikipedia.org/wiki/Forsyth%E2%80%93Edwards_Notation

        :param path: The path to the board file. Can either be a .brd or .fen file
        :return: ``True`` if successful, `False` otherwise
        """
        if path.strip() == "":
            return False

        if not os.path.exists(path):
            print(f"File '{path}' not found")
            return False

        if not os.path.isfile(path):
            print(f"'{path}' is not a file")
            return False

        ext = os.path.splitext(path)[1]

        if ext not in (".brd", ".fen"):
            print(f"Unsupported extension '{ext}'")
            return False

        with open(path, "r") as f:
            data = f.read()

        if ext == ".brd":
            lines = data.split("\n")
            rows = [
                line.replace('--', '').strip().split(",")
                for line in lines[1:]
            ]
            rows = list(filter(lambda r: len(r) != 0, rows))
            if len(rows) == 0:
                print("Board must have at least one row")
                return False

            width = len(rows[0])

            #   check lines length equals
            for row in rows:
                if len(row) != width:
                    print("All rows must have the same width")
                    return False

            self.player_order = lines[0]
            self.board = np.array(rows, dtype='O')
            self.path = path
            self.post_load()
            return True

        elif ext == ".fen":
            parts = data.strip().split(" ")
            if len(parts) == 0:
                print("FEN must at least contain the board state")
                return False

            board_desc = parts[0]
            rows_desc = board_desc.split("/")
            if len(rows_desc) == 0:
                print("Board must have at least one row")
                return False

            rows = []

            # Match before a letter or between a letter and a digit, or at the start/end of the string
            # (allows for bigger board with spaces >= 10)
            regexp = r"^|(?=\D)|(?<=\D)(?=\d)|$"
            for row_desc in rows_desc:
                matches = list(re.finditer(regexp, row_desc))
                row = []
                for i in range(len(matches) - 1):
                    m1 = matches[i]
                    m2 = matches[i + 1]
                    part = row_desc[m1.start():m2.start()]
                    if part.isnumeric():
                        row += [""] * int(part)
                    else:
                        color = "w" if part.isupper() else "b"
                        piece = part.lower()
                        if piece not in ("p", "r", "n", "b", "k", "q"):
                            print(f"Invalid piece '{part}'")
                            return False
                        row.append(piece + color)
                rows.append(row)

            width = len(rows[0])
            # Check lines length equals
            for row in rows:
                if len(row) != width:
                    print("All rows must have the same width")
                    return False

            next_player = parts[1] if len(parts) > 1 else "w"
            if next_player not in ("w", "b"):
                print(f"Invalid player '{next_player}'")
                return False

            self.player_order = "0w01b2" if next_player == "w" else "0b01w2"
            board = np.array(rows, dtype='O')
            if next_player == "w":
                board = np.rot90(board, 2)
            self.board = board
            self.path = path
            self.post_load()
            return True
        return False

    def reload(self):
        """Reload the board from the last imported file, if any"""
        if self.path is not None:
            self.load_file(self.path)

    def get_fen(self):
        """Get the current board position as a FEN string"""
        fen = ""
        rows = []
        for y in range(self.board.shape[0]):
            row = ""
            count = 0
            for x in range(self.board.shape[1]):
                piece = self.board[y, x]
                if piece == "":
                    count += 1
                else:
                    if count != 0:
                        row += str(count)
                        count = 0

                    type_ = piece.type
                    col = piece.color

                    if col == "w":
                        type_ = type_.upper()
                    row += type_

            if count != 0:
                row += str(count)
            rows.append(row)

        fen += "/".join(rows)
        fen += " " + self.player_order[1]
        fen += " - - 0 1"
        return fen

    def save(self, path: str):
        """
        Save the current board position in a file

        :param path: The path where to save the board
        """
        with open(path, "w") as file:
            file.write(self.player_order)
            for y in range(self.board.shape[0]):
                line = []
                for x in range(self.board.shape[1]):
                    piece = self.board[y, x]
                    if piece == "":
                        line.append("--")
                        continue;

                    line.append(piece.string())

                file.write("\n" + ",".join(line))
