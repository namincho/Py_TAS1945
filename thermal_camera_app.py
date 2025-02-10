# thermal_camera_app.py
from PyQt5.QtWidgets import QMainWindow, QLabel, QPushButton, QVBoxLayout, QWidget, QHBoxLayout
from PyQt5.QtCore import Qt
from udp_client import UDPClient, calculate_crc16

class ThermalCameraApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Thermal Camera GUI")
        self.setGeometry(100, 100, 900, 700)

        # 상태 표시 QLabel
        self.status_label = QLabel("Status: Disconnected", self)
        self.status_label.setStyleSheet("font-size: 16px; color: red;")
        self.status_label.setAlignment(Qt.AlignCenter)

        # Connect 버튼
        self.connect_button = QPushButton("Connect to FPGA", self)
        self.connect_button.setStyleSheet("font-size: 16px; padding: 10px;")
        self.connect_button.clicked.connect(self.connect_to_fpga)

        # Register 버튼
        self.register_button = QPushButton("Register Settings", self)
        self.register_button.setStyleSheet("font-size: 16px; padding: 10px;")
        self.register_button.clicked.connect(self.register_settings)

        # 버튼 레이아웃 (수평)
        button_layout = QHBoxLayout()
        button_layout.addWidget(self.connect_button)
        button_layout.addWidget(self.register_button)

        # 버튼 크기 조정 (창의 1/3 크기)
        self.connect_button.setMinimumWidth(self.width() // 3)
        self.register_button.setMinimumWidth(self.width() // 3)

        # 메인 레이아웃 (수직)
        layout = QVBoxLayout()
        layout.addLayout(button_layout)
        layout.addWidget(self.status_label)

        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)

        # UDP Client 객체 생성
        self.udp_client = UDPClient()

    def connect_to_fpga(self):
        fpga_ip = "192.168.1.10"
        fpga_port = 10000
        try:
            # UDP 소켓 설정 및 연결
            self.udp_client.setup(fpga_ip, fpga_port)

            # FPGA에 명령 전송 (예: Tas1945_SetRead, SetClock, SetAverageCount)
            self.send_command_with_response(0x0003, [1, 0])
            self.send_command_with_response(0x0004, [100])
            self.send_command_with_response(0x0005, [4])

            self.status_label.setText("Status: Connected and Configured")
            self.status_label.setStyleSheet("font-size: 16px; color: green;")
        except Exception as e:
            self.status_label.setText("Status: Connection Failed")
            self.status_label.setStyleSheet("font-size: 16px; color: red;")
            print(f"Connection failed: {e}")

    def send_command_with_response(self, req_code, data):
        # 패킷 생성
        send_data = bytearray(b'TP')
        send_data.append(req_code & 0xFF)
        send_data.append((req_code >> 8) & 0xFF)

        # 데이터 크기 자리 (4바이트) 확보
        send_data.extend([0, 0, 0, 0])

        # 실제 데이터 추가
        send_data.extend(data)

        # 전체 패킷 크기 계산 (헤더 + 데이터 + CRC 2바이트)
        total_size = len(send_data) + 2
        send_data[4] = total_size & 0xFF
        send_data[5] = (total_size >> 8) & 0xFF
        send_data[6] = (total_size >> 16) & 0xFF
        send_data[7] = (total_size >> 24) & 0xFF

        # CRC16 계산 후 추가
        crc16 = calculate_crc16(send_data)
        send_data.append(crc16 & 0xFF)
        send_data.append((crc16 >> 8) & 0xFF)

        # 명령 전송
        self.udp_client.send_and_receive(send_data)

    def register_settings(self):
        print("Starting Register Initialization...")
        registers = self.tas1945_register_init()

        # 255번 레지스터 초기화
        self.send_register_command(255, 0x10)
        self.send_register_command(255, 0x00)

        # 모든 레지스터에 대해 처리
        for addr in range(255):
            if addr in self.get_skip_registers():
                continue
            if addr == 212:
                self.send_register_command(addr, registers[addr])
                self.send_register_command(addr, 0xA0)
                self.send_register_command(addr, 0x10)
            else:
                self.send_register_command(addr, registers[addr])

        print("Register Initialization Completed.")

    def tas1945_register_init(self):
        registers = [0] * 256  # 256개 레지스터 초기화
        values = [
            0x01, 0x00, 0xA6, 0x01, 0x00, 0x01, 0x02, 0x01, 0x01, 0x00, 0x1A, 0x00,
            0x01, 0x00, 0x0E, 0x00, 0x01, 0x00, 0x0E, 0x00, 0x1A, 0x00, 0x01, 0x00,
            0x03, 0x01, 0x05, 0x01, 0x0C, 0x01, 0x06, 0x01, 0x01, 0x00, 0x1C, 0x00,
            0x01, 0x00, 0xEE, 0x0F, 0x07, 0x00, 0x09, 0x00, 0x00, 0x00, 0x00, 0x00,
            0x50, 0x00, 0x6A, 0x03, 0x54, 0x00, 0x66, 0x03, 0x01, 0x00, 0x1C, 0x03,
            0x2E, 0x06, 0x31, 0x06, 0x65, 0x00, 0x30, 0x00, 0x32, 0x00, 0x65, 0x00,
            0x5F, 0x00, 0x3D, 0x00, 0x2C, 0x00, 0x09, 0x00, 0x01, 0x00, 0x31, 0x00,
            0x32, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x62, 0x00, 0x64, 0x00,
            0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
            0x1E, 0x1E, 0x1E, 0x1E, 0x1E, 0x1E, 0x1E, 0x1E, 0x00, 0x25, 0x09, 0x1F,
            0x00, 0x00, 0x00, 0x00, 0xAA, 0x00, 0xA8, 0x00, 0x2A, 0x00, 0xAA, 0x00,
            0xAA, 0x00, 0xAA, 0x00, 0xAA, 0x00, 0x00, 0x00, 0x2F, 0x00, 0x00, 0x00,
            0xC0, 0x00, 0x00, 0x00, 0x01, 0x00, 0x00, 0x48, 0x00, 0x00, 0x00, 0x00,
            0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x53, 0x01,
            0x81, 0x14, 0x1D, 0x1F, 0x1F, 0x1F, 0x1F, 0x07, 0x1D, 0x1B, 0x00, 0x00,
            0x00, 0x00, 0x80, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
            0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00
        ]
        skip_registers = self.get_skip_registers()
        for i in range(len(registers)):
            if i not in skip_registers:
                registers[i] = values[i] if i < len(values) else 0x00
        return registers

    def get_skip_registers(self):
        return set([
            44, 45, 46, 47, *range(96, 112), 120, 124, 125,
            126, 142, 143, 145, 146, 147, 148, 149, 150, 151, 152, 153, 159,
            *range(160, 176), *range(183, 190), *range(192, 208), 222, 223,
            *range(224, 240), *range(241, 255)
        ])

    def send_register_command(self, address, data):
        # 12바이트 크기의 패킷 생성
        packet = bytearray(12)
        # [0]-[1]: 헤더 "TP"
        packet[0:2] = b'TP'
        # [2]-[3]: REQ 코드 (0x2001: Register Write)
        req_code = 0x2001
        packet[2] = req_code & 0x00FF
        packet[3] = (req_code >> 8) & 0x00FF
        # [4]-[7]: 데이터 크기 (12바이트 고정)
        packet[4] = 12
        packet[5] = 0
        packet[6] = 0
        packet[7] = 0
        # [8]: 레지스터 주소, [9]: 데이터 값
        packet[8] = address
        packet[9] = data
        # [10]-[11]: CRC16 계산 후 추가
        crc16 = calculate_crc16(packet[:10])
        packet[10] = crc16 & 0x00FF
        packet[11] = (crc16 >> 8) & 0x00FF
        self.udp_client.send_and_receive(packet)
