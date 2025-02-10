# main.py
import sys
from PyQt5.QtWidgets import QApplication
from thermal_camera_app import ThermalCameraApp

def main():
    app = QApplication(sys.argv)
    window = ThermalCameraApp()
    window.show()
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()
