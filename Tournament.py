


import os
import random
from PyQt6.QtCore import QEvent, QLineF, QPointF, QRectF, Qt
from PyQt6.QtGui import QColor, QPainter
from PyQt6.QtWidgets import QFileDialog, QGraphicsView, QGraphicsItem, QGraphicsScene, QGraphicsSceneMouseEvent, QPushButton, QStyleOptionGraphicsItem, QVBoxLayout, QWidget

from Data.tournament import Ui_Tournament
from TournamentManager import Match, Player, Tournament, TournamentManager

class MatchItem(QGraphicsItem):
    w_name = 160
    h_match = 70

    gap = 3
    w_padding = 10

    h = (h_match - gap) // 2
    s_idx = h
    s_score = h
    w_mid = h

    width = w_name + s_idx + s_score + w_mid
    height = h_match + gap

    background_color: QColor = QColor(99, 98, 99)
    background_color2: QColor = QColor(125, 130, 125)
    background_color3: QColor = QColor(160, 165, 160)
    background_color4: QColor = QColor(200, 205, 200)
    text_color: QColor =  QColor(220, 220, 220)
    text_color2: QColor = QColor(88, 87, 88)
    winner_color: QColor =  QColor(66, 244, 192)
    current_color: QColor = QColor(218, 48, 102)
    selected_color: QColor = QColor(20, 140, 100)
    
    def __init__(self, match: Match, tournament: Tournament):
        super().__init__()

        self.match: Match = match
        self.tournament: Tournament = tournament

        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, True)

    def boundingRect(self):
        return QRectF(0, 0, self.width, self.height)

    def paint(self, painter: QPainter, option: QStyleOptionGraphicsItem, widget: QWidget = ...) -> None:
        p1, id1, win1 = self.match.getPlayer1Infos()
        p2, id2, win2 = self.match.getPlayer2Infos()

        is_loser = not self.match.is_grand_final and self.match.bracket.name == "loser"

        if is_loser and self.match.player1_from.bracket.name != "loser":
            p1 = f"{p1} (from {self.match.player1_from.id})"

        if is_loser and not self.match.is_bye and self.match.player2_from.bracket.name != "loser":
            p2 = f"{p2} (from {self.match.player2_from.id})"

        flags = Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter

        painter.setPen(self.text_color2)

        mid_rect = QRectF(0, 0, self.w_mid, self.height)
        painter.drawText(mid_rect, flags, self.match.id)

        self._paint_part(painter, p1, id1, win1)
        self._paint_part(painter, p2, id2, win2, True)

    def _paint_part(self, painter: QPainter, name, id, win: bool, player2: bool = False):
        y_pos = 0 if not player2 else self.h + self.gap

        alive = not self.match.can_eliminate(player2, True) or self.match.winner is None or win

        if alive:
            id_rect_color = self.background_color2
            name_rect_color = self.background_color

            if win:
                s_rect_color = self.winner_color

            elif self.match is self.tournament.current:
                s_rect_color = self.current_color

            else:
                s_rect_color = self.background_color2

            name_color = self.text_color
            s_color = self.text_color2 if win else self.text_color

        else:
            id_rect_color = self.background_color4
            name_rect_color = self.background_color3
            s_rect_color = self.background_color4

            name_color = self.text_color2
            s_color = self.text_color2

        if self.isSelected():
            s_color = self.text_color
            s_rect_color = self.selected_color

        id_color = self.text_color2

        painter.setBrush(id_rect_color)
        painter.setPen(id_rect_color)

        id_rect = QRectF(self.w_mid, y_pos, self.s_idx, self.s_idx)
        painter.drawRect(id_rect)

        painter.setBrush(name_rect_color)
        painter.setPen(name_rect_color)

        name_rect = QRectF(self.s_idx + self.w_mid, y_pos, self.w_name, self.h)
        painter.drawRect(name_rect)

        painter.setBrush(s_rect_color)
        painter.setPen(s_rect_color)

        s_rect = QRectF(self.s_idx + self.w_mid + self.w_name, y_pos, self.s_score, self.s_score)
        painter.drawRect(s_rect)
        
        flags = Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter

        painter.setPen(id_color)
        painter.drawText(id_rect, flags, id)

        painter.setPen(s_color)
        painter.drawText(s_rect, flags, '1' if win else '0')

        flags = Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter

        painter.setPen(name_color)
        painter.drawText(QRectF(self.s_idx + self.w_mid + self.w_padding, y_pos, self.w_name - self.w_padding, self.h), flags, name)


    def mousePressEvent(self, event: QGraphicsSceneMouseEvent | None):
        return super().mousePressEvent(event)


    def _is_alive(self, player: Player):
        return self.match.bracket.id != "loser" or self.match.winner is None or self.match.winner is player


    def _get_scores(self):
        if self.match.winner is None:
            return '0', '0'

        if self.match.winner is self.match.player1:
            return '1', '0'

        return '0', '1'


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
        self.tournamentView.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.tournamentView.setResizeAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)

        self.tournamentView.viewport().installEventFilter(self)

        # Tournament actions
        self.actionStart.triggered.connect(self.startMatch)
        self.actionLoad.triggered.connect(self.select_and_load_tournament)
        self.actionReset.triggered.connect(self.reset_tournament)
        self.actionExport.triggered.connect(self.export_tournament)

        self.tournamentManager = TournamentManager()
        self.tournamentManager.tournament.arena = self.arena
        self.tournamentManager.tournament.view = self

        self.gf_reset_item = None

        self.line_margin = 10
        self.l_line = 30

        self.setup_view()

    def eventFilter(self, source, event):
        if (source is self.tournamentView.viewport() and
                event.type() == QEvent.Type.Wheel):
            if event.angleDelta().y() > 0:
                scale_factor = 1.25
            else:
                scale_factor = 0.8
            self.tournamentView.scale(scale_factor, scale_factor)
            return True
        return super().eventFilter(source, event)

    def startMatch(self):
        self.arena.game_manager.reload_and_start()

    def testwin(self):
        players = (self.tournamentManager.tournament.current.player1, self.tournamentManager.tournament.current.player2)

        self.tournamentManager.tournament.setWinnerAndNext(random.choice(players))

    def select_and_load_tournament(self):
        """Open tournament file selector and load the selected file"""
        path = QFileDialog.getOpenFileName(
            self, "Select tournament", self.TOURNAMENTS_DIR, "Tournament Files (*.yaml *.txt);;YAML Files (*.yaml);;Text Files (*.txt);;All Files (*)"
        )

        if path is None:
            return
        path = path[0]

        if self.tournamentManager.load_file(path):
            self.tournamentManager.tournament.arena = self.arena
            self.tournamentManager.tournament.view = self
            self.setup_view()
            # self.show_status("Tournament loaded")


    def draw_ln1(self, mat1: MatchItem, mat2: MatchItem, mat3: MatchItem):
        x1 = mat1.x() + mat1.width + self.line_margin
        x2 = x1 + self.l_line
        x3 = mat2.x() + mat2.width + self.line_margin
        x4 = x3 + self.l_line
        x6 = mat3.x() - self.line_margin
        x5 = (x6 + x2) / 2

        y1 = mat1.y() + mat1.height / 2
        y2 = mat2.y() + mat2.height / 2
        y3 = (y2 + y1) / 2
        y4 = mat3.y() + mat3.height / 2

        p1 = QPointF(x1, y1)
        p2 = QPointF(x2, y1)
        p3 = QPointF(x3, y2)
        p4 = QPointF(x4, y2)
        p5 = QPointF(x2, y3)
        p6 = QPointF(x5, y3)
        p7 = QPointF(x5, y4)
        p8 = QPointF(x6, y4)

        self.tournament_scene.addLine(QLineF(p1, p2)) #l1
        self.tournament_scene.addLine(QLineF(p3, p4)) #l2
        self.tournament_scene.addLine(QLineF(p2, p4)) #l3
        self.tournament_scene.addLine(QLineF(p5, p6)) #l4
        self.tournament_scene.addLine(QLineF(p6, p7)) #l5
        self.tournament_scene.addLine(QLineF(p7, p8)) #l6

    def draw_lngf(self, mat: MatchItem):
        wm = mat.match.player1_from.item
        lm = mat.match.player2_from.item

        x1 = mat.x() - self.line_margin
        x2 = lm.x() + lm.width + self.line_margin
        x3 = x2 + self.l_line
        x4 = wm.x() + wm.width + self.line_margin

        y1 = mat.y() + mat.height / 2
        y2 = lm.y() + lm.height / 2
        y3 = wm.y() + wm.height / 2
        
        p1 = QPointF(x1, y1)
        p2 = QPointF(x3, y1)
        p3 = QPointF(x3, y3)
        p4 = QPointF(x4, y3)
        p5 = QPointF(x3, y2)
        p6 = QPointF(x2, y2)

        self.tournament_scene.addLine(QLineF(p1, p2))
        self.tournament_scene.addLine(QLineF(p3, p5))
        self.tournament_scene.addLine(QLineF(p3, p4))
        self.tournament_scene.addLine(QLineF(p5, p6))


    
    def draw_ln2(self, mat1: MatchItem, mat2: MatchItem):
        x1 = mat1.x() + mat1.width + self.line_margin
        x2 = mat2.x() - self.line_margin

        y1 = mat1.y() + mat1.height / 2
        y2 = mat2.y() + mat2.height / 2

        p1 = QPointF(x1, y1)
        p2 = QPointF(x2, y2)

        self.tournament_scene.addLine(QLineF(p1, p2))
        

    def draw_lines(self):
        t = self.tournamentManager.tournament
        wb = t.brackets["winner"]
        lb = t.brackets["loser"]

        for i in range(len(wb.rounds) - 1):
            matches = wb.rounds[i].matches

            for j in range(0, len(matches), 2):
                mat1 = matches[j]
                mat2 = matches[j+1].item
                mat3 = mat1.winner_to.item

                self.draw_ln1(mat1.item, mat2, mat3)

        for i in range(len(lb.rounds) - 1):
            matches = lb.rounds[i].matches

            for j in range(0, len(matches), 2):
                mat1 = matches[j]

                if j == len(matches) - 1 and len(matches) % 2 == 1:
                    mat2 = mat1.winner_to.item

                    self.draw_ln2(mat1.item, mat2)
                    continue
                    


                mat2 = matches[j+1].item
                mat3 = mat1.winner_to.item

                self.draw_ln1(mat1.item, mat2, mat3)

        
        gf1 = t.grand_finals.matches[0]

        if len(t.grand_finals.matches) == 2:
            gf2 = t.grand_finals.matches[1]

            self.draw_ln2(gf1.item, gf2.item)

        self.draw_lngf(gf1.item)





    def setup_view(self):
        self.tournament_scene.clear()

        t = self.tournamentManager.tournament

        self.x_spacing = MatchItem.width + 200
        y_spacing = MatchItem.height + 40

        top_margin = 100

        rows = 1
        max_rows = 1

        # --- Winners Bracket ---
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

        # --- Losers Bracket ---

        max_matches_in_wb = max_rows - 1
        lb_vertical_offset = (max_matches_in_wb + 2) * y_spacing

        if "loser" in t.brackets:
            lb = t.brackets["loser"]
            for col, rnd in enumerate(lb.rounds):
                for row, mat in enumerate(rnd.matches):
                    item = MatchItem(mat, self.tournamentManager.tournament)
                    mat.item = item
                    x = (col + 1) * self.x_spacing
                    y = top_margin + lb_vertical_offset + row * y_spacing
                    item.setPos(x, y)
                    self.tournament_scene.addItem(item)

            lb_width = len(lb.rounds) * self.x_spacing + self.x_spacing
        else:
            lb_width = 0

        # --- Grand Finals ---
        gf = t.grand_finals

        gf_col = max(wb_width, lb_width)
        self.gf_x = gf_col
        self.gf_y = top_margin + max_matches_in_wb * y_spacing

        self.x_offset_gf = 0

        for i in range(len(gf.matches)):
            mat = gf.matches[i]

            gf_item = MatchItem(mat, self.tournamentManager.tournament)
            mat.item = gf_item
            gf_item.setPos(self.gf_x + self.x_offset_gf, self.gf_y)
            self.x_offset_gf += self.x_spacing

            self.tournament_scene.addItem(gf_item)

            if i == 1:
                self.gf_reset_item = gf_item


        self.draw_lines()

        self.tournament_scene.setSceneRect(self.tournament_scene.itemsBoundingRect())

    def addGFMatch(self, mat: Match):
        self.gf_reset_item = MatchItem(mat, self.tournamentManager.tournament)
        mat.item = self.gf_reset_item
        self.gf_reset_item.setPos(self.gf_x + self.x_offset_gf, self.gf_y)
        self.x_offset_gf += self.x_spacing

        self.tournament_scene.addItem(self.gf_reset_item)

        self.draw_ln2(self.tournamentManager.tournament.grand_finals.matches[0].item, mat.item)

        self.tournament_scene.setSceneRect(self.tournament_scene.itemsBoundingRect())

    def resetGF(self):
        if self.gf_reset_item is not None:
            self.tournament_scene.removeItem(self.gf_reset_item)
            self.gf_reset_item = None

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
        self.tournamentManager.tournament.reset()

        print("Tournament has been reset")
