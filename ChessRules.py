

def check_player_defeated(player_color, board):
    for x in range(board.shape[0]):
        for y in range(board.shape[1]):
            if board[x,y] == 'k'+player_color:
                return False
    return True

def move_is_valid(player_order, move, board):
    player_color = player_order[1]
    player_team = int(player_order[0])
    other_teams = [int(e) for e in player_order[::3]]
    other_teams.remove(player_team)

    #   Helper
    def is_free(pos):
        val = board[pos[0], pos[1]]
        return val == '' or val is None

    def color_at(pos):
        return board[pos[0], pos[1]][1]

    def team_at(pos):
        col = color_at(pos)
        return int(player_order[int(player_order.find(col)-1)])

    def can_move_or_capture(pos):
        return is_free(pos) or team_at(pos) != player_team

    def can_move_diagonally():
        dx = end[0] - start[0]
        dy = end[1] - start[1]

        def stepto(end):
            delta = 1 if end > 0 else -1
            i = delta
            while abs(i) < abs(end):
                yield i
                i += delta

        if abs(dx) == abs(dy):  #   diagonal move
            for x,y in zip(stepto(dx), stepto(dy)):
                if not is_free((start[0]+x,start[1]+y)):
                    return False
            return can_move_or_capture(end)
        else:   # Invalid bishop move (only diagonals)
            return False

    def can_move_along_axis():
        dx = end[0] - start[0]
        dy = end[1] - start[1]

        if (dx == 0) != (dy == 0):  #   along the axis movement one must be equals to 0
            dst = dx+dy
            delta = 1 if dst > 0 else -1
            Xaxis,Yaxis = (delta,0) if dx != 0 else (0,delta)

            for i in range(1, abs(dst)):
                if not is_free((start[0] + Xaxis * i, start[1] + Yaxis * i)):
                    return False

            return can_move_or_capture(end)
        else:   # Invalid bishop move (only diagonals)
            return False


    start, end = move
    #   Check boundary condition
    if start[0] < 0 or start[0] >= board.shape[0] or \
       start[1] < 0 or start[1] >= board.shape[1]:
       return False

    #   Check boundary condition
    if end[0] < 0 or end[0] >= board.shape[0] or \
       end[1] < 0 or end[1] >= board.shape[1]:
       return False

    #   Check piece moved
    if board[start[0], start[1]] in ('', 'X', None):
        return False

    piece = board[start[0], start[1]]
    
    #   Moving right color
    if piece.color != player_color:
        return False

    #   check piece specific rules
    if piece.type == 'p':
        if end[0] != start[0] + 1: #    Pawn always move forward
            return False

        if end[1] == start[1]:
            return is_free(end)
        
        if is_free(end):
            # Diagonal but no piece
            return False
        
        #   Capture ?
        print(team_at(end), "!=", player_team, "==", team_at(end) != player_team)
        return abs(end[1] - start[1]) == 1 and (not is_free(end)) and team_at(end) != player_team
    elif piece.type == 'n':
        dx = abs(end[0] - start[0])
        dy = abs(end[1] - start[1])

        if (dx == 1 and dy == 2) or (dx == 2 and dy == 1):
            return can_move_or_capture(end)
        else: # invalid knight move
            return False

    elif piece.type == 'b':
        return can_move_diagonally()

    elif piece.type == 'r':
        return can_move_along_axis()

    elif piece.type == "q":
        return can_move_diagonally() != can_move_along_axis()

    elif piece.type == "k":
        dx = abs(end[0] - start[0])
        dy = abs(end[1] - start[1])

        return (-1 <= dx <= 1 and -1 <= dy <= 1) and can_move_or_capture(end)

    return False
