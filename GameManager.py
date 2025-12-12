from __future__ import annotations

import math
from typing import List, Optional, TYPE_CHECKING, Tuple

import numpy as np
from PyQt6.QtCore import QTimer
from PyQt6.QtGui import QIcon

from BoardManager import BoardManager
from BotWidget import BotWidget
from ChessRules import move_is_valid
from ParallelPlayer import ParallelTurn
from Piece import Piece
from PieceManager import PieceManager
from Player import Player
from TournamentManager import TournamentManager

if TYPE_CHECKING:
    from ChessArena import ChessArena


def rotate_coordinates(
    size: tuple[int, int], pt: tuple[int, int], rot: int
) -> tuple[int, int]:
    """
    Rotate the given coordinates by the indicated angle
    :param size: Size of the board in the current orientation
    :param pt: Coordinates in the current orientation
    :param rot: Number of 90° clockwise rotations to perform
    :return: The rotated coordinates
    """
    rot = rot % 4
    if rot == 0:
        return pt

    y, x = pt
    y2 = size[0] - y - 1
    x2 = size[1] - x - 1
    if rot == 1:
        return x, y2
    if rot == 2:
        return y2, x2
    return x2, y


class GameManager:
    MIN_WAIT = 500
    GRACE_RATIO = 0.05

    def __init__(self, arena: ChessArena):
        self.arena: ChessArena = arena
        self.board_manager: BoardManager = BoardManager()
        self.tournamentManager: TournamentManager = None
        self.tournament_mode = False
        self.players: list[Player] = []
        self.turn: int = 0
        self.nbr_turn_to_play: int = 0
        self.current_player: Optional[ParallelTurn] = None
        self.current_player_next_move = None
        self.current_player_color = None
        self.current_player_board = None
        self.player_finished: bool = False
        self.auto_playing: bool = False
        self.timeout = QTimer()
        self.timeout.timeout.connect(lambda: self.end_turn(forced=True))
        self.min_wait = QTimer()
        self.min_wait.timeout.connect(self.end_if_finished)

    def start_tournament_mode(self, tournamentManager: TournamentManager):
        """Set tournament mode on"""
        self.tournament_mode = True
        self.tournamentManager = tournamentManager

    def reset(self):
        """Reset the game"""
        self.players = []
        self.turn = 0

    def add_player(self, color: str, widget: BotWidget):
        """
        Add a player to the game
        :param color: The player's color
        :param widget: The bot widget
        """
        player = Player(color, widget)
        self.players.append(player)

    def get_sequence(self, full: bool = False) -> str:
        """
        Get the player sequence
        :param full: If ``True``, the full sequence is returned.
                     If ``False``, only the part related to the current player is returned
        :return: The player sequence
        """
        if full:
            start = self.board_manager.player_order[: 3 * self.turn]
            end = self.board_manager.player_order[3 * self.turn :]
            return end + start
        return self.board_manager.player_order[
            self.turn * 3 : self.turn * 3 + 3
        ]

    def next(self) -> bool:
        """
        Start a new turn

        This function calls the next player's bot function with the appropriate arguments and starts a timeout timer.
        :return: ``True`` if successful, ``False`` if a turn is already in progress
        """
        if self.current_player is not None:
            print("Cannot launch new turn while already processing")
            return False

        self.update_start_button(playing=True)

        board = self.board_manager.board
        player: Player = self.players[self.turn]
        budget: float = player.get_budget()
        sequence: str = self.get_sequence()
        func_name, func = player.get_func()
        print(f"Player {self.turn}'s turn: {func_name} (budget: {budget:.2f}s)")

        tile_width = self.arena.white_square.size().width()
        tile_height = self.arena.white_square.size().width()

        self.player_finished = False

        self.current_player_color = player.color
        self.current_player_board = np.rot90(board, int(sequence[2]))

        if func_name == "ManualMover":
            self.start_manual_turn(player)

            budget_ms: int = int(budget * 1000 * (1 + self.GRACE_RATIO))
            self.timeout.start(budget_ms)

            if self.MIN_WAIT < budget_ms:
                self.min_wait.start(self.MIN_WAIT)

            return True

        self.current_player = ParallelTurn(
            func,
            sequence,
            BoardManager.get_string_board(self.current_player_board),
            budget,
            tile_width,
            tile_height,
        )

        self.current_player.setTerminationEnabled(True)
        self.current_player.finished.connect(self.on_player_finished)
        self.current_player.start()

        # Timer to call
        # self.timeout.singleShot(int(budget * 1000 * 1.05), lambda: self.end_turn(forced=True))
        budget_ms: int = int(budget * 1000 * (1 + self.GRACE_RATIO))
        self.timeout.start(budget_ms)
        if self.MIN_WAIT < budget_ms:
            self.min_wait.start(self.MIN_WAIT)

        return True

    def start_manual_turn(self, player):
        for piece in self.board_manager.pieces:
            if piece.color == player.color:
                piece.enableMovement(True)
                piece.signals.released.connect(self.on_piece_released)

    def on_piece_released(self, piece, start, end):
        tile_w = self.arena.white_square.width()
        tile_h = self.arena.white_square.height()

        start_tile = (int(start.y() // tile_h), int(start.x() // tile_w))
        end_tile = (int(end.y() // tile_h), int(end.x() // tile_w))

        snapped_x = end_tile[1] * tile_w
        snapped_y = end_tile[0] * tile_h

        if start_tile[0] == end_tile[0] and start_tile[1] == end_tile[1]:
            piece.setPos(snapped_x, snapped_y)
            return

        sequence = self.get_sequence()
        rot = int(sequence[2])
        board_shape = self.board_manager.board.shape
        rotated_start_tile = rotate_coordinates(board_shape, start_tile, rot)
        rotated_end_tile = rotate_coordinates(board_shape, end_tile, rot)
        move = (rotated_start_tile, rotated_end_tile)

        if not move_is_valid(self.get_sequence(True), move, self.current_player_board):
            piece.setPos(piece.old_pos)
            return

        piece.setPos(snapped_x, snapped_y)

        for p in self.board_manager.pieces:
            p.enableMovement(False)

            if p.color == piece.color:
                p.signals.released.disconnect()

        self.end_turn(forced=False, manual_move=move)


    def on_player_finished(self):
        """Callback called by the player when it has finished playing"""
        self.player_finished = True

    def end_if_finished(self):
        """Callback called after a minimum waiting time to end the turn if the player has already finished playing"""
        if self.player_finished:
            self.end_turn()

    def end_turn(self, forced: bool = False, manual_move=None) -> bool:
        """
        End the current turn

        If this function is called to prematurely end a player's turn
        because of a timeout, ``forced`` should be set to ``True``
        :param forced: If ``True``, prints a message telling the user the current player
                       took too long and was terminated early
        :return: ``True`` if successful, ``False`` if no turn was in progress
        """

        if manual_move is not None:
            self.current_player_next_move = manual_move

            self.min_wait.stop()
            self.timeout.stop()

            self.apply_move()

            if self.check_game_end():
                return True

            self.turn += 1
            self.turn %= len(self.players)

            if self.auto_playing:
                self.nbr_turn_to_play -= 1
                if self.nbr_turn_to_play <= 0:
                    self.stop()
                else:
                    self.next()

            return True

        if self.current_player is None:
            return False

        self.current_player_next_move = self.current_player.next_move

        self.min_wait.stop()
        self.timeout.stop()
        if forced:
            print("Player took too long, terminating thread")

        self.current_player.terminate()
        self.current_player.quit()

        self.apply_move()

        if self.check_game_end():
            return True

        self.current_player = None
        self.turn += 1
        self.turn %= len(self.players)

        if self.auto_playing:
            self.nbr_turn_to_play -= 1
            if self.nbr_turn_to_play <= 0:
                self.stop()
            else:
                self.next()

        return True

    def start(self) -> bool:
        """
        Start a series of turns

        :return: ``True`` if successful, ``False`` if the number of turns to play is <= 0 or if already autoplaying
        """
        self.nbr_turn_to_play = self.arena.autoMovesCount.value()
        if self.nbr_turn_to_play <= 0:
            self.arena.show_message(
                f"Cannot start auto-playing, number of moves is {self.nbr_turn_to_play}, must be >0"
            )
            return False

        self.update_start_button(playing=True)
        if self.auto_playing:
            print("Already auto-playing")
            return False
        self.auto_playing = True
        print(f"Starting auto-play for {self.nbr_turn_to_play} moves")
        self.next()
        return True

    def stop(self):
        """
        Stop the game if currently autoplaying

        This does not immediately end the running turn but lets it complete gracefully
        """
        self.update_start_button(playing=False)
        if not self.auto_playing:
            print("Already stopped")
            return
        self.auto_playing = False

    def update_start_button(self, playing: bool):
        """
        Update the start/stop button

        If ``playing`` is ``True``, the button will also display the remaining number of turns
        :param playing: If ``True`` the button uses the "stop" icon. If ``False``, it uses the "start" icon
        """
        icon: QIcon = self.arena.STOP_ICON if playing else self.arena.START_ICON
        self.arena.startStop.setIcon(icon)

        if playing and self.auto_playing:
            self.arena.startStop.setText(
                f"{self.nbr_turn_to_play} move(s) left"
            )
        else:
            self.arena.startStop.setText(None)

    def start_stop(self):
        """
        Toggle autoplaying

        This function calls either `start` or `stop` depending on the current state
        """
        if self.auto_playing:
            print("Stopping")
            self.stop()
        else:
            print("Starting")
            self.start()

    def undo_move(self):
        """Undo the last move, if any"""
        self.arena.show_message("This feature has not been implemented yet")

    def redo_move(self):
        """Redo the next move, if any"""
        self.arena.show_message("This feature has not been implemented yet")

    def apply_move(self) -> bool:
        """
        Try to apply the move chosen by the current player
        :return: ``True`` if successful, ``False`` if the move is invalid
        """
        move: tuple[tuple[int, int], tuple[int, int]] = (
            self.current_player_next_move
        )

        start, end = move
        color: str = self.current_player_color
        color_name: str = PieceManager.COLOR_NAMES[color]
        board = self.current_player_board

        tile_width = self.arena.white_square.size().width()
        tile_height = self.arena.white_square.size().width()

        start_piece = board[start[0], start[1]]

        if not move_is_valid(self.get_sequence(True), move, board):
            print(f"Invalid move from {start} to {end}")
            return False

        end_piece = board[end[0], end[1]]

        start_piece_and_col = f"{start_piece.type}{start_piece.color}"

        print(
            f"{color_name} moved {PieceManager.get_piece_name(start_piece_and_col)} from {start} to {end}"
        )

        # Capture
        if end_piece != '':
            end_piece_and_col = f"{end_piece.type}{end_piece.color}"

            print(
                f"{color_name} captured {PieceManager.get_piece_name(end_piece_and_col)}"
            )

        # Apply move
        board[end[0], end[1]] = start_piece
        board[start[0], start[1]] = ""

        if type(end_piece) is Piece:
            self.board_manager.pieces = [p for p in self.board_manager.pieces if p is not end_piece]

            self.arena.remove_piece(end_piece)
        
        # Promotion
        if start_piece[0] == "p" and end[0] == board.shape[0] - 1:
            PieceManager.upgrade_piece(board[end[0], end[1]], 'q')

        sequence: str = self.get_sequence()
        rot: int = int(sequence[2])
        real_start = rotate_coordinates(board.shape, start, rot)
        real_end = rotate_coordinates(board.shape, end, rot)
        real_height, real_width = self.board_manager.board.shape
        col1 = "ABCDEFGH"[real_width - 1 - real_start[1]]
        col2 = "ABCDEFGH"[real_width - 1 - real_end[1]]
        
        start_piece.move(real_end[0], real_end[1], tile_width, tile_height);

        row1 = real_start[0] + 1
        row2 = real_end[0] + 1
        self.arena.push_move_to_history(
            f"{col1}{row1} -> {col2}{row2}", color_name
        )

        return True

    def reload_board(self):
        """Resets the board and UI for the next tournament match"""
        self.arena.reloadBoard.click()

    def check_game_end(self):
        board = self.current_player_board
        current_color = self.current_player_color
        for y in range(board.shape[0]):
            for x in range(board.shape[1]):
                piece = board[y, x]
                if piece and piece[0] == "k" and piece[1] != current_color:
                    return

        color_name: str = PieceManager.COLOR_NAMES[current_color]
        
        self.arena.show_message(
            f"{color_name} player won the match", "End of game"
        )

        self.stop()

        if self.tournament_mode:
            tournament = self.tournamentManager.tournament
            tournament.setWinnerAndNext(tournament.current.player1 if current_color == "w" else tournament.current.player2)

            QTimer.singleShot(0, self.reload_board) # Next event
