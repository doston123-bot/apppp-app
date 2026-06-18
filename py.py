import json
import re
import urllib.error
import urllib.request
import tkinter as tk
from dataclasses import dataclass
from datetime import datetime
from tkinter import filedialog, messagebox, ttk
from typing import Any, Callable, Dict, List, Optional

LOG_PATTERN = re.compile(
    r"\[(?P<timestamp>[^\]]+)\]\s+"
    r"(?P<level>\w+)\s+"
    r"(?P<code>\d+):\s+"
    r"(?P<message>.+)"
)
SUPPORTED_DATE_FORMATS = ["%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M"]
API_URL_TEMPLATE = "https://api.exchangerate.host/latest?base={base}"


@dataclass
class LogEntry:
    timestamp: datetime
    level: str
    code: str
    message: str
    raw: str


def quick_sort(items: List[Any], key: Callable[[Any], Any] = lambda x: x, reverse: bool = False) -> List[Any]:
    if len(items) <= 1:
        return items
    pivot = items[len(items) // 2]
    pivot_key = key(pivot)
    left = [item for item in items if key(item) < pivot_key]
    center = [item for item in items if key(item) == pivot_key]
    right = [item for item in items if key(item) > pivot_key]
    if reverse:
        return quick_sort(right, key, reverse) + center + quick_sort(left, key, reverse)
    return quick_sort(left, key, reverse) + center + quick_sort(right, key, reverse)


def binary_search(items: List[Any], target: Any, key: Callable[[Any], Any] = lambda x: x) -> int:
    low = 0
    high = len(items) - 1
    while low <= high:
        mid = (low + high) // 2
        value = key(items[mid])
        if value == target:
            return mid
        if value < target:
            low = mid + 1
        else:
            high = mid - 1
    return -1


def parse_timestamp(value: str) -> Optional[datetime]:
    for fmt in SUPPORTED_DATE_FORMATS:
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            continue
    return None


def parse_log_line(line: str) -> Optional[LogEntry]:
    match = LOG_PATTERN.match(line.strip())
    if not match:
        return None
    timestamp = parse_timestamp(match.group("timestamp"))
    if not timestamp:
        return None
    return LogEntry(
        timestamp=timestamp,
        level=match.group("level"),
        code=match.group("code"),
        message=match.group("message").strip(),
        raw=line.strip(),
    )


def load_log_file(path: str) -> List[LogEntry]:
    entries: List[LogEntry] = []
    try:
        with open(path, encoding="utf-8") as file:
            for line in file:
                entry = parse_log_line(line)
                if entry:
                    entries.append(entry)
    except FileNotFoundError:
        messagebox.showerror("Файл не найден", f"Файл не найден: {path}")
    except Exception as error:
        messagebox.showerror("Ошибка загрузки", f"Не удалось прочитать файл: {error}")
    return entries


def summarize_log_entries(entries: List[LogEntry]) -> Dict[str, Any]:
    levels: Dict[str, int] = {}
    codes: Dict[str, int] = {}
    for entry in entries:
        levels[entry.level] = levels.get(entry.level, 0) + 1
        codes[entry.code] = codes.get(entry.code, 0) + 1
    sorted_entries = quick_sort(entries, key=lambda item: item.timestamp)
    return {
        "total": len(entries),
        "levels": levels,
        "codes": codes,
        "first_timestamp": sorted_entries[0].timestamp if sorted_entries else None,
        "last_timestamp": sorted_entries[-1].timestamp if sorted_entries else None,
    }


def format_log_summary(summary: Dict[str, Any]) -> str:
    lines = ["=== Сводка логов ==="]
    lines.append(f"Всего записей: {summary['total']}")
    if summary["first_timestamp"] and summary["last_timestamp"]:
        lines.append(f"Период: {summary['first_timestamp']} - {summary['last_timestamp']}")
    lines.append("Уровни:")
    for level, count in sorted(summary["levels"].items(), key=lambda item: (-item[1], item[0])):
        lines.append(f"  {level}: {count}")
    lines.append("Коды ошибок:")
    for code, count in sorted(summary["codes"].items(), key=lambda item: (-item[1], item[0])):
        lines.append(f"  {code}: {count}")
    lines.append("=======================")
    return "\n".join(lines)


def filter_entries_by_date(entries: List[LogEntry], start: Optional[datetime], end: Optional[datetime]) -> List[LogEntry]:
    if not start and not end:
        return entries
    filtered: List[LogEntry] = []
    for entry in entries:
        if start and entry.timestamp < start:
            continue
        if end and entry.timestamp > end:
            continue
        filtered.append(entry)
    return filtered


def fetch_exchange_rates(base_currency: str) -> Optional[Dict[str, float]]:
    try:
        url = API_URL_TEMPLATE.format(base=base_currency)
        with urllib.request.urlopen(url, timeout=10) as response:
            body = response.read().decode("utf-8")
            data = json.loads(body)
            if data.get("success", True) is False:
                return None
            return {k.upper(): float(v) for k, v in data.get("rates", {}).items()}
    except (urllib.error.URLError, json.JSONDecodeError, Exception):
        return None


class Application(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("LogPro GUI")
        self.geometry("960x720")
        self.configure(bg="#1c2331")
        self.resizable(False, False)
        self.log_path = ""
        self._header_colors = ["#8fb3ff", "#7fd6ff", "#78d893", "#ffb46b"]
        self._header_color_index = 0
        self._create_styles()
        self._create_background()
        self._create_header()
        self._create_card()
        self._animate_header()

    def _create_styles(self):
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("Root.TFrame", background="#1c2331")
        style.configure("Card.TFrame", background="#ffffff", relief="flat")
        style.configure("Header.TLabel", background="#1c2331", foreground="#ffffff", font=("Segoe UI", 18, "bold"))
        style.configure("SubHeader.TLabel", background="#1c2331", foreground="#d1e4ff", font=("Segoe UI", 10))
        style.configure("CardTitle.TLabel", background="#ffffff", foreground="#253149", font=("Segoe UI", 13, "bold"))
        style.configure("CardText.TLabel", background="#ffffff", foreground="#4f5f7a", font=("Segoe UI", 10))
        style.configure("Big.TButton", font=("Segoe UI", 11, "bold"), foreground="#ffffff", background="#4c6bff", padding=10)
        style.map("Big.TButton", background=[("!disabled", "#4c6bff"), ("active", "#5f7dff")])
        style.configure("Outline.TButton", font=("Segoe UI", 11, "bold"), foreground="#4c6bff", background="#ffffff")
        style.map("Outline.TButton", background=[("!disabled", "#ffffff"), ("active", "#eef2ff")])

    def _create_background(self):
        self.canvas = tk.Canvas(self, highlightthickness=0, bg="#1c2331")
        self.canvas.place(relwidth=1, relheight=1)
        self.canvas.create_rectangle(0, 0, 960, 720, fill="#1c2331", outline="")
        self.canvas.create_oval(-220, -140, 420, 320, fill="#3755aa", outline="", stipple="gray25")
        self.canvas.create_oval(540, -180, 1080, 260, fill="#2d74d5", outline="", stipple="gray12")
        self.canvas.create_oval(180, 420, 820, 940, fill="#172b44", outline="", stipple="gray25")

    def _create_header(self):
        title = ttk.Label(self, text="LogPro - анализ логов и конвертер валют", style="Header.TLabel")
        title.place(relx=0.5, y=35, anchor="center")
        self.header_label = title

    def _create_card(self):
        card = ttk.Frame(self, style="Card.TFrame")
        card.place(relx=0.5, rely=0.55, anchor="center", width=900, height=590)
        
        left = ttk.Frame(card, style="Card.TFrame")
        left.place(relx=0.02, rely=0.02, relwidth=0.48, relheight=0.96)
        right = ttk.Frame(card, style="Card.TFrame")
        right.place(relx=0.50, rely=0.02, relwidth=0.48, relheight=0.96)
        
        ttk.Label(left, text="Анализ логов", style="CardTitle.TLabel").pack(anchor="w", padx=10, pady=10)
        self.log_path_var = tk.StringVar()
        ttk.Entry(left, textvariable=self.log_path_var).pack(fill="x", padx=10, pady=5)
        ttk.Button(left, text="Открыть лог", command=self._browse_log).pack(fill="x", padx=10, pady=5)
        ttk.Button(left, text="Анализировать", command=self._analyze).pack(fill="x", padx=10, pady=5)
        
        ttk.Label(left, text="Конвертер валют", style="CardTitle.TLabel").pack(anchor="w", padx=10, pady=(20, 10))
        self.base_var = tk.StringVar(value="USD")
        self.target_var = tk.StringVar(value="EUR")
        self.amount_var = tk.StringVar(value="100")
        ttk.Entry(left, textvariable=self.base_var, width=8).pack(side="left", padx=5)
        ttk.Entry(left, textvariable=self.target_var, width=8).pack(side="left", padx=5)
        ttk.Entry(left, textvariable=self.amount_var, width=10).pack(side="left", padx=5)
        ttk.Button(left, text="Конвертировать", command=self._convert).pack(fill="x", padx=10, pady=5)
        
        ttk.Label(right, text="Результаты", style="CardTitle.TLabel").pack(anchor="w", padx=10, pady=10)
        self.output = tk.Text(right, bg="#eef2ff", fg="#253149", font=("Consolas", 9))
        self.output.pack(fill="both", expand=True, padx=10, pady=10)
        ttk.Button(right, text="Очистить", command=lambda: self.output.delete("1.0", tk.END)).pack(padx=10, pady=5)

    def _browse_log(self):
        path = filedialog.askopenfilename(filetypes=[("Text", "*.txt"), ("Logs", "*.log"), ("All", "*.*")])
        if path:
            self.log_path_var.set(path)

    def _analyze(self):
        path = self.log_path_var.get()
        if not path:
            messagebox.showwarning("Предупреждение", "Выберите файл логов")
            return
        entries = load_log_file(path)
        if entries:
            summary = summarize_log_entries(entries)
            self.output.delete("1.0", tk.END)
            self.output.insert("1.0", format_log_summary(summary))
        else:
            messagebox.showerror("Ошибка", "Не удалось прочитать файл")

    def _convert(self):
        base = self.base_var.get().upper()
        target = self.target_var.get().upper()
        try:
            amount = float(self.amount_var.get())
        except ValueError:
            messagebox.showerror("Ошибка", "Неверная сумма")
            return
        
        rates = fetch_exchange_rates(base)
        if not rates:
            messagebox.showerror("Ошибка", f"Не удалось получить курсы для {base}")
            return
        if target not in rates:
            messagebox.showerror("Ошибка", f"Валюта {target} не найдена")
            return
        
        result = amount * rates[target]
        text = f"{amount:.2f} {base} = {result:.2f} {target}\nКурс: {rates[target]:.6f}"
        self.output.delete("1.0", tk.END)
        self.output.insert("1.0", text)

    def _animate_header(self):
        if not self.winfo_exists():
            return
        color = self._header_colors[self._header_color_index % len(self._header_colors)]
        self.header_label.configure(foreground=color)
        self._header_color_index += 1
        self.after(500, self._animate_header)


if __name__ == "__main__":
    app = Application()
    app.mainloop()
