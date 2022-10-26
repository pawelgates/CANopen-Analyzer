from msilib.schema import Error
import sys, can, canopen
from PyQt5.QtCore import *
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *
from CanOpenDecoder import *
from time import sleep
from infi.devicemanager import DeviceManager
import threading
import serial.tools.list_ports as p
from serial import Serial

# QT Constants
FONT_BOLD = QFont()
FONT_BOLD.setBold(True)

COLOR_RED = QColor(255, 128, 128)
COLOR_GRAY = QColor(224, 224, 224)
COLOR_BLUE = QColor(153, 204, 255)
COLOR_GREEN = QColor(153, 255, 204)
COLOR_ORANGE = QColor(255, 204, 153)
COLOR_WHITE = QColor(255, 255, 255)
COLOR_YELLOW = QColor(255, 255, 204)

SDO_ENTRY_LIST = [
            "0x1000     Device type", 
            "0x1001     Error register", 
            "0x1005     SYNC COB ID",
            "0x1010     Store Parameters",
            "0x1017     Producer Heartbeat", 
            "0x1018     Identity",
            "0x1020     Verify Configuration",
            "0x1400     Receive PDO 1 Parameters",
            "0x1401     Receive PDO 2 Parameters",
            "0x1402     Receive PDO 3 Parameters",
            "0x1403     Receive PDO 4 Parameters",
            "0x1600     Receive PDO 1 Mapping",
            "0x1601     Receive PDO 2 Mapping",
            "0x1602     Receive PDO 3 Mapping",
            "0x1603     Receive PDO 4 Mapping",
            "0x1800     Transmit PDO 1 Parameters",
            "0x1801     Transmit PDO 2 Parameters",
            "0x1802     Transmit PDO 3 Parameters",
            "0x1803     Transmit PDO 4 Parameters",
            "0x1A00     Transmit PDO 1 Mapping",
            "0x1A01     Transmit PDO 2 Mapping",
            "0x1A02     Transmit PDO 3 Mapping",
            "0x1A03     Transmit PDO 4 Mapping",
            "0x1F50     Download program",
            "0x6000     Read Digital Inputs",
            "0x6200     Write Digital Outputs",
            "0x6401     Read Analog Inputs",
            "0x6411     Write Analog Outputs",
            "0x6423     Analog Input Interrupt Enable",
            "0x6426     Analog Input Value Difference"
            ]

class MsgSdo:
    cobid = None
    cmd = None
    entry = None
    subentry = None
    data = None

# Subclass QMainWindow to customize your application's main window
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        # Window
        self.setWindowTitle("CANopen Analyzer")
        self.main_window_size = self.size()
          
        # Buttons config
        layout_buttons = QHBoxLayout()

        self.selected_device = None
        self.selected_bitrate = 1000000

        self.bus = None
        self.notifier = None
        self.listeners = None
        
        device_layout = QVBoxLayout()
        device_layout.setContentsMargins(10,10,10,10)
        label_connect = QLabel("Select Device")
        label_connect.setStyleSheet('font: bold 12px; border: 0px solid rgb(124, 124, 124);')
        device_layout.addWidget(label_connect)

        self.device_combobox = QComboBox()
        self.device_combobox.setStyleSheet("font: bold 12px;")
        devices_list = self.pcan_devices()
        self.device_combobox.addItems(devices_list)
        self.device_combobox.activated.connect(self.device_combobox_activated)
        device_layout.addWidget(self.device_combobox)

        layout_buttons.addLayout(device_layout)

        bitrate_layout = QVBoxLayout()
        bitrate_layout.setContentsMargins(10,10,10,10)
        label_bitrate = QLabel("Select Bitrate")
        label_bitrate.setStyleSheet('font: bold 12px; border: 0px solid rgb(124, 124, 124);')
        bitrate_layout.addWidget(label_bitrate)

        self.bitrate_combobox = QComboBox()
        self.bitrate_combobox.setStyleSheet("font: bold 12px;")
        devices_list = ["Bitrate", "1Mbps", "500Kbps", "250Kbps", "125Kbps"]
        self.bitrate_combobox.addItems(devices_list)
        bitrate_layout.addWidget(self.bitrate_combobox)
        self.bitrate_combobox.activated.connect(self.bitrate_combobox_activated)
        
        layout_buttons.addLayout(bitrate_layout)

        self.btn_connect = QPushButton("CONNECT")
        self.btn_connect.setFixedSize(120, 60)
        self.btn_connect.pressed.connect(self.button_connect_pressed)

        layout_buttons.addWidget(self.btn_connect)
        
        self.btn_start = QPushButton("START")
        self.btn_start.setFixedSize(120, 60)
        self.btn_start.pressed.connect(self.start_scanner)
        layout_buttons.addWidget(self.btn_start)
        
        self.window_scanbus = BottomWindowScanBus()
        self.btn_start.setEnabled(False)
        
        self.btn_clear = QPushButton("CLEAR")
        self.btn_clear.setFixedSize(120, 60)
        self.btn_clear.pressed.connect(self.clear)
        layout_buttons.addWidget(self.btn_clear)
        self.btn_clear.setEnabled(False)

        self.window_nmt = BottomWindowNMT()
        self.window_sdo = BottomWindowSDO()
        self.window_pdo = BottomWindowPDO()
        self.spacer = QSpacerItem(20, 200, QSizePolicy.Minimum, QSizePolicy.Minimum)
        
        layout_buttons.setAlignment(Qt.AlignLeft)

        # Bottom window
        layout_main = QVBoxLayout()
        layout_main.addLayout(layout_buttons)

        layout_bottom = QHBoxLayout()
        layout_bottom.setAlignment(Qt.AlignTop)
        layout_bottom.addWidget(self.window_scanbus)
        
        layout_bottom_left = QVBoxLayout()
        layout_bottom_left.setContentsMargins(0,1,0,0)
        
        layout_bottom_left.addWidget(self.window_nmt)
        layout_bottom_left.addWidget(self.window_sdo)
        layout_bottom_left.addWidget(self.window_pdo)
        layout_bottom_left.addItem(self.spacer)
        
        layout_bottom.addLayout(layout_bottom_left)        

        layout_main.addLayout(layout_bottom)
        
        widget = QWidget()
        widget.setLayout(layout_main)
        self.setCentralWidget(widget)
    
    def start_scanner(self):
        if self.window_scanbus.read_enable == True:
            self.window_scanbus.read_enable = False
            self.btn_start.setText("START")
            self.notifier = can.Notifier(self.bus, self.listeners, 0.5)
            self.window_pdo.setEnabled(True)
        else:
            self.window_scanbus.read_enable = True
            self.btn_start.setText("STOP")
            self.window_pdo.setEnabled(False)
            self.notifier.stop()
            self.window_scanbus.send_to_thread()
            ## TODO: FIX Double Start press fault

    def clear(self):
        self.window_scanbus.tableWidget.clearContents()
        self.window_scanbus.tableWidget.setRowCount(0) 
        self.window_scanbus.msg_dict = {}

    def main_window_height(self):
        return self.size().height()

    def activate_pdo(self):
        pass

    def buttons_enable(self):
        self.btn_start.setEnabled(True)
        self.btn_clear.setEnabled(True)
        self.window_sdo.setEnabled(True)
        self.window_nmt.setEnabled(True)
        self.window_pdo.setEnabled(True)

    # SCAN PCAN Devices
    def pcan_devices(self):
        dm = DeviceManager()
        dm.root.rescan()
        dm_devices = dm.all_devices
        devices_list = ["Device"]
        i = 1
        for device in dm_devices:
            if "PCAN-USB" in str(device):
                devices_list.append(f"PCAN_USBBUS{i}")
                i = i + 1
        return devices_list

    def device_combobox_activated(self):
        self.selected_device = self.device_combobox.currentText()
        QApplication.processEvents()

    def bitrate_combobox_activated(self):
        match self.bitrate_combobox.currentText():
            case "1Mbps":
                self.selected_bitrate = 1000000
                QApplication.processEvents()
            case "500Kbps":
                self.selected_bitrate = 500000
                QApplication.processEvents()
            case "250Kbps":
                self.selected_bitrate = 250000
                QApplication.processEvents()
            case "125Kbps":
                self.selected_bitrate = 125000
                QApplication.processEvents()

    def button_connect_pressed(self):
        try:
            print(f"Device: {self.selected_device}")
            print(f"Bitrate: {self.selected_bitrate}")
            self.bus = can.interface.Bus(bustype='pcan', channel=self.selected_device, bitrate=self.selected_bitrate, can_filters=None)  # TODO: MAKE GLOBAL BUS VAR
            print("BUS is connected\n")
            network = canopen.Network()
            network.bus = self.bus
            self.buttons_enable()
            self.window_scanbus.bus = self.bus
            self.window_nmt.bus = self.bus
            self.window_sdo.bus = self.bus
            self.window_pdo.bus = self.bus
            self.window_sdo.network = network
            self.window_pdo.network = network
            self.listeners = network.listeners
            self.notifier = can.Notifier(self.bus, self.listeners, 0.5)
            # Detecting nodes
            network.scanner.search()
            sleep(0.05)
            node_list = []
            for node_id in network.scanner.nodes:
                node_list.append(str(node_id))
            node_list.sort()
            nmt_node_list = node_list.copy()
            nmt_node_list.insert(0, "All")
            self.window_pdo.device_list = node_list
            self.window_sdo.device_list = node_list
            self.window_nmt.device_list = nmt_node_list
            self.window_nmt.update_device_list()
            self.window_pdo.update_device_list()
            self.window_sdo.update_device_list()
            self.btn_connect.setHidden(True)
        except:
            print("BUS connection FAILED\n")
            ErrorMessage("BUS connection failed")


class WorkerScanBus(QObject):
    finished = pyqtSignal()
    gui_update = pyqtSignal(object, object)

    def __init__(self, scanbus):
        super(WorkerScanBus , self).__init__()
        self.scanbus = scanbus

    def run(self):
        self.scanbus.read_from_bus()
        self.finished.emit()


class BottomWindowScanBus(QMainWindow):
    def __init__(self):
        super().__init__()
        self.rows_num = 1
        self.setFixedSize(1300, 930)
        self.setEnabled(True)

        self.msg_dict = {}
        self.read_enable = False
        self.bus = None

        # Table Widget
        self.tableWidget = QTableWidget()
        self.tableWidget.setRowCount(1) 
        self.tableWidget.setColumnCount(5)
        names = ["Count", "Msg Type", "Device ID", "Raw Data", "Data"]
        self.tableWidget.setHorizontalHeaderLabels(names)
        self.tableWidget.verticalHeader().hide()
        self.tableWidget.setColumnWidth(0, 100)
        self.tableWidget.setColumnWidth(1, 100)
        self.tableWidget.setColumnWidth(2, 100)
        self.tableWidget.setColumnWidth(3, 300)
        self.tableWidget.setColumnWidth(4, 698)

        self.setCentralWidget(self.tableWidget)
    
    def send_to_thread(self):
        self.event1 = threading.Event()
        self.thread1 = QThread()
        self.bus_worker = WorkerScanBus(self)
        self.bus_worker.moveToThread(self.thread1)
        self.thread1.started.connect(self.bus_worker.run)
        self.bus_worker.finished.connect(self.thread1.quit)
        self.bus_worker.finished.connect(self.bus_worker.deleteLater)
        self.thread1.finished.connect(self.thread1.deleteLater)
        self.bus_worker.gui_update.connect(self.change_gui)
        self.thread1.start()

    def change_gui(self, sorted_keys, msg_dict):
        for i in range(len(sorted_keys)):
            # Count col
            count_item = QTableWidgetItem(str(msg_dict[sorted_keys[i]].count))
            count_item.setFont(FONT_BOLD)
            count_item.setTextAlignment(Qt.AlignCenter)
            self.tableWidget.setItem(i, 0, count_item)
            # Type col
            type_item = QTableWidgetItem(msg_dict[sorted_keys[i]].type)
            type_item.setFont(FONT_BOLD)
            type_item.setTextAlignment(Qt.AlignCenter)
            match msg_dict[sorted_keys[i]].type:
                case "NMT":
                    type_item.setBackground(COLOR_ORANGE)
                case "EMCY":
                    type_item.setBackground(COLOR_RED)
                case "T_PDO_1" | "T_PDO_2" | "T_PDO_3" | "T_PDO_4" | "R_PDO_1" | "R_PDO_2" | "R_PDO_3" | "R_PDO_4":
                    type_item.setBackground(COLOR_GREEN)
                case "T_SDO" | "R_SDO":
                    type_item.setBackground(COLOR_BLUE)
                case "HEARTBEAT":
                    type_item.setBackground(COLOR_GRAY)
                case "LSS MASTER" | "LSS SLAVE":
                    type_item.setBackground(COLOR_YELLOW)
                case _:
                    type_item.setBackground(COLOR_WHITE)   
            self.tableWidget.setItem(i, 1, type_item)
            # ID col
            id_item = QTableWidgetItem(str(msg_dict[sorted_keys[i]].id))
            id_item.setFont(FONT_BOLD)
            id_item.setTextAlignment(Qt.AlignCenter)
            self.tableWidget.setItem(i, 2, id_item)
            # RAW Data col
            rawdata_item = QTableWidgetItem(msg_dict[sorted_keys[i]].raw_data)
            rawdata_item.setFont(FONT_BOLD)
            rawdata_item.setTextAlignment(Qt.AlignCenter)
            self.tableWidget.setItem(i, 3, rawdata_item)
            # Data col
            data_item = QTableWidgetItem(msg_dict[sorted_keys[i]].data)
            data_item.setFont(FONT_BOLD)
            self.tableWidget.setItem(i, 4, data_item)

    def read_from_bus(self):
        self.msg_dict = {}
        while self.read_enable:
            msg = self.bus.recv()
            if self.read_enable == False:
                self.bus_worker.finished.emit()
                return "STOP was pressed"
            if msg != None:
                decoder = CanOpenDecoder()
                decoder.decode_cob_id(msg.arbitration_id)
                decoder.decode_data(msg.data)
                message_id = msg.arbitration_id
                message_data = decoder.return_data()
                if message_id in self.msg_dict:
                    self.msg_dict[message_id].data = message_data.data
                    self.msg_dict[message_id].raw_data = message_data.raw_data
                    self.msg_dict[message_id].count = self.msg_dict[message_id].count + 1
                else:
                    self.msg_dict[message_id] = message_data
                sorted_keys = sorted(list(self.msg_dict.keys()))
                self.tableWidget.setRowCount(len(sorted_keys))
                self.bus_worker.gui_update.emit(sorted_keys, self.msg_dict)
                print(f"{msg.arbitration_id:03x} {msg.data}")


class BottomWindowNMT(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setFixedSize(600, 155)
        self.setStyleSheet('border:1px solid rgb(124, 124, 124);')
        self.setEnabled(True)
        
        # INIT VALUES
        # self.baudrate = 230400
        self.baudrate = 115200
        self.device_list = []
        self.bus = None

        self.name = QLabel("Master Device Config")
        self.name.setStyleSheet('font: bold 14px; border: 1px solid rgb(124, 124, 124); padding: 5px;background-color: rgb(255, 153, 153);')
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0,0,0,0)
        main_layout.setAlignment(Qt.AlignTop)
        main_layout.addWidget(self.name)

        horisontal_layout = QHBoxLayout()
        horisontal_layout.setContentsMargins(10,5,10,5)

        # COM Port Layout
        com_layout = QHBoxLayout()
        com_layout.setContentsMargins(10,5,10,0)
        self.com_label = QLabel("Device COM Port:")
        self.com_label.setStyleSheet('border:0px; font: bold 12px;')
        com_layout.addWidget(self.com_label)
        self.com_combobox = QComboBox()
        self.com_combobox.setFixedWidth(100)
        self.com_ports_list = ["PORT"]
        ports = p.comports()
        for port in ports:
            self.com_ports_list.append(port.device)
        self.com_combobox.addItems(self.com_ports_list)
        self.com_combobox.activated.connect(self.com_combobox_activated)
        com_layout.addWidget(self.com_combobox)
        main_layout.addLayout(com_layout)

        # NMT Layout
        nmt_layout = QHBoxLayout()
        nmt_layout.setEnabled(False)
        nmt_layout.setContentsMargins(10,5,10,0)
        self.nmt_label = QLabel("NMT:")
        self.nmt_label.setStyleSheet('border:0px; font: bold 12px;')
        nmt_layout.addWidget(self.nmt_label)
        self.device_id_combobox = QComboBox()
        self.device_id_combobox.setFixedWidth(118)
        self.device_id_combobox.addItems(self.device_list)
        nmt_layout.addWidget(self.device_id_combobox)
        self.cmd_combobox = QComboBox()
        self.cmd_combobox.setFixedWidth(150)
        cmd_list = ["Go to Reset Device", "Go to Reset Com.","Go to Pre-Operational", "Go to Operational", "Go to Stopped"]
        self.cmd_combobox.addItems(cmd_list)
        nmt_layout.addWidget(self.cmd_combobox)
        self.send_btn = QPushButton("SEND")
        self.send_btn.setStyleSheet("QPushButton {background-color: rgb(224, 224, 224);} QPushButton:hover {background-color: #CED4DA; border: 1px solid #49545a; }")
        self.send_btn.setFixedSize(120, 18)
        self.send_btn.pressed.connect(self.nmt_send_command)
        nmt_layout.addWidget(self.send_btn)
        main_layout.addLayout(nmt_layout)

         # HEARTBEAT
        heartbeat_layout = QHBoxLayout()
        heartbeat_layout.setContentsMargins(10,5,10,0)
        self.heartbeat_label = QLabel("HEARTBEAT (ms):")
        self.heartbeat_label.setStyleSheet('border:0px; font: bold 12px;')
        heartbeat_layout.addWidget(self.heartbeat_label)
        self.heartbeat_combobox = QComboBox()
        self.heartbeat_combobox.setFixedWidth(118)
        self.heartbeat_combobox.addItems(self.device_list)
        heartbeat_layout.addWidget(self.heartbeat_combobox)        
        self.heartbeat_line = QLineEdit()
        self.heartbeat_line.setFixedWidth(150)
        heartbeat_layout.addWidget(self.heartbeat_line)
        self.heartbeat_button = QPushButton("START")
        self.heartbeat_button.setStyleSheet("QPushButton {background-color: rgb(224, 224, 224);} QPushButton:hover {background-color: #CED4DA; border: 1px solid #49545a; }")
        self.heartbeat_button.pressed.connect(self.heartbeat_button_pressed)
        self.heartbeat_button.setFixedSize(120, 18)
        heartbeat_layout.addWidget(self.heartbeat_button)
        main_layout.addLayout(heartbeat_layout)

        # SYNC
        sync_layout = QHBoxLayout()
        sync_layout.setContentsMargins(10,5,10,0)
        self.sync_label = QLabel("SYNC (ms):")
        self.sync_label.setStyleSheet('border:0px; font: bold 12px;')
        sync_layout.addWidget(self.sync_label)
        self.sync_line = QLineEdit()
        self.sync_line.setFixedWidth(150)
        sync_layout.addWidget(self.sync_line)
        self.sync_button = QPushButton("START")
        self.sync_button.setStyleSheet("QPushButton {background-color: rgb(224, 224, 224);} QPushButton:hover {background-color: #CED4DA; border: 1px solid #49545a; }")
        self.sync_button.pressed.connect(self.sync_button_pressed)
        self.sync_button.setFixedSize(120, 18)
        sync_layout.addWidget(self.sync_button)
        main_layout.addLayout(sync_layout)

        # Default ENABLE False
        self.device_id_combobox.setEnabled(False)
        self.cmd_combobox.setEnabled(False)
        self.send_btn.setEnabled(False)
        self.heartbeat_combobox.setEnabled(False)
        self.heartbeat_line.setEnabled(False)
        self.heartbeat_button.setEnabled(False)
        self.sync_line.setEnabled(False)
        self.sync_button.setEnabled(False)

        widget = QWidget()
        widget.setLayout(main_layout)
        self.setCentralWidget(widget)

    def update_device_list(self):
        self.device_id_combobox.clear()
        self.heartbeat_combobox.clear()
        self.device_id_combobox.addItems(self.device_list)
        self.heartbeat_combobox.addItems(self.device_list)

    def com_combobox_activated(self):
        # CHECK COM PORT SELECTION
        selected_port = self.com_combobox.currentText()
        if selected_port != "PORT":
            port = Serial(f'{selected_port}', self.baudrate, timeout=0.3)
            #TODO: CREATE PROPER CMD
            command = ('cmd_hs' + '\r\n').encode()
            port.write(command)
            sleep(1)
            resp = port.read_all().decode()
            port.close()
            #TODO: CHECK PROPER RESP
            print(f'RESP: {resp}')
            if "OK" in resp:
                self.device_id_combobox.setEnabled(True)
                self.cmd_combobox.setEnabled(True)
                self.send_btn.setEnabled(True)
                self.heartbeat_combobox.setEnabled(True)
                self.heartbeat_line.setEnabled(True)
                self.heartbeat_button.setEnabled(True)
                self.sync_line.setEnabled(True)
                self.sync_button.setEnabled(True)
            else:
                print("No response from M0")

    def nmt_send_command(self):
        if self.device_id_combobox.currentText() == '':
            print("ERROR: Incorrect NMT input")
            ErrorMessage("Incorrect NMT input")
        else:
            # Device Number
            if self.device_id_combobox.currentText() == 'All':
                device_id = '00'
            else:
                device_id = f'{int(self.device_id_combobox.currentText()):02x}'
            # NMT command
            match self.cmd_combobox.currentText():
                case "Go to Reset Device":
                    nmt_cmd = '81'
                case "Go to Reset Com.":
                    nmt_cmd = '82'
                case "Go to Pre-Operational":
                    nmt_cmd = '80'
                case "Go to Operational":
                    nmt_cmd = '01'
                case _:
                    nmt_cmd = '02'
            # MSG
            msg = f'cmd_nmt_p{nmt_cmd}_p{device_id}'
            print(msg)
            # UART MSG
            port = Serial(f'{self.com_combobox.currentText()}', self.baudrate, timeout=0.3)
            command = (f'{msg}' + '\r\n').encode()
            port.write(command)
            sleep(1)
            resp = port.read_all().decode()
            print(resp)
            port.close()

    def heartbeat_button_pressed(self):
        if self.heartbeat_line.text() == '' or self.heartbeat_combobox.currentText() == '':
            print("ERROR: Incorrect HEARTBEAT input")
            ErrorMessage("Incorrect HEARTBEAT input")
        else:
            # Device Number
            if self.heartbeat_combobox.currentText() == 'All':
                device_id = '00'
            else:
                device_id = f'{int(self.heartbeat_combobox.currentText()):02x}'
            if self.heartbeat_line.text().isnumeric():
                period_time = f'{int(self.heartbeat_line.text()):04x}'
            else:
                print("ERROR: Incorrect HEARTBEAT input")
                period_time = '0000'
            # MSG
            msg = f'cmd_heartbeat_p{device_id}_p{period_time}'
            print(msg)
            # UART MSG
            port = Serial(f'{self.com_combobox.currentText()}', self.baudrate, timeout=0.3)
            command = (f'{msg}' + '\r\n').encode()
            port.write(command)
            sleep(1)
            resp = port.read_all().decode()
            print(resp)
            port.close()

    def sync_button_pressed(self):
        if self.sync_line.text() == '':
            print("ERROR: Incorrect SYNC input")
            ErrorMessage("Incorrect SYNC input")
        else:
            delay = 0
            # SYNC start
            if self.sync_button.text() == "START":
                if self.sync_line.text().isnumeric():
                    delay = int(self.sync_line.text())
                    
                    msg = f'cmd_sync_start_p{delay:04x}'
                    print(msg)
                    # UART MSG
                    port = Serial(f'{self.com_combobox.currentText()}', self.baudrate, timeout=0.3)
                    command = (f'{msg}' + '\r\n').encode()
                    port.write(command)
                    sleep(1)
                    resp = port.read_all().decode()
                    print(resp)
                    port.close()

                    self.sync_button.setText("STOP")
                    self.sync_button.setStyleSheet("background-color: rgb(255, 128, 128);")
            # SYNC stop 
            else:
                if self.sync_button.text() == "STOP":
                    
                    self.sync_line.setText('')
                    msg = f'cmd_sync_stop'
                    print(msg)
                    # UART MSG
                    port = Serial(f'{self.com_combobox.currentText()}', self.baudrate, timeout=0.3)
                    command = (f'{msg}' + '\r\n').encode()
                    port.write(command)
                    sleep(1)
                    resp = port.read_all().decode()
                    print(resp)
                    port.close()

                    self.sync_button.setText("START")
                    self.sync_button.setStyleSheet("background-color: rgb(224, 224, 224);")
        

class BottomWindowSDO(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setFixedSize(600, 235)
        self.setStyleSheet('border:1px solid rgb(124, 124, 124);')
        self.setEnabled(False)

        # CAN BUS
        self.bus = None
        self.network = None
        self.listener = None
        self.notifier = None
        self.selected_node = None

        # MSG VARS
        self.cobid = None
        self.cmd = None
        self.index1 = None
        self.index2 = None
        self.subindex = None
        self.data1 = None
        self.data2 = None
        self.data3 = None
        self.data4 = None

        self.name = QLabel("SDO Config")
        self.name.setStyleSheet('font: bold 14px; border: 1px solid rgb(124, 124, 124); padding: 5px;background-color: rgb(153, 204, 255);')
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0,0,0,0)
        main_layout.setAlignment(Qt.AlignTop)
        main_layout.addWidget(self.name)

        # Device ID line
        device_id_layout = QHBoxLayout()
        device_id_layout.setContentsMargins(10,5,10,0)
        self.device_id_label = QLabel("Device ID:".ljust(25))
        self.device_id_label.setStyleSheet('border:0px; font: bold 12px;')
        device_id_layout.addWidget(self.device_id_label)
        spacer = QSpacerItem(34, 0, QSizePolicy.Minimum, 0)
        device_id_layout.addItem(spacer)
        self.device_id_combobox = QComboBox()
        self.device_id_combobox.setFixedWidth(400)
        self.device_id_combobox.activated.connect(self.device_id_combobox_activated)
        self.device_list = []
        self.device_id_combobox.addItems(self.device_list)
        device_id_layout.addWidget(self.device_id_combobox)
        
        main_layout.addLayout(device_id_layout)

        # CMD line
        cmd_layout = QHBoxLayout()
        cmd_layout.setContentsMargins(10,5,10,0)
        self.cmd_label = QLabel("Command:".ljust(25))
        self.cmd_label.setStyleSheet('border:0px; font: bold 12px;')
        cmd_layout.addWidget(self.cmd_label)
        spacer = QSpacerItem(1, 0, QSizePolicy.Minimum, 0)
        cmd_layout.addItem(spacer)
        self.cmd_combobox = QComboBox()
        self.cmd_combobox.setFixedWidth(400)
        self.cmd_combobox.activated.connect(self.cmd_combobox_activated)
        cmd_list = [
            "READ",
            "WRITE"
        ]
        self.cmd_combobox.addItems(cmd_list)
        cmd_layout.addWidget(self.cmd_combobox)
        main_layout.addLayout(cmd_layout)

        # Entry Index line
        entry_layout = QHBoxLayout()
        entry_layout.setContentsMargins(10,5,10,0)
        self.entry_index_label = QLabel("Entry Index:".ljust(25))
        self.entry_index_label.setStyleSheet('border:0px; font: bold 12px;')
        entry_layout.addWidget(self.entry_index_label)
        spacer = QSpacerItem(6, 0, QSizePolicy.Minimum, 0)
        entry_layout.addItem(spacer)
        self.entry_combobox = QComboBox()
        self.entry_combobox.setFixedWidth(400)
        self.entry_list = SDO_ENTRY_LIST
        self.entry_combobox.addItems(self.entry_list)
        self.entry_combobox.activated.connect(self.entry_combobox_activated)
        entry_layout.addWidget(self.entry_combobox)
        main_layout.addLayout(entry_layout)

        # Entry Sub Index line
        entry_sub_layout = QHBoxLayout()
        entry_sub_layout.setContentsMargins(10,5,10,0)
        self.entry_sub_index_label = QLabel("Entry Sub Index:".ljust(23))
        self.entry_sub_index_label.setStyleSheet('border:0px; font: bold 12px;')
        entry_sub_layout.addWidget(self.entry_sub_index_label)

        self.entry_sub_index_combobox = QComboBox()
        self.entry_sub_index_combobox.setFixedWidth(400)
        subentries_list = []
        for i in range(128):
            subentries_list.append(str(i))
        self.entry_sub_index_combobox.addItems(subentries_list)
        entry_sub_layout.addWidget(self.entry_sub_index_combobox)
        main_layout.addLayout(entry_sub_layout)

        # Data line
        data_layout = QHBoxLayout()
        data_layout.setContentsMargins(10,5,10,0)
        self.data_label = QLabel("Data:".ljust(25))
        self.data_label.setStyleSheet('border:0px; font: bold 12px;')
        data_layout.addWidget(self.data_label)
        self.data_textbox = QLineEdit("00000000".rjust(8, "0"))
        self.data_textbox.setMaxLength(8)
        self.data_textbox.setFixedWidth(400)
        self.data_textbox.setEnabled(False)
        data_layout.addWidget(self.data_textbox)
        main_layout.addLayout(data_layout)

        # Send Button
        btn_layout = QHBoxLayout()
        btn_layout.setAlignment(Qt.AlignLeft)
        btn_layout.setContentsMargins(10,5,10,10)
        self.btn_sendmsg = QPushButton("SEND SDO")
        self.btn_sendmsg.setStyleSheet("QPushButton {background-color: rgb(224, 224, 224);} QPushButton:hover {background-color: #CED4DA; border: 1px solid #49545a; }")
        self.btn_sendmsg.setFixedSize(120, 40)
        self.btn_sendmsg.pressed.connect(self.btn_sendmsg_pressed)
        btn_layout.addWidget(self.btn_sendmsg)
        main_layout.addLayout(btn_layout)

        widget = QWidget()
        widget.setLayout(main_layout)
        self.setCentralWidget(widget)

    def update_device_list(self):
        self.device_id_combobox.clear()
        self.device_id_combobox.addItems(self.device_list)

    def device_id_combobox_activated(self):
        self.selected_node = int(self.device_id_combobox.currentText())

    def cmd_combobox_activated(self):
        if self.cmd_combobox.currentText() == "READ":
            self.data_textbox.setEnabled(False)
        if self.cmd_combobox.currentText() == "WRITE":
            self.data_textbox.setEnabled(True)


    def entry_combobox_activated(self):
        entry_hex = int(self.entry_combobox.currentText()[:6], 16)
        # Save Params
        if entry_hex == 0x1010: 
            self.entry_sub_index_combobox.setCurrentIndex(1)
            self.data_textbox.setText("65766173")
        # Heartbeat
        else:
            self.cmd_combobox.setCurrentIndex(0)
            self.entry_sub_index_combobox.setCurrentIndex(0)
            self.data_textbox.setText("00000000")


    def btn_sendmsg_pressed(self):
        self.device_id_combobox_activated()
        node = self.network.add_node(self.selected_node, 'PEAK.eds')
        index = int(self.entry_combobox.currentText()[2:6], 16)
        subindex = int(self.entry_sub_index_combobox.currentText())
        
        try:
            if self.cmd_combobox.currentText() == "READ":
                data = node.sdo.upload(index, subindex)
                sleep(0.05)
                print(data)
        except canopen.sdo.exceptions.SdoCommunicationError:
            print("ERROR: No SDO Response")
            WarningMessage("No SDO Response")

        try:
            if self.cmd_combobox.currentText() == "WRITE":
                if index == 0x1010:
                    data = int(self.data_textbox.text(), 16)
                    data_bytes = data.to_bytes(4, 'little')
                elif index == 0x1017:
                    data = int(self.data_textbox.text())
                    data_bytes = data.to_bytes(2, 'little')
                print(data_bytes)
                node.sdo.download(index, subindex, data_bytes)
                sleep(0.05)
        except canopen.sdo.exceptions.SdoCommunicationError:
            print("ERROR: No SDO Response")
            WarningMessage("No SDO Response")
            

class BottomWindowPDO(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setFixedSize(600, 345)
        self.setStyleSheet('border:1px solid rgb(124, 124, 124);')
        self.setEnabled(False)

        # CAN BUS
        self.bus = None
        self.network = None
        self.listener = None
        self.notifier = None

        self.data_list = []
        
        self.selected_node = None
        self.selected_entry = None

        self.name = QLabel("PDO Config")
        self.name.setStyleSheet('font: bold 14px; border: 1px solid rgb(124, 124, 124); padding: 5px;background-color: rgb(153, 255, 204);')
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0,0,0,0)
        main_layout.setAlignment(Qt.AlignTop)
        main_layout.addWidget(self.name)

        # Device ID line
        device_id_layout = QHBoxLayout()
        device_id_layout.setContentsMargins(10,5,10,0)
        self.device_id_label = QLabel("Device ID:".ljust(25))
        self.device_id_label.setStyleSheet('border:0px; font: bold 12px;')
        device_id_layout.addWidget(self.device_id_label)
        spacer = QSpacerItem(34, 0, QSizePolicy.Minimum, 0)
        device_id_layout.addItem(spacer)
        self.device_id_combobox = QComboBox()
        self.device_id_combobox.setFixedWidth(400)
        self.device_list = []
        self.device_id_combobox.addItems(self.device_list)
        self.device_id_combobox.activated.connect(self.device_id_combobox_activated)
        device_id_layout.addWidget(self.device_id_combobox)
        main_layout.addLayout(device_id_layout)

        # Entry Combobox line
        entry_layout = QHBoxLayout()
        entry_layout.setContentsMargins(10,5,10,5)
        self.entry_index_label = QLabel("Entry:".ljust(25))
        self.entry_index_label.setStyleSheet('border:0px; font: bold 12px;')
        entry_layout.addWidget(self.entry_index_label)
        spacer = QSpacerItem(21, 0, QSizePolicy.Minimum, 0)
        entry_layout.addItem(spacer)
        self.entry_combobox = QComboBox()
        self.entry_combobox.setFixedWidth(400)
        self.entry_list = [
            "Select PDO type",
            "Transmit PDO",
            "Receive PDO"
            ]
        self.entry_combobox.addItems(self.entry_list)
        self.entry_combobox.activated.connect(self.entry_combobox_activated)
        entry_layout.addWidget(self.entry_combobox)
        main_layout.addLayout(entry_layout)

        # Table widget
        table_layout = QHBoxLayout()
        table_layout.setContentsMargins(10,5,10,5)
        self.table = QTableWidget()
        self.table.setRowCount(4) 
        self.table.setColumnCount(5)
        names = ["Name", "Sync", "Inhibit", "Event", "Mapping"]
        self.table.setHorizontalHeaderLabels(names)
        self.table.verticalHeader().hide()
        self.table.setColumnWidth(0, 60)
        self.table.setColumnWidth(1, 60)
        self.table.setColumnWidth(2, 60)
        self.table.setColumnWidth(3, 60)
        self.table.setColumnWidth(4, 338)
        table_layout.addWidget(self.table)
        main_layout.addLayout(table_layout)
    
        # ENABLE Buttons
        enable_layout = QHBoxLayout()
        enable_layout.setContentsMargins(10,5,10,5)
        self.enable_label = QLabel("ENABLE PDO:".ljust(25))
        self.enable_label.setStyleSheet('border:0px; font: bold 12px;')
        enable_layout.addWidget(self.enable_label)
        self.PDO1_label = QLabel("TPDO1")
        self.PDO1_label.setStyleSheet('border:0px; font: 12px;')
        enable_layout.addWidget(self.PDO1_label)
        self.PDO1_checkbox = QCheckBox()
        self.PDO1_checkbox.setStyleSheet('border:0px; font: 12px;')
        self.PDO1_checkbox.toggled.connect(self.checkbox_pdo1_activated)
        enable_layout.addWidget(self.PDO1_checkbox)
        self.PDO2_label = QLabel("TPDO2")
        self.PDO2_label.setStyleSheet('border:0px; font: 12px;')
        enable_layout.addWidget(self.PDO2_label)
        self.PDO2_checkbox = QCheckBox()
        self.PDO2_checkbox.setStyleSheet('border:0px; font: 12px;')
        self.PDO2_checkbox.toggled.connect(self.checkbox_pdo2_activated)
        enable_layout.addWidget(self.PDO2_checkbox)
        self.PDO3_label = QLabel("TPDO3")
        self.PDO3_label.setStyleSheet('border:0px; font: 12px;')
        enable_layout.addWidget(self.PDO3_label)
        self.PDO3_checkbox = QCheckBox()
        self.PDO3_checkbox.setStyleSheet('border:0px; font: 12px;')
        self.PDO3_checkbox.toggled.connect(self.checkbox_pdo3_activated)
        enable_layout.addWidget(self.PDO3_checkbox)
        self.PDO4_label = QLabel("TPDO4")
        self.PDO4_label.setStyleSheet('border:0px; font: 12px;')
        enable_layout.addWidget(self.PDO4_label)
        self.PDO4_checkbox = QCheckBox()
        self.PDO4_checkbox.setStyleSheet('border:0px; font: 12px;')
        self.PDO4_checkbox.toggled.connect(self.checkbox_pdo4_activated)
        enable_layout.addWidget(self.PDO4_checkbox)
        main_layout.addLayout(enable_layout)

        # Update Button
        btn_layout = QHBoxLayout()
        btn_layout.setContentsMargins(10,5,10,10)
        btn_layout.setAlignment(Qt.AlignLeft)
        send_btn = QPushButton("UPDATE PDO")
        send_btn.setStyleSheet("QPushButton {background-color: rgb(224, 224, 224);} QPushButton:hover {background-color: #CED4DA; border: 1px solid #49545a; }")
        send_btn.setFixedSize(120, 40)
        send_btn.pressed.connect(self.update_pdo_pressed)
        btn_layout.addWidget(send_btn)
        main_layout.addLayout(btn_layout)

        widget = QWidget()
        widget.setLayout(main_layout)
        self.setCentralWidget(widget)

    def checkbox_pdo1_activated(self):
        try:
            self.device_id_combobox_activated()
            node = self.network.add_node(self.selected_node, 'PEAK.eds')
            if self.PDO1_checkbox.isChecked() == True:
                if self.entry_combobox.currentText() == "Transmit PDO":
                    # enable the TPDO
                    pdo_en = node.sdo.upload(0x1800, 1)
                    pdo_en = int.from_bytes(pdo_en, 'little') - 0x80000000
                    pdo_dis_bytes = pdo_en.to_bytes(4, byteorder='little')
                    node.sdo.download(0x1800, 1, pdo_dis_bytes)
                else:
                    # enable the RPDO
                    pdo_en = node.sdo.upload(0x1400, 1)
                    pdo_en = int.from_bytes(pdo_en, 'little') - 0x80000000
                    pdo_dis_bytes = pdo_en.to_bytes(4, byteorder='little')
                    node.sdo.download(0x1400, 1, pdo_dis_bytes)
                self.table.item(0,0).setBackground(COLOR_WHITE)
                self.table.item(0,1).setBackground(COLOR_WHITE)
                self.table.item(0,2).setBackground(COLOR_WHITE)
                self.table.item(0,3).setBackground(COLOR_WHITE)
                self.table.item(0,4).setBackground(COLOR_WHITE)
            else:
                if self.entry_combobox.currentText() == "Transmit PDO":
                    # Disable the TPDO (set highest bit in COBID)
                    pdo_dis = node.sdo.upload(0x1800, 1)
                    pdo_dis = 0x80000000 | int.from_bytes(pdo_dis, 'little')
                    pdo_dis_bytes = pdo_dis.to_bytes(4, byteorder='little')
                    node.sdo.download(0x1800, 1, pdo_dis_bytes)
                else:
                    # Disable the RPDO (set highest bit in COBID)
                    pdo_dis = node.sdo.upload(0x1400, 1)
                    pdo_dis = 0x80000000 | int.from_bytes(pdo_dis, 'little')
                    pdo_dis_bytes = pdo_dis.to_bytes(4, byteorder='little')
                    node.sdo.download(0x1400, 1, pdo_dis_bytes)
                self.table.item(0,0).setBackground(COLOR_RED)
                self.table.item(0,1).setBackground(COLOR_RED)       
                self.table.item(0,2).setBackground(COLOR_RED)       
                self.table.item(0,3).setBackground(COLOR_RED)
                self.table.item(0,4).setBackground(COLOR_RED)
        except:
            print("PDO1 FAIL")

    def checkbox_pdo2_activated(self):
        try:
            self.device_id_combobox_activated()
            node = self.network.add_node(self.selected_node, 'PEAK.eds')
            if self.PDO2_checkbox.isChecked() == True:
                if self.entry_combobox.currentText() == "Transmit PDO":
                    # enable the TPDO
                    pdo_en = node.sdo.upload(0x1801, 1)
                    pdo_en = int.from_bytes(pdo_en, 'little') - 0x80000000
                    pdo_dis_bytes = pdo_en.to_bytes(4, byteorder='little')
                    node.sdo.download(0x1801, 1, pdo_dis_bytes)
                else:
                    # enable the RPDO
                    pdo_en = node.sdo.upload(0x1401, 1)
                    pdo_en = int.from_bytes(pdo_en, 'little') - 0x80000000
                    pdo_dis_bytes = pdo_en.to_bytes(4, byteorder='little')
                    node.sdo.download(0x1401, 1, pdo_dis_bytes)
                self.table.item(1,0).setBackground(COLOR_WHITE)
                self.table.item(1,1).setBackground(COLOR_WHITE)
                self.table.item(1,2).setBackground(COLOR_WHITE)
                self.table.item(1,3).setBackground(COLOR_WHITE)
                self.table.item(1,4).setBackground(COLOR_WHITE)
            else:
                if self.entry_combobox.currentText() == "Transmit PDO":
                    # Disable the TPDO (set highest bit in COBID)
                    pdo_dis = node.sdo.upload(0x1801, 1)
                    pdo_dis = 0x80000000 | int.from_bytes(pdo_dis, 'little')
                    pdo_dis_bytes = pdo_dis.to_bytes(4, byteorder='little')
                    node.sdo.download(0x1801, 1, pdo_dis_bytes)
                else:
                    # Disable the RPDO (set highest bit in COBID)
                    pdo_dis = node.sdo.upload(0x1401, 1)
                    pdo_dis = 0x80000000 | int.from_bytes(pdo_dis, 'little')
                    pdo_dis_bytes = pdo_dis.to_bytes(4, byteorder='little')
                    node.sdo.download(0x1401, 1, pdo_dis_bytes)
                self.table.item(1,0).setBackground(COLOR_RED) 
                self.table.item(1,1).setBackground(COLOR_RED)   
                self.table.item(1,2).setBackground(COLOR_RED)   
                self.table.item(1,3).setBackground(COLOR_RED) 
                self.table.item(1,4).setBackground(COLOR_RED)   
        except:
            print("PDO2 FAIL")
        

    def checkbox_pdo3_activated(self):
        try:
            self.device_id_combobox_activated()
            node = self.network.add_node(self.selected_node, 'PEAK.eds')
            if self.PDO3_checkbox.isChecked() == True:
                if self.entry_combobox.currentText() == "Transmit PDO":
                    # enable the TPDO
                    pdo_en = node.sdo.upload(0x1802, 1)
                    pdo_en = int.from_bytes(pdo_en, 'little') - 0x80000000
                    pdo_dis_bytes = pdo_en.to_bytes(4, byteorder='little')
                    node.sdo.download(0x1802, 1, pdo_dis_bytes)
                else:
                    # enable the RPDO
                    pdo_en = node.sdo.upload(0x1402, 1)
                    pdo_en = int.from_bytes(pdo_en, 'little') - 0x80000000
                    pdo_dis_bytes = pdo_en.to_bytes(4, byteorder='little')
                    node.sdo.download(0x1402, 1, pdo_dis_bytes)
                self.table.item(2,0).setBackground(COLOR_WHITE)
                self.table.item(2,1).setBackground(COLOR_WHITE)
                self.table.item(2,2).setBackground(COLOR_WHITE)
                self.table.item(2,3).setBackground(COLOR_WHITE)
                self.table.item(2,4).setBackground(COLOR_WHITE)
            else:
                if self.entry_combobox.currentText() == "Transmit PDO":
                    # Disable the TPDO (set highest bit in COBID)
                    pdo_dis = node.sdo.upload(0x1802, 1)
                    pdo_dis = 0x80000000 | int.from_bytes(pdo_dis, 'little')
                    pdo_dis_bytes = pdo_dis.to_bytes(4, byteorder='little')
                    node.sdo.download(0x1802, 1, pdo_dis_bytes)
                else:
                    # Disable the RPDO (set highest bit in COBID)
                    pdo_dis = node.sdo.upload(0x1402, 1)
                    pdo_dis = 0x80000000 | int.from_bytes(pdo_dis, 'little')
                    pdo_dis_bytes = pdo_dis.to_bytes(4, byteorder='little')
                    node.sdo.download(0x1402, 1, pdo_dis_bytes)
                self.table.item(2,0).setBackground(COLOR_RED) 
                self.table.item(2,1).setBackground(COLOR_RED) 
                self.table.item(2,2).setBackground(COLOR_RED) 
                self.table.item(2,3).setBackground(COLOR_RED)
                self.table.item(2,4).setBackground(COLOR_RED)
        except:
            print("PDO3 FAIL")         

    def checkbox_pdo4_activated(self):
        try:
            self.device_id_combobox_activated()
            node = self.network.add_node(self.selected_node, 'PEAK.eds')
            if self.PDO4_checkbox.isChecked() == True:
                if self.entry_combobox.currentText() == "Transmit PDO":
                    # enable the TPDO
                    pdo_en = node.sdo.upload(0x1803, 1)
                    pdo_en = int.from_bytes(pdo_en, 'little') - 0x80000000
                    pdo_dis_bytes = pdo_en.to_bytes(4, byteorder='little')
                    node.sdo.download(0x1803, 1, pdo_dis_bytes)
                else:
                    # enable the RPDO
                    pdo_en = node.sdo.upload(0x1403, 1)
                    pdo_en = int.from_bytes(pdo_en, 'little') - 0x80000000
                    pdo_dis_bytes = pdo_en.to_bytes(4, byteorder='little')
                    node.sdo.download(0x1403, 1, pdo_dis_bytes)
                self.table.item(3,0).setBackground(COLOR_WHITE)
                self.table.item(3,1).setBackground(COLOR_WHITE)
                self.table.item(3,2).setBackground(COLOR_WHITE)
                self.table.item(3,3).setBackground(COLOR_WHITE)
                self.table.item(3,4).setBackground(COLOR_WHITE)
            else:
                if self.entry_combobox.currentText() == "Transmit PDO":
                    # Disable the TPDO (set highest bit in COBID)
                    pdo_dis = node.sdo.upload(0x1803, 1)
                    pdo_dis = 0x80000000 | int.from_bytes(pdo_dis, 'little')
                    pdo_dis_bytes = pdo_dis.to_bytes(4, byteorder='little')
                    node.sdo.download(0x1803, 1, pdo_dis_bytes)
                else:
                    # Disable the RPDO (set highest bit in COBID)
                    pdo_dis = node.sdo.upload(0x1403, 1)
                    pdo_dis = 0x80000000 | int.from_bytes(pdo_dis, 'little')
                    pdo_dis_bytes = pdo_dis.to_bytes(4, byteorder='little')
                    node.sdo.download(0x1403, 1, pdo_dis_bytes)
                self.table.item(3,0).setBackground(COLOR_RED) 
                self.table.item(3,1).setBackground(COLOR_RED)
                self.table.item(3,2).setBackground(COLOR_RED)
                self.table.item(3,3).setBackground(COLOR_RED)
                self.table.item(3,4).setBackground(COLOR_RED)
        except:
            print("PDO4 FAIL")              

    def update_device_list(self):
        self.device_id_combobox.clear()
        self.device_id_combobox.addItems(self.device_list)
        
    def device_id_combobox_activated(self):
        self.selected_node = int(self.device_id_combobox.currentText())
    
    def entry_combobox_activated(self):
        try:
            self.device_id_combobox_activated()
            node = self.network.add_node(self.selected_node, 'PEAK.eds')
            # TPDO / RPDO print
            if self.entry_combobox.currentText() == "Transmit PDO":
                for i in range(4):
                    # NAME Print
                    item = QTableWidgetItem(f"TPDO_{i+1}")
                    item.setFont(FONT_BOLD)
                    item.setTextAlignment(Qt.AlignCenter)
                    self.table.setItem(i, 0, item)
                    # SYNC Print
                    index = 0x1800+i
                    sync_type = node.sdo.upload(index, 2)
                    sync_type = int.from_bytes(sync_type, 'little')
                    item = QTableWidgetItem(f"{sync_type}")
                    item.setFont(FONT_BOLD)
                    item.setTextAlignment(Qt.AlignCenter)
                    self.table.setItem(i, 1, item)
                    sleep(0.05)
                    # INHIBIT TIME Print
                    index = 0x1800+i
                    inhibit = node.sdo.upload(index, 3)
                    inhibit = int.from_bytes(inhibit, 'little')
                    item = QTableWidgetItem(f"{inhibit}")
                    item.setFont(FONT_BOLD)
                    item.setTextAlignment(Qt.AlignCenter)
                    self.table.setItem(i, 2, item)
                    sleep(0.05)
                    # EVENT TIME Print
                    index = 0x1800+i
                    event = node.sdo.upload(index, 5)
                    event = int.from_bytes(event, 'little')
                    item = QTableWidgetItem(f"{event}")
                    item.setFont(FONT_BOLD)
                    item.setTextAlignment(Qt.AlignCenter)
                    self.table.setItem(i, 3, item)
                    sleep(0.05)
                    # MAPPING Print
                    index = 0x1a00+i
                    mapping_num = node.sdo.upload(index, 0)
                    mapping_num = int.from_bytes(mapping_num, 'little')
                    print(f"NUM: {mapping_num}")
                    mapping_list = []
                    for k in range(mapping_num):
                        map_item = node.sdo.upload(index, k+1)
                        map_item = int.from_bytes(map_item, 'little')
                        mapping_list.append(f"{map_item:08x}")
                    print(mapping_list)
                    new_item = QTableWidgetItem()
                    new_item.setText(f"{mapping_list}")
                    new_item.setFont(FONT_BOLD)
                    # new_item.setTextAlignment(Qt.AlignCenter)
                    self.table.setItem(i, 4, new_item)
                for i in range(4):
                    # CHECK ENABLE
                    index = 0x1800+i
                    en = node.sdo.upload(index, 1)
                    en = int.from_bytes(en, 'little')
                    en_str = f"{en:08x}"
                    pdo_enable_list = [self.PDO1_checkbox, self.PDO2_checkbox, self.PDO3_checkbox, self.PDO4_checkbox]
                    bg_change_func = [self.checkbox_pdo1_activated, self.checkbox_pdo2_activated, self.checkbox_pdo3_activated, self.checkbox_pdo4_activated]
                    if en_str[0] == "8":
                        pdo_enable_list[i].setChecked(False)
                        bg_change_func[i]()
                    if en_str[0] == "0":
                        pdo_enable_list[i].setChecked(True)
                        bg_change_func[i]()
                    sleep(0.05)
            else:
                for i in range(4):
                    # NAME Print
                    item = QTableWidgetItem(f"RPDO_{i+1}")
                    item.setFont(FONT_BOLD)
                    item.setTextAlignment(Qt.AlignCenter)
                    self.table.setItem(i, 0, item)
                    
                    # SYNC Print
                    index = 0x1400+i
                    sync_type = node.sdo.upload(index, 2)
                    sync_type = int.from_bytes(sync_type, 'little')
                    item = QTableWidgetItem(f"{sync_type}")
                    item.setFont(FONT_BOLD)
                    item.setTextAlignment(Qt.AlignCenter)
                    self.table.setItem(i, 1, item)
                    sleep(0.05)

                    # INHIBIT and EVENT
                    item = QTableWidgetItem("NONE")
                    item.setFont(FONT_BOLD)
                    item.setTextAlignment(Qt.AlignCenter)
                    self.table.setItem(i, 2, item)
                    sleep(0.05)
                    item = QTableWidgetItem("NONE")
                    item.setFont(FONT_BOLD)
                    item.setTextAlignment(Qt.AlignCenter)
                    self.table.setItem(i, 3, item)
                    sleep(0.05)

                    # MAPPING Print
                    index = 0x1600+i
                    mapping_num = node.sdo.upload(index, 0)
                    mapping_num = int.from_bytes(mapping_num, 'little')
                    mapping_list = []
                    for k in range(mapping_num):
                        map_item = node.sdo.upload(index, k+1)
                        map_item = int.from_bytes(map_item, 'little')
                        mapping_list.append(f"{map_item:08x}")
                    new_item = QTableWidgetItem()
                    new_item.setText(f"{mapping_list}")
                    new_item.setFont(FONT_BOLD)
                    self.table.setItem(i, 4, new_item)

                for i in range(4):
                    # CHECK ENABLE
                    index = 0x1400+i
                    en = node.sdo.upload(index, 1)
                    en = int.from_bytes(en, 'little')
                    en_str = f"{en:08x}"
                    pdo_enable_list = [self.PDO1_checkbox, self.PDO2_checkbox, self.PDO3_checkbox, self.PDO4_checkbox]
                    bg_change_func = [self.checkbox_pdo1_activated, self.checkbox_pdo2_activated, self.checkbox_pdo3_activated, self.checkbox_pdo4_activated]
                    if en_str[0] == "8":
                        pdo_enable_list[i].setChecked(False)
                        bg_change_func[i]()
                    if en_str[0] == "0":
                        pdo_enable_list[i].setChecked(True)
                        bg_change_func[i]()
                    sleep(0.05)
        except canopen.sdo.exceptions.SdoCommunicationError:
            print("ERROR: No SDO Response")
            WarningMessage("No SDO Response")
    
    def update_pdo_pressed(self):
        self.device_id_combobox_activated()
        node = self.network.add_node(self.selected_node, 'PEAK.eds')
        enabled_pdo = [self.PDO1_checkbox.isChecked(), self.PDO2_checkbox.isChecked(), self.PDO3_checkbox.isChecked(), self.PDO4_checkbox.isChecked()]
        print(enabled_pdo)
        if self.entry_combobox.currentText() == "Transmit PDO":
            for i in range(4):
                if enabled_pdo[i] == False:
                    # SYNC
                    sync = int(self.table.item(i, 1).text())
                    sync_bytes = sync.to_bytes(1, byteorder='little')
                    index = 0x1800 + i
                    node.sdo.download(index, 2, sync_bytes)
                    sleep(0.05)
                    # INHIBIT
                    inhibit = int(self.table.item(i, 2).text())
                    inhibit_bytes = inhibit.to_bytes(2, byteorder='little')
                    index = 0x1800 + i
                    node.sdo.download(index, 3, inhibit_bytes)
                    sleep(0.05)
                    # EVENT
                    event = int(self.table.item(i, 3).text())
                    event_bytes = event.to_bytes(2, byteorder='little')
                    index = 0x1800 + i
                    node.sdo.download(index, 5, event_bytes)
                    sleep(0.05)
                    # MAPPING
                    map_list = self.table.item(i, 4).text()
                    map_list = map_list.replace("[", "")
                    map_list = map_list.replace("]", "")
                    map_list = map_list.replace("'", "")
                    map_list = map_list.split(', ')
                    print(map_list)
                    map_int_list = []
                    if map_list[0].isnumeric():
                        for num in map_list:
                            temp = int(num, 16)
                            map_int_list.append(temp)
                    print(map_int_list)
                    # Write zero to the number of mapping entries
                    zero = 0
                    zero_bytes = zero.to_bytes(1, byteorder='little')
                    index = 0x1a00 + i
                    node.sdo.download(index, 0, zero_bytes)
                    sleep(0.05)
                    # Now make your new mapping entries, but one by one (subindex 1, 2, 3 - in order)
                    for k in range(len(map_int_list)):
                        maping = map_int_list[k]
                        maping_bytes = maping.to_bytes(4, byteorder='little')
                        index = 0x1a00 + i
                        node.sdo.download(index, k+1, maping_bytes)
                        sleep(0.05)
                    # When done, write the new non zero value to the number of mapping entries
                    entries_num = len(map_int_list)
                    entries_num_bytes = entries_num.to_bytes(1, byteorder='little')
                    index = 0x1a00 + i
                    node.sdo.download(index, 0, entries_num_bytes)
                    sleep(0.05)
        else:
            for i in range(4):
                if enabled_pdo[i] == False:
                    # SYNC
                    sync = int(self.table.item(i, 1).text())
                    sync_bytes = sync.to_bytes(1, byteorder='little')
                    index = 0x1400 + i
                    node.sdo.download(index, 2, sync_bytes)
                    sleep(0.05)
                    # MAPPING
                    map_list = self.table.item(i, 4).text()
                    map_list = map_list.replace("[", "")
                    map_list = map_list.replace("]", "")
                    map_list = map_list.replace("'", "")
                    map_list = map_list.split(', ')
                    print(map_list)
                    map_int_list = []
                    if map_list[0].isnumeric():
                        for num in map_list:
                            temp = int(num, 16)
                            map_int_list.append(temp)
                    print(map_int_list)
                    # Write zero to the number of mapping entries
                    zero = 0
                    zero_bytes = zero.to_bytes(1, byteorder='little')
                    index = 0x1600 + i
                    node.sdo.download(index, 0, zero_bytes)
                    sleep(0.05)
                    # Now make your new mapping entries, but one by one (subindex 1, 2, 3 - in order)
                    for k in range(len(map_int_list)):
                        maping = map_int_list[k]
                        maping_bytes = maping.to_bytes(4, byteorder='little')
                        index = 0x1600 + i
                        node.sdo.download(index, k+1, maping_bytes)
                        sleep(0.05)
                    # When done, write the new non zero value to the number of mapping entries
                    entries_num = len(map_int_list)
                    entries_num_bytes = entries_num.to_bytes(1, byteorder='little')
                    index = 0x1600 + i
                    node.sdo.download(index, 0, entries_num_bytes)
                    sleep(0.05)


class ErrorMessage:
    def __init__(self, error_text):
        pop_msg = QMessageBox()
        pop_msg.setIcon(QMessageBox.Critical)
        pop_msg.setWindowTitle("Error Message")
        pop_msg.setText(f'{error_text}'.ljust(50))
        pop_msg.exec()

class WarningMessage:
    def __init__(self, warning_text):
        pop_msg = QMessageBox()
        pop_msg.setIcon(QMessageBox.Warning)
        pop_msg.setWindowTitle("Warning Message")
        pop_msg.setText(f'{warning_text}'.ljust(50))
        pop_msg.exec()
 

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.showMaximized()
    app.exec()