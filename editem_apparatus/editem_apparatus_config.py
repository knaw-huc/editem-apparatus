from dataclasses import dataclass
from typing import Optional

from typing_extensions import Callable


@dataclass
class EditemApparatusConfig:
    project_name: str
    data_path: str
    export_path: str
    show_progress: bool = False
    log_file_path: Optional[str] = None
    graphic_url_mapper: Optional[Callable[[str], str]] = None
    file_url_prefix: str = ""
    illustration_sizes_file: Optional[str] = None
