
import tkinter as tk
from tkinter import messagebox
import os
import threading

from chess_game import ChessGame, PIECE_MAP, INITIAL_FEN
from engine import ChessEngine

COLORS = {
    'bg': '#f0d9a0',
    'board_bg': '#e8c870',
    'grid': '#4a3728',
    'red_piece': '#c0392b',
    'black_piece': '#1a1a2e',
    'piece_bg': '#fdebd0',
    'piece_ring': '#4a3728',
    'selected': '#27ae60',
    'last_move_sq': '#b8e6b8',
    'legal_dot': '#7f8c8d',
    'check_highlight': '#e74c3c',
    'status_bg': '#2c3e50',
    'status_fg': '#ecf0f1',
    'arrow': '#27ae60',
}

FONT_FAMILY = 'Microsoft YaHei'


class ChineseChessGUI:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("中国象棋 - Chinese Chess")
        self.root.resizable(False, False)
        self.root.configure(bg=COLORS['status_bg'])

        self.game = ChessGame()
        self.engine = ChessEngine(debug_callback=self._log)
        self.engine_move_event = threading.Event()

        self.selected = None
        self.legal_destinations = []
        self.last_move = None
        self.player_color = 'r'
        self._engine_time = 1500
        self._engine_depth = 4
        self._search_mode = tk.StringVar(value="time")

        self._board_size = 56
        self._padding = 40
        self._canvas_w = 8 * self._board_size + 2 * self._padding
        self._canvas_h = 9 * self._board_size + 2 * self._padding

        self._build_ui()
        self._draw_board()

        if self.engine.available:
            self._log(f"引擎已连接: {self.engine.get_name()}")
        else:
            self._log("未找到 Pikafish 引擎，请将 pikafish.exe 放在程序目录下")

        self._update_status()
        self._check_engine_turn()
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        self.root.mainloop()

    def _build_ui(self):
        board_frame = tk.Frame(self.root, bg=COLORS['status_bg'])
        board_frame.pack(padx=6, pady=(6, 0))

        self.canvas = tk.Canvas(
            board_frame,
            width=self._canvas_w,
            height=self._canvas_h,
            bg=COLORS['board_bg'],
            highlightthickness=0,
        )
        self.canvas.pack()
        self.canvas.bind("<Button-1>", self._on_canvas_click)

        control_frame = tk.Frame(self.root, bg=COLORS['status_bg'])
        control_frame.pack(fill=tk.X, padx=6, pady=6)

        btn_font = (FONT_FAMILY, 9)
        label_font = (FONT_FAMILY, 8)

        tk.Button(control_frame, text="新游戏", command=self._new_game,
                  font=btn_font, relief=tk.GROOVE, bd=2, width=8).pack(side=tk.LEFT, padx=2)
        tk.Button(control_frame, text="悔棋", command=self._undo,
                  font=btn_font, relief=tk.GROOVE, bd=2, width=8).pack(side=tk.LEFT, padx=2)
        tk.Button(control_frame, text="切换红/黑", command=self._switch_side,
                  font=btn_font, relief=tk.GROOVE, bd=2, width=9).pack(side=tk.LEFT, padx=2)

        self.engine_var = tk.BooleanVar(value=True)
        tk.Checkbutton(
            control_frame, text="启用引擎", variable=self.engine_var,
            command=self._on_engine_toggle,
            font=(FONT_FAMILY, 8), bg=COLORS['status_bg'], fg=COLORS['status_fg'],
            selectcolor=COLORS['status_bg'],
            activebackground=COLORS['status_bg'], activeforeground=COLORS['status_fg'],
        ).pack(side=tk.LEFT, padx=4)

        rb_font = (FONT_FAMILY, 8)
        self.time_var = tk.StringVar(value=str(self._engine_time))
        self.depth_var = tk.StringVar(value=str(self._engine_depth))

        tk.Radiobutton(control_frame, text="时限", variable=self._search_mode,
                       value="time", command=self._on_mode_change,
                       font=rb_font, bg=COLORS['status_bg'], fg=COLORS['status_fg'],
                       selectcolor=COLORS['status_bg'],
                       activebackground=COLORS['status_bg'], activeforeground=COLORS['status_fg'],
                       ).pack(side=tk.LEFT, padx=(8, 1))
        self.time_spin = tk.Spinbox(
            control_frame, textvariable=self.time_var, from_=200, to=30000, increment=500,
            width=6, font=label_font, command=self._on_time_change,
            state='readonly',
        )
        self.time_spin.pack(side=tk.LEFT, padx=(1, 0))
        tk.Label(control_frame, text="ms", font=label_font, fg=COLORS['status_fg'],
                 bg=COLORS['status_bg']).pack(side=tk.LEFT, padx=(0, 6))

        tk.Radiobutton(control_frame, text="深度", variable=self._search_mode,
                       value="depth", command=self._on_mode_change,
                       font=rb_font, bg=COLORS['status_bg'], fg=COLORS['status_fg'],
                       selectcolor=COLORS['status_bg'],
                       activebackground=COLORS['status_bg'], activeforeground=COLORS['status_fg'],
                       ).pack(side=tk.LEFT, padx=(0, 1))
        self.depth_spin = tk.Spinbox(
            control_frame, textvariable=self.depth_var, from_=1, to=30, increment=1,
            width=4, font=label_font, command=self._on_depth_change,
            state='disabled',
        )
        self.depth_spin.pack(side=tk.LEFT, padx=(1, 6))
        self.depth_spin.bind('<MouseWheel>', self._on_depth_wheel)

        self.status_label = tk.Label(
            self.root, text="",
            font=(FONT_FAMILY, 10, 'bold'),
            bg=COLORS['status_bg'], fg=COLORS['status_fg'],
            pady=3,
        )
        self.status_label.pack(fill=tk.X, padx=6)

        self.log_text = tk.Text(
            self.root, height=3,
            font=(FONT_FAMILY, 8),
            bg='#1a252f', fg='#bdc3c7',
            state=tk.DISABLED, relief=tk.FLAT,
            padx=4, pady=3,
        )
        self.log_text.pack(fill=tk.X, padx=6, pady=(0, 6))

    def _on_mode_change(self):
        mode = self._search_mode.get()
        if mode == "time":
            self.time_spin.config(state='readonly')
            self.depth_spin.config(state='disabled')
        else:
            self.time_spin.config(state='disabled')
            self.depth_spin.config(state='readonly')

    def _on_depth_change(self):
        try:
            self._engine_depth = int(self.depth_var.get())
            if self._engine_depth < 1:
                self._engine_depth = 1
                self.depth_var.set("1")
        except ValueError:
            self._engine_depth = 4

    def _on_depth_wheel(self, event):
        d = self._engine_depth
        d += 1 if event.delta > 0 else -1
        d = max(1, min(30, d))
        self._engine_depth = d
        self.depth_var.set(str(d))

    def _on_time_change(self):
        try:
            self._engine_time = int(self.time_var.get())
        except ValueError:
            self._engine_time = 1500

    def _on_time_wheel(self, event):
        t = self._engine_time
        step = 500 if abs(event.delta) > 60 else 100
        t += step if event.delta > 0 else -step
        t = max(200, min(30000, t))
        self._engine_time = t
        self.time_var.set(str(t))

    def _log(self, msg):
        self.log_text.config(state=tk.NORMAL)
        self.log_text.insert(tk.END, f"{msg}\n")
        self.log_text.see(tk.END)
        self.log_text.config(state=tk.DISABLED)

    def _coord_to_xy(self, r, c):
        x = self._padding + c * self._board_size
        y = self._padding + r * self._board_size
        return x, y

    def _xy_to_coord(self, x, y):
        c = round((x - self._padding) / self._board_size)
        r = round((y - self._padding) / self._board_size)
        if 0 <= r < 10 and 0 <= c < 9:
            return r, c
        return None, None

    def _draw_board(self):
        self.canvas.delete("all")
        self._draw_grid()
        self._draw_river()
        self._draw_palace_lines()
        self._draw_move_arrow()
        self._draw_last_move_squares()
        self._draw_pieces()
        self._draw_selection()
        self._draw_legal_markers()

    def _draw_grid(self):
        for r in range(10):
            x1, y1 = self._coord_to_xy(r, 0)
            x2, y2 = self._coord_to_xy(r, 8)
            self.canvas.create_line(x1, y1, x2, y2, fill=COLORS['grid'], width=1)

        for c in range(9):
            x1, y1 = self._coord_to_xy(0, c)
            x2, y2 = self._coord_to_xy(9, c)
            if c == 0 or c == 8:
                self.canvas.create_line(x1, y1, x2, y2, fill=COLORS['grid'], width=1)
            else:
                xm, ym = self._coord_to_xy(4, c)
                self.canvas.create_line(x1, y1, xm, ym, fill=COLORS['grid'], width=1)
                xm2, ym2 = self._coord_to_xy(5, c)
                self.canvas.create_line(xm2, ym2, x2, y2, fill=COLORS['grid'], width=1)

    def _draw_river(self):
        y1 = self._coord_to_xy(4, 0)[1]
        y2 = self._coord_to_xy(5, 0)[1]
        mid_y = (y1 + y2) / 2
        font_size = max(12, int(self._board_size * 0.22))
        self.canvas.create_text(
            self._canvas_w / 2 - 55, mid_y,
            text="楚  河", font=(FONT_FAMILY, font_size, 'bold'),
            fill=COLORS['grid'],
        )
        self.canvas.create_text(
            self._canvas_w / 2 + 55, mid_y,
            text="汉  界", font=(FONT_FAMILY, font_size, 'bold'),
            fill=COLORS['grid'],
        )

    def _draw_palace_lines(self):
        for (r1, c1, r2, c2) in [(0, 3, 2, 5), (0, 5, 2, 3),
                                  (7, 3, 9, 5), (7, 5, 9, 3)]:
            x1, y1 = self._coord_to_xy(r1, c1)
            x2, y2 = self._coord_to_xy(r2, c2)
            self.canvas.create_line(x1, y1, x2, y2, fill=COLORS['grid'], width=1)

    def _draw_move_arrow(self):
        if not self.last_move:
            return
        r1, c1, r2, c2 = self.last_move
        x1, y1 = self._coord_to_xy(r1, c1)
        x2, y2 = self._coord_to_xy(r2, c2)

        dx, dy = x2 - x1, y2 - y1
        length = (dx * dx + dy * dy) ** 0.5
        if length < 1:
            return
        ux, uy = dx / length, dy / length
        offset = self._board_size * 0.38
        sx, sy = x1 + ux * offset, y1 + uy * offset
        ex, ey = x2 - ux * offset, y2 - uy * offset

        self.canvas.create_line(
            sx, sy, ex, ey,
            fill=COLORS['arrow'],
            width=max(3, int(self._board_size * 0.07)),
            arrow=tk.LAST,
            arrowshape=(12, 14, 5),
            tags="arrow",
        )

    def _draw_last_move_squares(self):
        if not self.last_move:
            return
        r_s = self._board_size * 0.78
        for (r, c) in [(self.last_move[0], self.last_move[1]),
                       (self.last_move[2], self.last_move[3])]:
            x, y = self._coord_to_xy(r, c)
            self.canvas.create_rectangle(
                x - r_s / 2, y - r_s / 2,
                x + r_s / 2, y + r_s / 2,
                fill=COLORS['last_move_sq'],
                outline='',
                tags="last_sq",
            )

    def _draw_pieces(self):
        r_s = self._board_size * 0.76
        piece_font_size = max(12, int(self._board_size * 0.28))
        for r in range(10):
            for c in range(9):
                piece = self.game.board[r][c]
                if piece is None:
                    continue
                x, y = self._coord_to_xy(r, c)
                color = COLORS['red_piece'] if piece.isupper() else COLORS['black_piece']
                self.canvas.create_oval(
                    x - r_s / 2, y - r_s / 2,
                    x + r_s / 2, y + r_s / 2,
                    fill=COLORS['piece_bg'],
                    outline=COLORS['piece_ring'],
                    width=2,
                    tags="piece",
                )
                self.canvas.create_text(
                    x + 1, y + 1,
                    text=PIECE_MAP[piece],
                    font=(FONT_FAMILY, piece_font_size, 'bold'),
                    fill=color,
                    tags="piece",
                )

    def _draw_selection(self):
        if not self.selected:
            return
        r, c = self.selected
        x, y = self._coord_to_xy(r, c)
        r_s = self._board_size * 0.76
        self.canvas.create_rectangle(
            x - r_s / 2 - 3, y - r_s / 2 - 3,
            x + r_s / 2 + 3, y + r_s / 2 + 3,
            outline=COLORS['selected'],
            width=3,
            tags="selection",
        )

    def _draw_legal_markers(self):
        r_s = self._board_size * 0.76
        for (r, c) in self.legal_destinations:
            x, y = self._coord_to_xy(r, c)
            target = self.game.board[r][c]
            if target is not None:
                self.canvas.create_rectangle(
                    x - r_s / 2 - 2, y - r_s / 2 - 2,
                    x + r_s / 2 + 2, y + r_s / 2 + 2,
                    outline=COLORS['check_highlight'],
                    width=3,
                    tags="legal",
                )
            else:
                dot_r = max(3, int(self._board_size * 0.08))
                self.canvas.create_oval(
                    x - dot_r, y - dot_r,
                    x + dot_r, y + dot_r,
                    fill=COLORS['legal_dot'],
                    outline='',
                    tags="legal",
                )

    def _on_canvas_click(self, event):
        if self._is_engine_turn():
            return
        r, c = self._xy_to_coord(event.x, event.y)
        if r is None:
            return

        if self.selected:
            if (r, c) in self.legal_destinations:
                self._make_move(self.selected[0], self.selected[1], r, c)
                self.selected = None
                self.legal_destinations = []
            else:
                piece = self.game.board[r][c]
                if piece:
                    side = 'r' if piece.isupper() else 'b'
                    if side == self.player_color:
                        self.selected = (r, c)
                        self.legal_destinations = self.game.legal_moves(r, c)
                    else:
                        self.selected = None
                        self.legal_destinations = []
                else:
                    self.selected = None
                    self.legal_destinations = []
        else:
            piece = self.game.board[r][c]
            if piece:
                side = 'r' if piece.isupper() else 'b'
                if side == self.player_color:
                    self.selected = (r, c)
                    self.legal_destinations = self.game.legal_moves(r, c)
        self._draw_board()
        self._update_status()

    def _make_move(self, r, c, nr, nc):
        piece = self.game.board[r][c]
        captured = self.game.board[nr][nc]
        self.game.make_move(r, c, nr, nc)
        self.last_move = (r, c, nr, nc)

        p_name = PIECE_MAP.get(piece, piece)
        cap_name = PIECE_MAP.get(captured, "") if captured else ""
        move_desc = f"{p_name} {chr(ord('a') + c)}{r} -> {chr(ord('a') + nc)}{nr}"
        if cap_name:
            move_desc += f" 吃{cap_name}"
        self._log(move_desc)

        self._draw_board()
        self._update_status()
        self._check_game_over()
        self._check_engine_turn()

    def _is_engine_turn(self):
        return (
            self.engine.available
            and self.engine_var.get()
            and not self.game.is_checkmate()
            and self._get_engine_side() == ('r' if self.game.side == 'w' else 'b')
        )

    def _get_engine_side(self):
        return 'b' if self.player_color == 'r' else 'r'

    def _check_engine_turn(self):
        if self._is_engine_turn():
            self.status_label.config(text="引擎思考中...")
            self.canvas.config(cursor="watch")
            threading.Thread(target=self._engine_move, daemon=True).start()

    def _engine_move(self):
        fen = self.game.to_fen()
        if self._search_mode.get() == "depth":
            depth = self._engine_depth
            movetime = 30000
        else:
            depth = None
            movetime = self._engine_time
        self._log(f"引擎搜索, FEN: {fen}")
        uci_move = self.engine.search(fen, movetime=movetime, depth=depth)
        if uci_move and uci_move != "(none)" and uci_move != "0000":
            try:
                r, c, nr, nc = self.game.uci_to_move(uci_move)
                self._log(f"引擎着法: {uci_move} -> ({r},{c})->({nr},{nc})")
                self.root.after(0, lambda: self._apply_engine_move(r, c, nr, nc, uci_move))
            except Exception as e:
                self._log(f"解析着法异常: {e}")
                self.root.after(0, self._on_engine_error)
        else:
            self._log(f"引擎返回无效着法: {uci_move}")
            self.root.after(0, self._on_engine_error)

    def _apply_engine_move(self, r, c, nr, nc, raw_uci=""):
        if not self._is_engine_turn():
            self._draw_board()
            self._update_status()
            return
        piece = self.game.board[r][c]
        if piece is None:
            self._log(f"引擎着法起点 ({r},{c}) 无棋子, 原始: {raw_uci}")
            self._on_engine_error()
            return
        legal = self.game.legal_moves(r, c)
        if (nr, nc) not in legal:
            self._log(f"引擎着法 ({r},{c})->({nr},{nc}) 不合法")
            self._log(f"合法着法: {legal}")
            self._fallback_engine_move()
            return
        self.selected = None
        self.legal_destinations = []
        self._make_move(r, c, nr, nc)
        self.canvas.config(cursor="")

    def _fallback_engine_move(self):
        fen = self.game.to_fen()
        uci_move = self.engine.search(fen, movetime=5000, depth=10)
        if uci_move and uci_move != "(none)" and uci_move != "0000":
            try:
                r, c, nr, nc = self.game.uci_to_move(uci_move)
                piece = self.game.board[r][c]
                if piece is None:
                    self._on_engine_error()
                    return
                legal = self.game.legal_moves(r, c)
                if (nr, nc) in legal:
                    self.selected = None
                    self.legal_destinations = []
                    self._make_move(r, c, nr, nc)
                    self.canvas.config(cursor="")
                    return
            except Exception:
                pass
        self._on_engine_error()

    def _on_engine_error(self):
        self._log("引擎出错")
        self.canvas.config(cursor="")
        self._draw_board()
        self._update_status()

    def _update_status(self):
        if self.game.is_checkmate():
            winner = "黑方" if self.game.side == 'w' else "红方"
            self.status_label.config(text=f"将死! {winner}获胜!")
            return

        side = "红方" if self.game.side == 'w' else "黑方"
        check = ""
        if self.game.in_check_red and self.game.side == 'w':
            check = " (被将!)"
        elif self.game.in_check_black and self.game.side == 'b':
            check = " (被将!)"

        engine_side = ""
        if self._is_engine_turn():
            engine_side = " [引擎]"
        self.status_label.config(text=f"{side}走棋{check}{engine_side}")

    def _check_game_over(self):
        if self.game.is_checkmate():
            winner = "黑方" if self.game.side == 'w' else "红方"
            messagebox.showinfo("游戏结束", f"将死! {winner}获胜!")
            self.status_label.config(text=f"将死! {winner}获胜!")

    def _new_game(self):
        self.game = ChessGame()
        self.selected = None
        self.legal_destinations = []
        self.last_move = None
        self._draw_board()
        self._update_status()
        self._log("=== 新游戏开始 ===")
        self._check_engine_turn()

    def _undo(self):
        if self._is_engine_turn():
            return
        if self.game.move_history:
            undo_count = 2 if self.engine.available and self.engine_var.get() else 1
            for _ in range(undo_count):
                if not self.game.move_history:
                    break
                self.game.undo_move()
            self.selected = None
            self.legal_destinations = []
            if self.game.move_history:
                h = self.game.move_history[-1]
                self.last_move = (h[0], h[1], h[2], h[3])
            else:
                self.last_move = None
            self._draw_board()
            self._update_status()
            self._log("悔棋")

    def _switch_side(self):
        if self.game.move_history:
            if not messagebox.askyesno("切换阵营", "当前有对局进行中，切换将开始新游戏，是否继续?"):
                return
        self.player_color = 'b' if self.player_color == 'r' else 'r'
        side_name = "红方" if self.player_color == 'r' else "黑方"
        self._log(f"玩家切换为: {side_name}")
        self._new_game()

    def _on_engine_toggle(self):
        if self.engine.available:
            state = "启用" if self.engine_var.get() else "禁用"
            self._log(f"{state}引擎")
            self._check_engine_turn()

    def _on_close(self):
        if self.engine:
            self.engine.quit()
        self.root.destroy()


if __name__ == "__main__":
    ChineseChessGUI()
