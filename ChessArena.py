import math
import os.path
from typing import Optional, Dict

from PyQt6 import QtWidgets, QtGui
from PyQt6 import uic
from PyQt6.QtCore import QPointF, QTimer, QRectF
from PyQt6.QtGui import QPixmap, QImage
from PyQt6.QtWidgets import (
    QApplication,
    QFrame,
    QMessageBox,
    QTableWidgetItem,
    QMainWindow,
)

from BoardManager import BoardManager
from BotWidget import BotWidget
from Bots.ChessBotList import *
from Data.UI import Ui_MainWindow
from GameManager import GameManager
from ParallelPlayer import *
from Piece import Piece
from PieceManager import PieceManager

from Tournament import TournamentWindow

from Bots import *


#   Wrap up for QApplication
class ChessApp(QtWidgets.QApplication):
    def __init__(self):
        super().__init__([])

    def start(self):
        arena = ChessArena()
        arena.show()
        arena.start()

        self.exec()


#   Main window to handle the chess board
class ChessArena(Ui_MainWindow, QMainWindow):
    PROJECT_DIR = os.path.abspath(os.path.dirname(__file__))
    BOARDS_DIR = os.path.join(PROJECT_DIR, "Data", "maps")
    START_ICON = QtGui.QIcon.fromTheme("media-playback-start")
    STOP_ICON = QtGui.QIcon.fromTheme("media-playback-stop")

    tournament = None

    def __init__(self):
        super().__init__()

        uic.loadUi("Data/UI.ui", self)

        if self.tournament is None:
            self.tournament = TournamentWindow(self)

        self.msg_box: Optional[QMessageBox] = None

        # Render for chess board
        self.chess_scene = QtWidgets.QGraphicsScene()
        self.chessboardView.setScene(self.chess_scene)

        # Assets
        self.white_square: Optional[QPixmap] = None
        self.black_square: Optional[QPixmap] = None
        self.pieces_imgs: Dict[str, QImage] = {}
        self.load_assets()

        # Variables
        self.game_manager: GameManager = GameManager(self)
        self.board_manager: BoardManager = self.game_manager.board_manager

        # Board actions
        self.actionLoad.triggered.connect(self.select_and_load_board)
        self.actionReload.triggered.connect(self.reload_board)
        self.actionCopy.triggered.connect(self.copy_board)
        self.actionExport.triggered.connect(self.export_board)

        # Game actions
        self.actionTournamentMode.triggered.connect(self.tournament_mode)
        self.actionUndo.triggered.connect(self.game_manager.undo_move)
        self.actionStart.triggered.connect(self.game_manager.start_stop)
        self.actionRedo.triggered.connect(self.game_manager.redo_move)
        
        self.whiteBotWins.clicked.connect(self.manual_white_win)
        self.blackBotWins.clicked.connect(self.manual_black_win)

        self.movesList.resizeColumnsToContents()

        self.chessboardView.resizeEvent = self.update_chessboard

    def update_chessboard(self, *args, **kwargs):
        """Update chessboard to fit in view"""

        view = self.chessboardView
        shape = self.board_manager.board.shape
        board_w = shape[1] * self.black_square.size().width()
        board_h = shape[0] * self.black_square.size().height()
        w_ratio = board_w / view.rect().width()
        h_ratio = board_h / view.rect().height()
        ratio = max(w_ratio, h_ratio)
        w = view.rect().width() * ratio
        h = view.rect().height() * ratio
        rect = QRectF(0, 0, w, h)
        view.setSceneRect(QRectF((board_w - w) / 2, (board_h - h) / 2, w, h))
        view.fitInView(rect)

    def select_and_load_board(self):
        """Open board file selector and load the selected file"""
        path = QtWidgets.QFileDialog.getOpenFileName(
            self, "Select board", self.BOARDS_DIR, "Board File (*.brd *.fen)"
        )

        if path is None:
            return
        path = path[0]

        if self.board_manager.load_file(path):
            self.setup_board()
            self.setup_players()
            self.show_status("Board loaded")

    def load_assets(self):
        """Load board and piece images"""
        self.white_square = QtGui.QPixmap("Data/assets/light_square.png")
        self.black_square = QtGui.QPixmap("Data/assets/dark_square.png")
        PieceManager.load_assets()

    def remove_piece(self, piece: Piece):
        pos = piece.pos()

        piece.hide()

        for i in range(len(piece.fragments)):
            for j, fragment in enumerate(piece.fragments[i]):
                fragmentItem = self.chess_scene.addPixmap(fragment)

                center = piece.cutting_number / 2

                vx = j - center
                vy = i - center

                k = 100

                norm = math.sqrt(vx**2 + vy**2)

                if norm != 0:
                    x_norm = k * vx/norm
                    y_norm = k * vy/norm

                else:
                    x_norm = k * vx
                    y_norm = k * vy


                rect = fragmentItem.sceneBoundingRect()

                x = pos.x() + i*rect.width()
                y = pos.y() + j*rect.height()

                piece.addFragmentItem(fragmentItem, QPointF(x + x_norm, y + y_norm))
            
                # Mid
                #fragmentItem.setPos(pos.x() + (rect.width() * (piece.cutting_number / 2)) - rect.width()/2,
                #                    pos.y() + (rect.height() * (piece.cutting_number / 2)) - rect.height()/2)

                fragmentItem.setPos(x, y)

                fragmentItem.setZValue(1000);

        piece.explode()

    def setup_board(self):
        """Render the current board position"""
        path: str = os.path.relpath(self.board_manager.path, self.BOARDS_DIR)
        if os.pardir in path:
            path = self.board_manager.path
        self.currentBoardValue.setText(path)

        self.chess_scene.clear()

        board = self.board_manager.board
        height, width = board.shape

        for y in range(height):
            for x in range(width):
                # Draw board square
                square_color = (
                    self.white_square if (x + y) % 2 == 0 else self.black_square
                )
                square_item = self.chess_scene.addPixmap(square_color)
                square_item.setPos(
                    QtCore.QPointF(
                        square_color.size().width() * x,
                        square_color.size().height() * y,
                    )
                )

                # If tile is empty, continue
                if board[y, x] in ("", "XX", None):
                    continue

                piece: Piece = board[y, x]
                
                self.chess_scene.addItem(piece)
                piece.setPos(
                    QtCore.QPointF(
                        square_color.size().width() * x,
                        square_color.size().height() * y,
                    )
                )

                piece.setZValue(1000)
        self.update_chessboard()

    def setup_players(self):
        """Reset the game and set up player widgets list"""
        self.game_manager.reset()
        layout = self.botsList.layout()
        for i in reversed(range(layout.count())):
            if layout.itemAt(i).widget() is not None:
                layout.itemAt(i).widget().setParent(None)

        for i, color in enumerate(self.board_manager.available_colors):
            player = BotWidget(color)

            bot_selector = player.playerBot
            for name in CHESS_BOT_LIST:
                bot_selector.addItem(name, CHESS_BOT_LIST[name])
            bot_selector.setCurrentIndex(0)
            if i != 0:
                sep = QtWidgets.QFrame()

                sep.setFrameShape(QFrame.Shape.HLine)
                sep.setFrameShadow(QFrame.Shadow.Sunken)
                layout.addWidget(sep)
            layout.addWidget(player)
            self.game_manager.add_player(color, player)

        # TODO: Find a better solution
        def resize():
            self.botsScrollArea.setMaximumHeight(
                layout.maximumSize().height() + 2
            )

        QTimer.singleShot(1, resize)

    def tournament_mode(self):
        self.tournament.show()
        self.game_manager.start_tournament_mode(self.tournament.tournament_manager)

        self.tournament.tournament_manager.tournament.set_bots()

    def manual_white_win(self):
        if self.game_manager.tournament_mode:
            t = self.tournament.tournament_manager.tournament
            t.set_winner_and_next(t.current.player1)

        self.game_manager.game_end(PieceManager.COLOR_NAMES["w"], True)

    def manual_black_win(self):
        if self.game_manager.tournament_mode:
            t = self.tournament.tournament_manager.tournament
            t.set_winner_and_next(t.current.player2)

        self.game_manager.game_end(PieceManager.COLOR_NAMES["b"], True)

    def start(self):
        """Set up a new game"""
        self.setup_board()
        self.setup_players()
        self.chess_scene.update()

    def copy_board(self):
        """Copy the current board position as FEN in the clipboard"""
        fen: str = self.board_manager.get_fen()
        QApplication.clipboard().setText(fen)
        self.show_status("Copied board FEN to clipboard")

    def export_board(self):
        """Open the export file selector and save the board"""
        path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self,
            "Save board as ...",
            self.BOARDS_DIR,
            "Board File (*.brd *.fen)",
        )
        if path == "":
            return
        self.board_manager.save(path)
        self.show_status("Board exported")

    def reload_board(self):
        """Reload the board"""
        self.board_manager.reload()
        self.setup_board()
        self.show_status("Board reloaded")

    def show_message(self, message: str, title: str = "Message"):
        """
        Show a modal with the given message
        :param message: The message to display
        :param title: The modal's title
        """
        self.msg_box = QMessageBox(self)

        font = QtGui.QFont() 
        font.setPointSize(36)
        font.setBold(True)
        self.msg_box.setFont(font)

        self.msg_box.setWindowTitle(title)
        self.msg_box.setText(message)
        self.msg_box.open()

        return self.msg_box
    
    def show_timed_message(self, message: str, title: str = "Message", duration: int = 3000):
        msg_box = self.show_message(message, title)
        QTimer.singleShot(duration, msg_box.close)
        return msg_box

    def show_status(self, message: str, duration: int = 3000):
        """
        Show a message in the status bar
        :param message: The message to display
        :param duration: The duration of the message in milliseconds
        """
        self.statusbar.showMessage(message, duration)

    def push_move_to_history(self, move: str, player: str):
        """
        Add a move to the history
        :param move: The move description
        :param player: The player who made the move
        """
        tab = self.movesList
        tab.insertRow(tab.rowCount())
        tab.setItem(
            tab.rowCount() - 1, 0, QTableWidgetItem(str(tab.rowCount()))
        )
        tab.setItem(tab.rowCount() - 1, 1, QTableWidgetItem(move))
        tab.setItem(tab.rowCount() - 1, 2, QTableWidgetItem(player))
        tab.resizeColumnsToContents()
