


from PyQt6 import uic
from PyQt6.QtCore import QRectF
from PyQt6.QtGui import QColor, QPainter
from PyQt6.QtWidgets import QGraphicsItem, QGraphicsScene, QStyleOptionGraphicsItem, QVBoxLayout, QWidget
from PyQt6.uic.uiparser import QtWidgets

from Data.tournament import Ui_Tournament
from TournamentManager import Match, TournamentManager

class MatchItem(QGraphicsItem):
    def __init__(self, match: Match):
        super().__init__()
        self.match = match
        self.width = 160
        self.height = 60

    def boundingRect(self):
        return QRectF(0, 0, self.width, self.height)

    def paint(self, painter: QPainter, option: QStyleOptionGraphicsItem, widget: QWidget = ...) -> None:
        painter.setBrush(QColor(110, 110, 110))
        painter.setPen(QColor(199, 255, 255))

        painter.drawRect(self.boundingRect())

        p1 = self.match.getPlayer1Name()
        p2 = self.match.getPlayer2Name()

        painter.drawText(10, 20, p1)
        painter.drawText(10, 40, p2)


class TournamentWindow(Ui_Tournament, QWidget):
    def __init__(self):
        super().__init__()

        uic.loadUi("Data/tournament.ui", self)

        layout = QVBoxLayout(self)
        layout.addWidget(self.centralWidget)

        # Render for tournament
        self.tournament_scene = QGraphicsScene()
        self.tournamentView.setScene(self.tournament_scene)

    

        # Tournament actions
        self.actionLoad.triggered.connect(self.select_and_load_tournament)
        self.actionReset.triggered.connect(self.reset_tournament)

        self.tournamentManager = TournamentManager()

        self.setup_view()

    def select_and_load_tournament(self):
        """Open tournament file selector and load the selected file"""
        path = QtWidgets.QFileDialog.getOpenFileName(
            self, "Select tournament", self.BOARDS_DIR, "Board File (*.trn)"
        )

        if path is None:
            return
        path = path[0]

        if self.tournamentManager.load_file(path):
            self.setup_view()
            self.show_status("Tournament loaded")

    def setup_view(self):
        self.tournament_scene.clear()

        t = self.tournamentManager.tournament

        x_spacing = 260
        y_spacing = 120
        top_margin = 40

        # --- Winners Bracket -----------------------------------------------------
        if "winner" in t.brackets:
            wb = t.brackets["winner"]
            for col, rnd in enumerate(wb.rounds):
                for row, match in enumerate(rnd.matches):
                    item = MatchItem(match)
                    x = col * x_spacing
                    y = top_margin + row * y_spacing
                    item.setPos(x, y)
                    self.tournament_scene.addItem(item)

            wb_width = len(wb.rounds) * x_spacing
        else:
            wb_width = 0

        # --- Losers Bracket ------------------------------------------------------
        # On place le LB en dessous du WB avec un gros offset vertical
        lb_vertical_offset = 300

        if "loser" in t.brackets:
            lb = t.brackets["loser"]
            for col, rnd in enumerate(lb.rounds):
                for row, match in enumerate(rnd.matches):
                    item = MatchItem(match)
                    x = col * x_spacing
                    y = top_margin + lb_vertical_offset + row * y_spacing
                    item.setPos(x, y)
                    self.tournament_scene.addItem(item)

            lb_width = len(lb.rounds) * x_spacing
        else:
            lb_width = 0

        # --- Grand Finals --------------------------------------------------------
        gf = t.grand_finals

        # colonne après le plus large bracket
        gf_col = max(wb_width, lb_width)
        gf_x = gf_col
        gf_y = top_margin + 100

        x_offset_gf = 0
        for mat in gf.matches:
            gf_item = MatchItem(mat)
            gf_item.setPos(gf_x + x_offset_gf, gf_y)
            x_offset_gf += x_spacing

            self.tournament_scene.addItem(gf_item)

        # Ajuste les bounds de la scène pour occuper toute la view
        self.tournament_scene.setSceneRect(self.tournament_scene.itemsBoundingRect())

    def reset_tournament(self):
        pass
