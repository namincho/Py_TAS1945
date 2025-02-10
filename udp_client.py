# udp_client.py
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

            # 응답 대기 (최대 5초)
            self._socket.settimeout(5.0)
            response, _ = self._socket.recvfrom(1024)  # 최대 1024 바이트 수신
            print(f"Response received: {response}")

            # 응답 파싱
            self.tas1945_resp_parser(response)

        except socket.timeout:
            print("No response from FPGA within timeout period.")
        except Exception as e:
            print(f"Error during send/receive: {e}")

    def tas1945_resp_parser(self, response):
        try:
            if response.startswith(b'TP'):
                # 헤더 이후: 요청 코드, 응답 크기, 상태 코드 추출
                req_code = struct.unpack('<H', response[2:4])[0]
                req_code = (req_code ^ 0x0100)  # XOR 연산
                resp_size = struct.unpack('<I', response[4:8])[0]
                status_code = struct.unpack('<H', response[8:10])[0]

                # CRC16 검증
                received_crc = struct.unpack('<H', response[resp_size - 2:resp_size])[0]
                calculated_crc = calculate_crc16(response[:resp_size - 2])
                if received_crc != calculated_crc:
                    print("CRC Error: Invalid response")
                    return

                # 요청 코드별 처리
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
                        reg_addr = response[10]
                        reg_data = response[11]
                        print(f"ECHO: 레지스터 주소 {reg_addr}, 데이터 {reg_data} [0x{reg_data:02X}]")
                    else:
                        print("Response Size Error: 예상 크기와 불일치")
                else:
                    print(f"Unhandled REQ code: {req_code}")
            else:
                print("Invalid response format: Missing 'TP' header")
        except Exception as e:
            print(f"Error parsing response: {e}")
