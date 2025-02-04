import sys
from PyQt5.QtWidgets import QApplication, QMainWindow, QLabel, QPushButton, QVBoxLayout, QWidget
import socket


class ThermalCameraApp(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Thermal Camera GUI")
        self.setGeometry(100, 100, 900, 700)

        # QLabel로 연결 상태 표시
        self.status_label = QLabel("Status: Disconnected", self)
        self.status_label.setStyleSheet("font-size: 16px; color: red;")

        # Connect 버튼 추가
        self.connect_button = QPushButton("Connect to FPGA", self)
        self.connect_button.clicked.connect(self.connect_to_fpga)

        # 레이아웃 설정
        layout = QVBoxLayout()
        layout.addWidget(self.status_label)
        layout.addWidget(self.connect_button)

        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)

    def connect_to_fpga(self):
        # FPGA의 IP와 포트 설정
        fpga_ip = "192.168.1.10"
        fpga_port = 5000

        try:
            # 소켓 생성 및 연결 시도
            self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.client_socket.connect((fpga_ip, fpga_port))

            # 연결 성공 메시지
            self.status_label.setText(f"Status: Connected to {fpga_ip}:{fpga_port}")
            self.status_label.setStyleSheet("font-size: 16px; color: green;")
            print("Successfully connected to FPGA.")

        except Exception as e:
            self.status_label.setText("Status: Connection Failed")
            self.status_label.setStyleSheet("font-size: 16px; color: red;")
            print(f"Connection failed: {e}")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = ThermalCameraApp()
    window.show()
    sys.exit(app.exec_())
