import sys
from config import Config
from hyperlyse import MainWindow
from PyQt6.QtWidgets import QApplication



# config
__version__ = "1.3"
config = Config(__version__, 'config.json')

# main
if __name__ == "__main__":
    if len(sys.argv) > 1:
        startup_file = sys.argv[1]
    else:
        startup_file = None
    app = QApplication([])
    win = MainWindow(config, startup_file)
    sys.exit(app.exec())
