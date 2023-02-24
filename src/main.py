import sys
import hyperlyse as hyper
from PyQt6.QtWidgets import QApplication



# config
__version__ = "1.3"
config = hyper.Config(__version__, 'config.json')

# main
if __name__ == "__main__":
    if len(sys.argv) > 1:
        startup_file = sys.argv[1]
    else:
        startup_file = None
    print(f'--- hyperlyse version {__version__} ---')
    app = QApplication([])
    win = hyper.MainWindow(config, startup_file)
    sys.exit(app.exec())
