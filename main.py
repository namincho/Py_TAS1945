import sys
from PyQt5.QtWidgets import QApplication, QMainWindow, QLabel, QPushButton, QVBoxLayout, QWidget
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

        # Connect 버튼 추가
        self.connect_button = QPushButton("Connect to FPGA", self)
        self.connect_button.setStyleSheet("font-size: 16px; padding: 10px;")
        self.connect_button.clicked.connect(self.connect_to_fpga)

        # 레이아웃 설정
        layout = QVBoxLayout()
        layout.addWidget(self.connect_button)
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

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = ThermalCameraApp()
    window.show()
    sys.exit(app.exec_())
