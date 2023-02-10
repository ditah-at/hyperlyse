import json
class Config:
    def __init__(self,
                 version,
                 config_json):
        """
        Reads config from .json file
        :param version: version string
        :param config_json: .json file containing config data
        """
        self.version = version
        with open(config_json, 'r') as f:
            cfg = json.load(f)
        self.default_db_file = cfg['DEFAULT_DB_FILE']
        self.scroll_speed = cfg['SCROLL_SPEED']
        self.cross_size = cfg['CROSS_SIZE']
        self.marker_colors = cfg['MARKER_COLORS']
        self.marker_alpha = cfg['MARKER_ALPHA']
        self.initial_image_width_ratio = cfg['INITIAL_IMAGE_WIDTH_RATIO']


    def infotext(self):
        return "\n".join(["Hyperlyse",
                          f"Version: {self.version}",
                          "Author: Simon Brenner",
                          "Institution: TU Wien, Computer Vision Lab",
                          "License: CC-BY-NC-SA"])