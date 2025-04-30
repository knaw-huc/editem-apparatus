from dataclasses import dataclass


@dataclass
class EditemApparatusConfig:
    project_name: str
    data_path: str
    export_path: str
    static_file_server_base_url: str
    show_progress: bool = False,
    log_file_path: str = None
