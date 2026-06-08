from dataclasses import dataclass
from typing import Optional


@dataclass
class EditemConfig:
    data_path: str
    export_path: str
    show_progress: bool = False
    log_file_path: Optional[str] = None
    file_url_prefix: str = ""
