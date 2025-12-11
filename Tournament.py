


import os
from PyQt6.QtCore import QRectF
from PyQt6.QtGui import QColor, QPainter
from PyQt6.QtWidgets import QFileDialog, QGraphicsItem, QGraphicsScene, QPushButton, QStyleOptionGraphicsItem, QVBoxLayout, QWidget

from Data.tournament import Ui_Tournament
from TournamentManager import Match, Tournament, TournamentManager

class MatchItem(QGraphicsItem):
    width = 160
    height = 70
    gap = 6
    
    def __init__(self, match: Match, tournament: Tournament):
        super().__init__()
        self.match: Match = match
        self.tournament: Tournament = tournament

    def boundingRect(self):
        return QRectF(0, 0, self.width, self.height)

    def paint(self, painter: QPainter, option: QStyleOptionGraphicsItem, widget: QWidget = ...) -> None:
        painter.setBrush(QColor(110, 110, 110))

        if self.match.is_bye:
            painter.setPen(QColor(199, 255, 255))

        if self.match is self.tournament.current:
            painter.setPen(QColor(255, 0, 0))

        h = (self.height - self.gap) // 2

        painter.drawRect(QRectF(0, 0, self.width, h))
        painter.drawRect(QRectF(0, h + 3, self.width, h))

        p1 = self.match.getPlayer1Name()
        p2 = self.match.getPlayer2Name()

        painter.drawText(10, h//2, p1)
        painter.drawText(10, h + self.gap + h//2, p2)


class TournamentWindow(Ui_Tournament, QWidget):
    PROJECT_DIR = os.path.abspath(os.path.dirname(__file__))
    TOURNAMENTS_DIR = os.path.join(PROJECT_DIR, "Data", "tournaments")

    def __init__(self, arena: QWidget):
        super().__init__()

        self.setupUi(self)

        self.arena = arena

        layout = QVBoxLayout(self)
        layout.addWidget(self.centralWidget)

        self.testbtn = QPushButton(self)

        self.testbtn.clicked.connect(self.testwin) 

        layout.addWidget(self.testbtn)

        # Render for tournament
        self.tournament_scene = QGraphicsScene()
        self.tournamentView.setScene(self.tournament_scene)

        # Tournament actions
        self.actionLoad.triggered.connect(self.select_and_load_tournament)
        self.actionReset.triggered.connect(self.reset_tournament)
        self.actionExport.triggered.connect(self.export_tournament)

        self.tournamentManager = TournamentManager()
        self.tournamentManager.tournament.arena = self.arena
        self.tournamentManager.tournament.view = self

        self.setup_view()

    def testwin(self):
        self.tournamentManager.tournament.setWinnerAndNext(self.tournamentManager.tournament.current.player1)

    def select_and_load_tournament(self):
        """Open tournament file selector and load the selected file"""
        path = QFileDialog.getOpenFileName(
            self, "Select tournament", self.TOURNAMENTS_DIR, "Tournament File (*.yaml, *.txt)"
        )

        if path is None:
            return
        path = path[0]

        if self.tournamentManager.load_file(path):
            self.tournamentManager.tournament.arena = self.arena
            self.tournamentManager.tournament.view = self
            self.setup_view()
            # self.show_status("Tournament loaded")

    def setup_view(self):
        self.tournament_scene.clear()

        t = self.tournamentManager.tournament

        self.x_spacing = 200
        y_spacing = MatchItem.height + 40

        top_margin = 40

        rows = 1
        max_rows = 1

        

        # --- Winners Bracket -----------------------------------------------------
        if "winner" in t.brackets:
            wb = t.brackets["winner"]
            for col, rnd in enumerate(wb.rounds):
                for row, mat in enumerate(rnd.matches):
                    item = MatchItem(mat, self.tournamentManager.tournament)
                    mat.item = item
                    x = col * self.x_spacing
                    y = top_margin + row * y_spacing
                    item.setPos(x, y)
                    self.tournament_scene.addItem(item)

                    rows += 1

                if rows > max_rows:
                    max_rows = rows

                rows = 1

            wb_width = len(wb.rounds) * self.x_spacing
        else:
            wb_width = 0

        # --- Losers Bracket ------------------------------------------------------
        # On place le LB en dessous du WB avec un gros offset vertical
        max_matches_in_wb = max_rows - 1
        lb_vertical_offset = (max_matches_in_wb + 2) * y_spacing

        if "loser" in t.brackets:
            lb = t.brackets["loser"]
            for col, rnd in enumerate(lb.rounds):
                for row, mat in enumerate(rnd.matches):
                    item = MatchItem(mat, self.tournamentManager.tournament)
                    mat.item = item
                    x = col * self.x_spacing
                    y = top_margin + lb_vertical_offset + row * y_spacing
                    item.setPos(x, y)
                    self.tournament_scene.addItem(item)

            lb_width = len(lb.rounds) * self.x_spacing
        else:
            lb_width = 0

        # --- Grand Finals --------------------------------------------------------
        gf = t.grand_finals

        # colonne après le plus large bracket
        gf_col = max(wb_width, lb_width)
        self.gf_x = gf_col
        self.gf_y = top_margin + max_matches_in_wb * y_spacing

        self.x_offset_gf = 0

        for mat in gf.matches:
            gf_item = MatchItem(mat, self.tournamentManager.tournament)
            mat.item = gf_item
            gf_item.setPos(self.gf_x + self.x_offset_gf, self.gf_y)
            self.x_offset_gf += self.x_spacing

            self.tournament_scene.addItem(gf_item)

        # Ajuste les bounds de la scène pour occuper toute la view
        self.tournament_scene.setSceneRect(self.tournament_scene.itemsBoundingRect())

    def addGFMatch(self, mat: Match):
        gf_item = MatchItem(mat, self.tournamentManager.tournament)
        mat.item = gf_item
        gf_item.setPos(self.gf_x + self.x_offset_gf, self.gf_y)
        self.x_offset_gf += self.x_spacing

        self.tournament_scene.addItem(gf_item)

        self.tournament_scene.setSceneRect(self.tournament_scene.itemsBoundingRect())


    def export_tournament(self):
        """Open the export file selector and save the board"""
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Save tournament as ...",
            self.TOURNAMENTS_DIR,
            "Tournament configuration file (*.yaml)",
        )
        if path == "":
            return

        # self.show_status("Tournament exported")
        self.tournamentManager.export(path)

    def reset_tournament(self):
        print("Reset tournament action triggered.")
        pass
