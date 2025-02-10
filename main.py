import sys
from PyQt5.QtWidgets import QApplication, QMainWindow, QLabel, QPushButton, QVBoxLayout, QWidget
from PyQt5.QtWidgets import QMainWindow, QPushButton, QLabel, QVBoxLayout, QHBoxLayout, QWidget
from PyQt5.QtCore import Qt
import socket
import struct

def calculate_crc16(data):
    poly = 0xA001
    crc = 0xFFFF
    for byte in data:
        crc ^= byte
        for _ in range(8):
            if crc & 0x0001:
                crc = (crc >> 1) ^ poly
            else:
                crc >>= 1
    return crc & 0xFFFF

class UDPClient:
    def __init__(self):
        self._socket = None

    def setup(self, address, port):
        try:
            # UDP 소켓 생성 및 설정
            self._socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self._socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.address = address
            self.port = port
            print(f"UDP socket setup complete for {address}:{port}")
        except Exception as ex:
            print(f"Error setting up UDP client: {ex}")

    def send_and_receive(self, data):
        try:
            # 데이터 전송
            self._socket.sendto(data, (self.address, self.port))
            print(f"Data sent to {self.address}:{self.port}")

            # 응답 대기 (최대 5초 대기)
            self._socket.settimeout(5.0)
            response, _ = self._socket.recvfrom(1024)  # 최대 1024 바이트 수신
            print(f"Response received: {response}")

            # 데이터 파싱
            self.tas1945_resp_parser(response)

        except socket.timeout:
            print("No response from FPGA within timeout period.")
        except Exception as e:
            print(f"Error during send/receive: {e}")

    def tas1945_resp_parser(self, response):
        try:
            if response.startswith(b'TP'):
                # 헤더가 맞는 경우 요청 코드, 응답 크기, 상태 코드 추출
                req_code = struct.unpack('<H', response[2:4])[0]
                req_code = (req_code ^ 0x0100)  # XOR 연산 적용
                resp_size = struct.unpack('<I', response[4:8])[0]
                status_code = struct.unpack('<H', response[8:10])[0]

                # CRC16 검증
                received_crc = struct.unpack('<H', response[resp_size - 2:resp_size])[0]
                calculated_crc = calculate_crc16(response[:resp_size - 2])

                if received_crc != calculated_crc:
                    print("CRC Error: Invalid response")
                    return

                # 각 요청 코드에 대한 상태 확인 및 로그 출력
                if req_code == 0x0003:  # SET_SPI_READ
                    if status_code == 0x00:
                        print("Set SPI Read Success!")
                    else:
                        print(f"Set SPI Read Error: Status {status_code}")

                elif req_code == 0x0004:  # SET_SPI_CLOCK
                    if status_code == 0x00:
                        print("Set SPI Clock Success!")
                    else:
                        print(f"Set SPI Clock Error: Status {status_code}")

                elif req_code == 0x0005:  # SET_AVR_COUNT
                    if status_code == 0x00:
                        print("Set Average Count Success!")
                    else:
                        print(f"Set Average Count Error: Status {status_code}")

                elif req_code == 0x2001:  # REG_WR (레지스터 쓰기)
                    if status_code != 0x00:
                        print(f"REG_WR Error: 상태 코드 {status_code}")

                    if resp_size == 14:
                        reg_addr = response[10]  # 레지스터 주소
                        reg_data = response[11]  # 레지스터 데이터
                        print(f"ECHO: 레지스터 주소 {reg_addr}, 데이터 {reg_data} [0x{reg_data:02X}]")
                    else:
                        print("Response Size Error: 예상 크기와 불일치")

                else:
                    print(f"Unhandled REQ code: {req_code}")

            else:
                print("Invalid response format: Missing 'TP' header")

        except Exception as e:
            print(f"Error parsing response: {e}")

class ThermalCameraApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Thermal Camera GUI")
        self.setGeometry(100, 100, 900, 700)

        # QLabel로 연결 상태 표시
        self.status_label = QLabel("Status: Disconnected", self)
        self.status_label.setStyleSheet("font-size: 16px; color: red;")
        self.status_label.setAlignment(Qt.AlignCenter)

        # Connect 버튼 추가
        self.connect_button = QPushButton("Connect to FPGA", self)
        self.connect_button.setStyleSheet("font-size: 16px; padding: 10px;")
        self.connect_button.clicked.connect(self.connect_to_fpga)

        # Register 버튼 생성
        self.register_button = QPushButton("Register Settings", self)
        self.register_button.setStyleSheet("font-size: 16px; padding: 10px;")
        self.register_button.clicked.connect(self.register_settings)

        # 수평 레이아웃으로 버튼 배치
        button_layout = QHBoxLayout()
        button_layout.addWidget(self.connect_button)
        button_layout.addWidget(self.register_button)

        # 버튼 크기 조정: 창의 1/3 크기
        self.connect_button.setMinimumWidth(self.width() // 3)
        self.register_button.setMinimumWidth(self.width() // 3)

        # 메인 레이아웃 설정
        layout = QVBoxLayout()
        layout.addLayout(button_layout)  # 버튼 레이아웃 추가
        layout.addWidget(self.status_label)

        # 위젯 설정
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

            # Tas1945_SetRead와 이후 작업들
            self.send_command_with_response(0x0003, [1, 0])  # Tas1945_SetRead
            self.send_command_with_response(0x0004, [100])   # Tas1945_SetClock
            self.send_command_with_response(0x0005, [4])     # Tas1945_SetAverageCount

            self.status_label.setText(f"Status: Connected and Configured")
            self.status_label.setStyleSheet("font-size: 16px; color: green;")
        except Exception as e:
            self.status_label.setText("Status: Connection Failed")
            self.status_label.setStyleSheet("font-size: 16px; color: red;")
            print(f"Connection failed: {e}")

    def send_command_with_response(self, req_code, data):
        # 요청 데이터 생성 및 전송
        send_data = bytearray(b'TP')
        send_data.append(req_code & 0xFF)
        send_data.append((req_code >> 8) & 0xFF)

        # 데이터 크기 설정 (헤더 포함)
        send_data.extend([0, 0, 0, 0])

        # 실제 데이터 추가
        send_data.extend(data)

        # 데이터 크기 설정 (헤더 포함 전체 크기)
        total_size = len(send_data) + 2  # CRC 크기 포함
        send_data[4] = total_size & 0xFF
        send_data[5] = (total_size >> 8) & 0xFF
        send_data[6] = (total_size >> 16) & 0xFF
        send_data[7] = (total_size >> 24) & 0xFF

        # CRC16 계산 및 추가
        crc16 = calculate_crc16(send_data)
        send_data.append(crc16 & 0xFF)
        send_data.append((crc16 >> 8) & 0xFF)

        # UDP 데이터 송신 후 응답 대기
        self.udp_client.send_and_receive(send_data)

    def register_settings(self):
        print("Starting Register Initialization...")
        registers = self.tas1945_register_init()

        # 255번 레지스터 초기화 과정
        self.send_register_command(255, 0x10)
        self.send_register_command(255, 0x00)

        # 모든 레지스터에 대한 쓰기 진행
        for addr in range(255):
            # 스킵할 레지스터 범위 처리
            if addr in self.get_skip_registers():
                continue

            # 212번지 특별 처리
            if addr == 212:
                self.send_register_command(addr, registers[addr])
                self.send_register_command(addr, 0xA0)
                self.send_register_command(addr, 0x10)
            else:
                self.send_register_command(addr, registers[addr])

        print("Register Initialization Completed.")

    def tas1945_register_init(self):
        registers = [0] * 256  # 전체 레지스터 초기화

        # 정확히 C#에서 제공한 레지스터 값 반영
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

        # Skip하는 레지스터는 0x00으로 처리하며, 나머지는 제공된 값으로 설정
        skip_registers = self.get_skip_registers()

        # 레지스터 값 할당
        for i in range(len(registers)):
            if i not in skip_registers:
                registers[i] = values[i] if i < len(values) else 0x00

        return registers

    def get_skip_registers(self):
        return set([44, 45, 46, 47, *range(96, 112), 120, 124, 125,
                    126, 142, 143, 145, 146, 147, 148, 149, 150, 151, 152, 153, 159,
                    *range(160, 176), *range(183, 190), *range(192, 208), 222, 223,
                    *range(224, 240), *range(241, 255)])

    def send_register_command(self, address, data):
        # 패킷 생성
        packet = bytearray(12)  # 총 12바이트 크기의 패킷

        # [0]~[1]: 헤더 "TP"
        packet[0:2] = b'TP'

        # [2]~[3]: REQ 코드 (0x2001 -> Register Write)
        req_code = 0x2001
        packet[2] = req_code & 0x00FF  # 하위 바이트
        packet[3] = (req_code >> 8) & 0x00FF  # 상위 바이트

        # [4]~[7]: 데이터 크기 (12바이트로 고정)
        packet[4] = 12  # 패킷 전체 크기(12바이트)
        packet[5] = 0  # 상위 바이트 (0으로 설정)
        packet[6] = 0
        packet[7] = 0

        # [8]: 레지스터 주소
        packet[8] = address

        # [9]: 레지스터에 쓸 데이터
        packet[9] = data

        # [10]~[11]: CRC16 계산 (상위 비트가 뒤로 가도록 설정)
        crc16 = calculate_crc16(packet[:10])  # [0]~[9]까지의 데이터를 기반으로 CRC 계산
        packet[10] = crc16 & 0x00FF  # 하위 바이트
        packet[11] = (crc16 >> 8) & 0x00FF  # 상위 바이트

        # 패킷 전송 및 응답 대기
        self.udp_client.send_and_receive(packet)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = ThermalCameraApp()
    window.show()
    sys.exit(app.exec_())
