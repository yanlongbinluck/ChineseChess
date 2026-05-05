
import copy
from collections import deque

FEN_START = "rnbakabnr/9/1c5c1/p1p1p1p1p/9/9/P1P1P1P1P/1C5C1/9/RNBAKABNR"

PIECE_MAP = {
    'K': '帅', 'k': '将',
    'A': '仕', 'a': '士',
    'B': '相', 'b': '象',
    'N': '馬', 'n': '馬',
    'R': '車', 'r': '車',
    'C': '炮', 'c': '砲',
    'P': '兵', 'p': '卒',
}

INITIAL_FEN = f"{FEN_START} w - - 0 1"


class ChessGame:
    def __init__(self, fen=INITIAL_FEN):
        self.move_history = []
        self.state_history = []
        self.load_fen(fen)

    def load_fen(self, fen):
        parts = fen.strip().split()
        board_str = parts[0]
        self.side = 'w' if parts[1] == 'w' else 'b'
        self._parse_board(board_str)
        self._update_in_check()
        self.move_history.clear()
        self.state_history.clear()

    def _parse_board(self, board_str):
        self.board = [[None] * 9 for _ in range(10)]
        rows = board_str.split('/')
        for r, row_str in enumerate(rows):
            c = 0
            for ch in row_str:
                if ch.isdigit():
                    c += int(ch)
                else:
                    self.board[r][c] = ch
                    c += 1

    def to_fen(self):
        fen_rows = []
        for r in range(10):
            row = ''
            empty = 0
            for c in range(9):
                p = self.board[r][c]
                if p is None:
                    empty += 1
                else:
                    if empty > 0:
                        row += str(empty)
                        empty = 0
                    row += p
            if empty > 0:
                row += str(empty)
            fen_rows.append(row)
        return '/'.join(fen_rows) + f" {self.side} - - 0 1"

    def is_red(self, piece):
        return piece.isupper()

    def is_black(self, piece):
        return piece.islower()

    def same_side(self, p1, p2):
        return (p1.isupper() and p2.isupper()) or (p1.islower() and p2.islower())

    def in_bounds(self, r, c):
        return 0 <= r < 10 and 0 <= c < 9

    def in_palace(self, r, c, side):
        if side == 'r':
            return 3 <= c <= 5 and 7 <= r <= 9
        else:
            return 3 <= c <= 5 and 0 <= r <= 2

    def in_own_half(self, r, side):
        if side == 'r':
            return 5 <= r <= 9
        else:
            return 0 <= r <= 4

    def _find_king(self, side):
        target = 'K' if side == 'r' else 'k'
        for r in range(10):
            for c in range(9):
                if self.board[r][c] == target:
                    return (r, c)
        return None

    def _kings_facing(self):
        rk = self._find_king('r')
        bk = self._find_king('b')
        if rk is None or bk is None:
            return False
        if rk[1] != bk[1]:
            return False
        min_r = min(rk[0], bk[0])
        max_r = max(rk[0], bk[0])
        for r in range(min_r + 1, max_r):
            if self.board[r][rk[1]] is not None:
                return False
        return True

    def _is_check(self, side):
        king_pos = self._find_king(side)
        if king_pos is None:
            return True
        opp = 'b' if side == 'r' else 'r'
        if self._is_attacked(king_pos[0], king_pos[1], opp):
            return True
        if self._kings_facing():
            return True
        return False

    def _update_in_check(self):
        self.in_check_red = self._is_check('r')
        self.in_check_black = self._is_check('b')

    def _is_attacked(self, r, c, attacker_side):
        for rr in range(10):
            for cc in range(9):
                p = self.board[rr][cc]
                if p is None:
                    continue
                if attacker_side == 'r' and not p.isupper():
                    continue
                if attacker_side == 'b' and not p.islower():
                    continue
                raw_moves = self._raw_piece_moves(rr, cc, p)
                if (r, c) in raw_moves:
                    return True
        return False

    def _raw_piece_moves(self, r, c, piece):
        moves = []
        p = piece.upper()
        if p == 'K':
            moves = self._king_moves(r, c, piece)
        elif p == 'A':
            moves = self._advisor_moves(r, c, piece)
        elif p == 'B':
            moves = self._elephant_moves(r, c, piece)
        elif p == 'N':
            moves = self._horse_moves(r, c, piece)
        elif p == 'R':
            moves = self._rook_moves(r, c, piece)
        elif p == 'C':
            moves = self._cannon_moves(r, c, piece)
        elif p == 'P':
            moves = self._pawn_moves(r, c, piece)
        return moves

    def _king_moves(self, r, c, piece):
        moves = []
        side = 'r' if piece.isupper() else 'b'
        for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            nr, nc = r + dr, c + dc
            if not self.in_bounds(nr, nc):
                continue
            if not self.in_palace(nr, nc, side):
                continue
            target = self.board[nr][nc]
            if target is None or not self.same_side(piece, target):
                moves.append((nr, nc))
        return moves

    def _advisor_moves(self, r, c, piece):
        moves = []
        side = 'r' if piece.isupper() else 'b'
        for dr, dc in [(-1, -1), (-1, 1), (1, -1), (1, 1)]:
            nr, nc = r + dr, c + dc
            if not self.in_bounds(nr, nc):
                continue
            if not self.in_palace(nr, nc, side):
                continue
            target = self.board[nr][nc]
            if target is None or not self.same_side(piece, target):
                moves.append((nr, nc))
        return moves

    def _elephant_moves(self, r, c, piece):
        moves = []
        side = 'r' if piece.isupper() else 'b'
        directions = [(-2, -2), (-2, 2), (2, -2), (2, 2)]
        eyes = [(-1, -1), (-1, 1), (1, -1), (1, 1)]
        for (dr, dc), (er, ec) in zip(directions, eyes):
            nr, nc = r + dr, c + dc
            eye_r, eye_c = r + er, c + ec
            if not self.in_bounds(nr, nc):
                continue
            if not self.in_own_half(nr, side):
                continue
            if self.board[eye_r][eye_c] is not None:
                continue
            target = self.board[nr][nc]
            if target is None or not self.same_side(piece, target):
                moves.append((nr, nc))
        return moves

    def _horse_moves(self, r, c, piece):
        moves = []
        leg_offsets = [(-1, 0, -2, -1), (-1, 0, -2, 1),
                       (1, 0, 2, -1), (1, 0, 2, 1),
                       (0, -1, -1, -2), (0, -1, 1, -2),
                       (0, 1, -1, 2), (0, 1, 1, 2)]
        for lr, lc, dr, dc in leg_offsets:
            leg_r, leg_c = r + lr, c + lc
            nr, nc = r + dr, c + dc
            if not self.in_bounds(nr, nc):
                continue
            if self.board[leg_r][leg_c] is not None:
                continue
            target = self.board[nr][nc]
            if target is None or not self.same_side(piece, target):
                moves.append((nr, nc))
        return moves

    def _rook_moves(self, r, c, piece):
        return self._slide_moves(r, c, piece, [(0, 1), (0, -1), (1, 0), (-1, 0)])

    def _cannon_moves(self, r, c, piece):
        moves = []
        for dr, dc in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
            nr, nc = r + dr, c + dc
            while self.in_bounds(nr, nc):
                if self.board[nr][nc] is None:
                    moves.append((nr, nc))
                else:
                    screen_r, screen_c = nr + dr, nc + dc
                    while self.in_bounds(screen_r, screen_c):
                        if self.board[screen_r][screen_c] is not None:
                            target = self.board[screen_r][screen_c]
                            if not self.same_side(piece, target):
                                moves.append((screen_r, screen_c))
                            break
                        screen_r += dr
                        screen_c += dc
                    break
                nr += dr
                nc += dc
        return moves

    def _pawn_moves(self, r, c, piece):
        moves = []
        if piece.isupper():
            forward = -1
            crossed = (r <= 4)
        else:
            forward = 1
            crossed = (r >= 5)

        nr = r + forward
        if self.in_bounds(nr, c):
            target = self.board[nr][c]
            if target is None or not self.same_side(piece, target):
                moves.append((nr, c))

        if crossed:
            for dc in [-1, 1]:
                nc = c + dc
                if self.in_bounds(r, nc):
                    target = self.board[r][nc]
                    if target is None or not self.same_side(piece, target):
                        moves.append((r, nc))
        return moves

    def _slide_moves(self, r, c, piece, directions):
        moves = []
        for dr, dc in directions:
            nr, nc = r + dr, c + dc
            while self.in_bounds(nr, nc):
                target = self.board[nr][nc]
                if target is None:
                    moves.append((nr, nc))
                else:
                    if not self.same_side(piece, target):
                        moves.append((nr, nc))
                    break
                nr += dr
                nc += dc
        return moves

    def legal_moves(self, r, c):
        piece = self.board[r][c]
        if piece is None:
            return []
        side = 'r' if piece.isupper() else 'b'
        current_side = 'r' if self.side == 'w' else 'b'
        if side != current_side:
            return []
        raw = self._raw_piece_moves(r, c, piece)
        legal = []
        for (nr, nc) in raw:
            if self._is_move_legal(r, c, nr, nc, piece):
                legal.append((nr, nc))
        return legal

    def _is_move_legal(self, r, c, nr, nc, piece):
        captured = self.board[nr][nc]
        self.board[nr][nc] = piece
        self.board[r][c] = None
        side = 'r' if piece.isupper() else 'b'
        king_pos = self._find_king(side)
        check = False
        if king_pos and self._kings_facing():
            check = True
        if not check and king_pos:
            opp = 'b' if side == 'r' else 'r'
            check = self._is_attacked(king_pos[0], king_pos[1], opp)
        self.board[r][c] = piece
        self.board[nr][nc] = captured
        return not check

    def make_move(self, r, c, nr, nc):
        piece = self.board[r][c]
        captured = self.board[nr][nc]
        self.move_history.append((r, c, nr, nc, piece, captured))
        self.state_history.append((self.side, copy.deepcopy(self.board)))
        self.board[nr][nc] = piece
        self.board[r][c] = None
        self.side = 'b' if self.side == 'w' else 'w'
        self._update_in_check()
        return True

    def undo_move(self):
        if not self.move_history:
            return False
        r, c, nr, nc, piece, captured = self.move_history.pop()
        self.side, _ = self.state_history.pop()
        self.board[r][c] = piece
        self.board[nr][nc] = captured
        self._update_in_check()
        return True

    def all_legal_moves(self):
        moves = []
        side = 'r' if self.side == 'w' else 'b'
        for r in range(10):
            for c in range(9):
                p = self.board[r][c]
                if p is None:
                    continue
                if side == 'r' and not p.isupper():
                    continue
                if side == 'b' and not p.islower():
                    continue
                for (nr, nc) in self.legal_moves(r, c):
                    moves.append((r, c, nr, nc))
        return moves

    def is_checkmate(self):
        return len(self.all_legal_moves()) == 0

    def move_to_uci(self, r, c, nr, nc):
        return f"{chr(ord('a') + c)}{9 - r}{chr(ord('a') + nc)}{9 - nr}"

    def uci_to_move(self, uci):
        c = ord(uci[0]) - ord('a')
        r = 9 - int(uci[1])
        nc = ord(uci[2]) - ord('a')
        nr = 9 - int(uci[3])
        return (r, c, nr, nc)

    def get_board_state(self):
        return [row[:] for row in self.board]
