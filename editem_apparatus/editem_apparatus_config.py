from dataclasses import dataclass


@dataclass
class EditemApparatusConfig:
    project_name: str
    data_path: str
    export_path: str
    show_progress: bool = False,
    log_file_path: str = None
