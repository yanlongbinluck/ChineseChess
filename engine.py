
import subprocess
import threading
import os
import time
import queue


class ChessEngine:
    def __init__(self, engine_path=None, debug_callback=None):
        self._debug = debug_callback
        self.engine_path = engine_path or self._find_engine()
        self.process = None
        self.lock = threading.Lock()
        self.ready = False
        self.best_move = None
        self.searching = False
        self._name = "Unknown"
        self.available = False
        self._output_queue = queue.Queue()

        if self.engine_path and os.path.exists(self.engine_path):
            try:
                self._start_engine()
                self.available = True
            except Exception as e:
                self._log(f"引擎启动失败: {e}")
                self.available = False

    def _log(self, msg):
        if self._debug:
            try:
                self._debug(f"[Engine] {msg}")
            except Exception:
                pass

    def _find_engine(self):
        search_names = ["pikafish.exe", "pikafish", "Pikafish.exe"]
        search_dirs = [
            os.path.dirname(os.path.abspath(__file__)),
            os.path.join(os.path.dirname(os.path.abspath(__file__)), "engine"),
            os.getcwd(),
            os.path.join(os.getcwd(), "engine"),
        ]
        for d in search_dirs:
            if not os.path.isdir(d):
                continue
            for name in search_names:
                path = os.path.join(d, name)
                if os.path.isfile(path):
                    self._log(f"找到引擎: {path}")
                    return path
        for name in search_names:
            path = self._which(name)
            if path:
                self._log(f"在PATH中找到引擎: {path}")
                return path
        return None

    def _which(self, name):
        for p in os.environ.get("PATH", "").split(os.pathsep):
            fpath = os.path.join(p, name)
            if os.path.isfile(fpath):
                return fpath
            if os.path.isfile(fpath + ".exe"):
                return fpath + ".exe"
        return None

    def _start_engine(self):
        try:
            self.process = subprocess.Popen(
                [self.engine_path],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0,
            )
        except Exception:
            self.process = subprocess.Popen(
                [self.engine_path],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
            )
        self._reader_thread = threading.Thread(target=self._read_output, daemon=True)
        self._reader_thread.start()
        self._send("uci")
        time.sleep(0.3)
        self._send("setoption name UCI_Variant value xiangqi")
        time.sleep(0.1)
        self._wait_ready(timeout=10)

    def _send(self, cmd):
        if self.process and self.process.stdin:
            try:
                self.process.stdin.write(cmd + "\n")
                self.process.stdin.flush()
            except Exception as e:
                self._log(f"发送命令失败: {e}")

    def _read_output(self):
        while self.process and self.process.stdout:
            try:
                line = self.process.stdout.readline()
                if not line:
                    break
                line = line.strip()
                if not line:
                    continue
                self._log(f"<- {line}")
                if line.startswith("id name"):
                    self._name = line.split("id name", 1)[1].strip()
                elif line.startswith("uciok"):
                    self.ready = True
                elif line.startswith("readyok"):
                    pass
                elif line.startswith("bestmove"):
                    parts = line.split()
                    if len(parts) >= 2:
                        self.best_move = parts[1]
                        self._log(f"最佳着法: {self.best_move}")
                    self.searching = False
            except Exception as e:
                self._log(f"读取输出异常: {e}")
                break

    def _wait_ready(self, timeout=10):
        self._send("isready")
        start = time.time()
        while not self.ready:
            if time.time() - start > timeout:
                self._log(f"等待引擎就绪超时 ({timeout}s)")
                self.ready = True
                break
            time.sleep(0.05)
        time.sleep(0.1)
        self._log(f"引擎就绪, 名称: {self._name}")

    def get_name(self):
        return self._name

    def search(self, fen, movetime=2000, depth=None):
        if not self.available:
            return None
        with self.lock:
            self.best_move = None
            self.searching = True
            self._send(f"position fen {fen}")
            if depth:
                self._send(f"go depth {depth}")
            else:
                self._send(f"go movetime {movetime}")
            start = time.time()
            timeout = (movetime / 1000) + 5 if depth is None else 30
            while self.searching:
                if time.time() - start > timeout:
                    self._send("stop")
                    break
                time.sleep(0.05)
            result = self.best_move
            self.best_move = None
            if result:
                self._log(f"返回着法: {result}")
            else:
                self._log("未收到着法")
            return result

    def quit(self):
        if self.process:
            try:
                self._send("quit")
                self.process.terminate()
                self.process.wait(timeout=2)
            except Exception:
                pass
            self.process = None
        self.available = False
