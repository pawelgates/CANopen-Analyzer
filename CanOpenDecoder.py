import io
from rich.console import Console
from datetime import datetime
from time import sleep

console = Console()

SDO_ABORT_CODES_DICT = {
    0x05030000 : "Toggle bit not alternated",
    0x05040000 : "SDO Protocol timed out",
    0x05040001 : "Client/Server command specifier not valid or unknown",
    0x05040002 : "Invalid block size (block mode)",
    0x05040003 : "Invalid sequence number (block mode)",
    0x05040004 : "CRC error (block mode)",
    0x05040005 : "Out of memory",
    0x06010000 : "Unsupported access to an object",
    0x06010001 : "Attempt to read a write-only object",
    0x06010002 : "Attempt to write a read-only object",
    0x06020000 : "Object does not exist in the Object Dictionary",
    0x06040041 : "Object cannot be mapped to the PDO",
    0x06040042 : "The number and length of the objects to be mapped would exceed PDO length",
    0x06040043 : "General parameter incompatibility",
    0x06040047 : "General internal incompatibility in the device",
    0x06060000 : "Access failed due to a hardware error",
    0x06070010 : "Data type does not match. Length of service parameter does not match",
    0x06070012 : "Data type does not match. Length of service parameter is too high",
    0x06070013 : "Data type does not match. Length of service parameter is too low",
    0x06090011 : "Subindex does not exist",
    0x06090030 : "Value range of parameter exceeded (write access only)",
    0x06090031 : "Value of parameter written is too high",
    0x06090032 : "Value of parameter written is too low",
    0x06090036 : "Maximum value is less than the minimum value",
    0x08000000 : "General error",
    0x08000020 : "Data cannot be transferred or stored to the application",
    0x08000021 : "Data cannot be transferred or stored to the application because of local control",
    0x08000022 : "Data cannot be transferred or stored to the application because of the present device state",
    0x08000023 : "Object Dictionary dynamic generation failed or no Object Dictionary is present"
}

SDO_ABORT_CODES = list(SDO_ABORT_CODES_DICT.keys())

EMCY_ERROR_CODES_DICT = {
    0x0    : "Error reset or no error",
    0x1000 : "Generic error",
    0x2000 : "Current",
    0x2100 : "Current, CANopen device input side",
    0x2200 : "Current inside the CANopen device",
    0x2300 : "Current, CANopen device output side",
    0x3000 : "Voltage",
    0x3100 : "Mains voltage",
    0x3200 : "Voltage inside the CANopen device",
    0x3300 : "Output voltage",
    0x4000 : "Temperature",
    0x4100 : "Ambient temperature",
    0x4200 : "Device temperature",
    0x5000 : "CANopen device hardware",
    0x6000 : "CANopen device software",
    0x6100 : "Internal software",
    0x6200 : "User software",
    0x6300 : "Data set",
    0x7000 : "Additional modules",
    0x8000 : "Monitoring",
    0x8100 : "Communication",
    0x8110 : "CAN overrun (objects lost)",
    0x8120 : "CAN in error passive mode",
    0x8130 : "Life guard error or heartbeat error",
    0x8140 : "Recovered from bus off",
    0x8150 : "CAN-ID collision",
    0x8200 : "Protocol error",
    0x8210 : "PDO not processed due to length error",
    0x8220 : "PDO length exceeded",
    0x8230 : "DAM MPDO not processed, destination object not available",
    0x9000 : "External error",
    0xF000 : "Additional functions",
    0xFF00 : "Device specific"
}

EMCY_ERROR_CODES = list(EMCY_ERROR_CODES_DICT.keys())

EMCY_ERROR_REG_DICT = {
    1 : "// Generic error",
    2 : "// Current error",
    4 : "// Voltage error",
    8 : "// Temperature error",
    16 : "// Communication error (overrun, error state)",
    32 : "// Device profile specific error",
    64 : "// Reserved (always 0)",
    128 : "// Manufacturer-specific error"
}

EMCY_ERROR_REG = list(EMCY_ERROR_REG_DICT.keys())

class LogDataMsg:
    timestamp = None
    device_id = None
    pdo_num = None
    raw_data = None

class CanOpenMsg:
    type = None
    id = None
    data = None
    count = 1
    raw_data = None

class CanOpenDecoder:

    def __init__(self):
        self.type = None
        self.id = None
        self.data = None
        self.raw_data = None
        self.cobid = None


    def decode_cob_id(self, cob_id):
        self.cobid = cob_id
        if cob_id == 0x0:
            self.type = "NMT"
            self.id = 0
        elif cob_id == 0x80:
            self.type = "SYNC"
            self.id = 0
        elif cob_id >= 0x81 and cob_id <= 0xFF:
            self.type = "EMCY"
            self.id = cob_id - 0x80
        elif cob_id == 0x100:
            self.type = "TIME"
            self.id = 0
        elif cob_id >= 0x181 and cob_id <= 0x1FF:
            self.type = "T_PDO_1"
            self.id = cob_id - 0x180
        elif cob_id >= 0x201 and cob_id <= 0x27F:
            self.type = "R_PDO_1"
            self.id = cob_id - 0x200
        elif cob_id >= 0x281 and cob_id <= 0x2FF:
            self.type = "T_PDO_2"
            self.id = cob_id - 0x280
        elif cob_id >= 0x301 and cob_id <= 0x37F:
            self.type = "R_PDO_2"
            self.id = cob_id - 0x300
        elif cob_id >= 0x381 and cob_id <= 0x3FF:
            self.type = "T_PDO_3"
            self.id = cob_id - 0x380
        elif cob_id >= 0x401 and cob_id <= 0x47F:
            self.type = "R_PDO_3"
            self.id = cob_id - 0x400
        elif cob_id >= 0x481 and cob_id <= 0x4FF:
            self.type = "T_PDO_4"
            self.id = cob_id - 0x480
        elif cob_id >= 0x501 and cob_id <= 0x57F:
            self.type = "R_PDO_4"
            self.id = cob_id - 0x500
        elif cob_id >= 0x581 and cob_id <= 0x5FF:
            self.type = "T_SDO"
            self.id = cob_id - 0x580
        elif cob_id >= 0x601 and cob_id <= 0x67F:
            self.type = "R_SDO"
            self.id = cob_id - 0x600
        elif cob_id >= 0x701 and cob_id <= 0x77F:
            self.type = "HEARTBEAT"
            self.id = cob_id - 0x700
        elif cob_id == 0x7E5:
            self.type = "LSS MASTER"
            self.id = 0
        elif cob_id == 0x7E4:
            self.type = "LSS SLAVE"
            self.id = 0


    def decode_data(self, payload):
        match self.type:
            case "NMT":
                data_frame = io.BytesIO(payload)
                requested_state = int.from_bytes(data_frame.read(1), byteorder="little", signed=False)
                addressed_node = int.from_bytes(data_frame.read(1), byteorder="little", signed=False)
                self.raw_data = f"{str(hex(requested_state))[2:].rjust(2, '0')} {str(hex(addressed_node))[2:].rjust(2, '0')}"
                match requested_state:
                    case 0x01:
                        if addressed_node == 0x0:
                            self.data = f"OPERATIONAL State to ALL devices"
                        else:
                            self.data = f"OPERATIONAL State to {addressed_node} device"
                    case 0x02:
                        if addressed_node == 0x0:
                            self.data = f"STOPPED State to ALL devices"
                        else:
                            self.data = f"STOPPED State to {addressed_node} device"
                    case 0x80:
                        if addressed_node == 0x0:
                            self.data = f"PRE-OPERATIONAL State to ALL devices"
                        else:
                            self.data = f"PRE-OPERATIONAL State to {addressed_node} device"
                    case 0x81:
                        if addressed_node == 0x0:
                            self.data = f"RESET State to ALL devices"
                        else:
                            self.data = f"RESET State to {addressed_node} device"
                    case 0x82:
                        if addressed_node == 0x0:
                            self.data = f"RESET COMMUNICATION State to ALL devices"
                        else:
                            self.data = f"RESET COMMUNICATION State to {addressed_node} device"
            
            case "SYNC":
                self.data = f"SYNC Message"
            
            case "EMCY":
                data_frame = io.BytesIO(payload)
                error_code = int.from_bytes(data_frame.read(2), byteorder="little", signed=False)
                # error_code = 0x8150
                error_reg = int.from_bytes(data_frame.read(1), byteorder="little", signed=False)
                # error_reg = 25
                error_manuf = int.from_bytes(data_frame.read(5), byteorder="little", signed=False)
                self.raw_data = f"{str(hex(error_code))[2:].rjust(4, '0')} {str(hex(error_reg))[2:].rjust(2, '0')} {str(hex(error_manuf))[2:].rjust(10, '0')}"
                errors_list = ""
                if error_code in EMCY_ERROR_CODES:
                    for error in EMCY_ERROR_REG:
                        if error_reg & error == error:
                            errors_list = errors_list + (EMCY_ERROR_REG_DICT[error]) + " "
                    self.data = f"{error_code:04x}h, {error_reg:08b}b - {EMCY_ERROR_CODES_DICT[error_code]} {errors_list}"
                else:
                    self.data = f"{error_code:04x}h, {error_reg:08b}b - UNDEFINED"
           
            case "TIME":
                pass
            
            case "T_PDO_1":
                data_frame = io.BytesIO(payload)
                word1 = int.from_bytes(data_frame.read(2), byteorder="little", signed=False)
                word2 = int.from_bytes(data_frame.read(2), byteorder="little", signed=False)
                word3 = int.from_bytes(data_frame.read(2), byteorder="little", signed=False)
                word4 = int.from_bytes(data_frame.read(2), byteorder="little", signed=False)
                self.raw_data = f"{str(hex(word1))[2:].rjust(4, '0')} {str(hex(word2))[2:].rjust(4, '0')} {str(hex(word3))[2:].rjust(4, '0')} {str(hex(word4))[2:].rjust(4, '0')}"
                self.data = f"{round((word1/1024)*5, 2)}V,    {round((word2/1024)*5, 2)}V,    {round((word3/1024)*5, 2)}V,    {round((word4/1024)*5, 2)}V"
            
            case "R_PDO_1":
                data_frame = io.BytesIO(payload)
                word1 = int.from_bytes(data_frame.read(2), byteorder="little", signed=False)
                word2 = int.from_bytes(data_frame.read(2), byteorder="little", signed=False)
                word3 = int.from_bytes(data_frame.read(2), byteorder="little", signed=False)
                word4 = int.from_bytes(data_frame.read(2), byteorder="little", signed=False)
                self.raw_data = f"{str(hex(word1))[2:].rjust(4, '0')} {str(hex(word2))[2:].rjust(4, '0')} {str(hex(word3))[2:].rjust(4, '0')} {str(hex(word4))[2:].rjust(4, '0')}"
                self.data = f"DATA: {word1}, {word2}, {word3}, {word4}"
            
            case "T_PDO_2":
                data_frame = io.BytesIO(payload)
                word1 = int.from_bytes(data_frame.read(2), byteorder="little", signed=False)
                word2 = int.from_bytes(data_frame.read(2), byteorder="little", signed=False)
                word3 = int.from_bytes(data_frame.read(2), byteorder="little", signed=False)
                word4 = int.from_bytes(data_frame.read(2), byteorder="little", signed=False)
                self.raw_data = f"{str(hex(word1))[2:].rjust(4, '0')} {str(hex(word2))[2:].rjust(4, '0')} {str(hex(word3))[2:].rjust(4, '0')} {str(hex(word4))[2:].rjust(4, '0')}"
                self.data = f"{round((word1/1024)*5, 2)}V,    {round((word2/1024)*5, 2)}V,    {round((word3/1024)*5, 2)}V,    {round((word4/1024)*5, 2)}V"
            
            case "R_PDO_2":
                data_frame = io.BytesIO(payload)
                word1 = int.from_bytes(data_frame.read(2), byteorder="little", signed=False)
                word2 = int.from_bytes(data_frame.read(2), byteorder="little", signed=False)
                word3 = int.from_bytes(data_frame.read(2), byteorder="little", signed=False)
                word4 = int.from_bytes(data_frame.read(2), byteorder="little", signed=False)
                self.raw_data = f"{str(hex(word1))[2:].rjust(4, '0')} {str(hex(word2))[2:].rjust(4, '0')} {str(hex(word3))[2:].rjust(4, '0')} {str(hex(word4))[2:].rjust(4, '0')}"
                self.data = f"DATA: {word1}, {word2}, {word3}, {word4}"
            
            case "T_PDO_3":
                data_frame = io.BytesIO(payload)
                word1 = int.from_bytes(data_frame.read(2), byteorder="little", signed=False)
                word2 = int.from_bytes(data_frame.read(2), byteorder="little", signed=False)
                word3 = int.from_bytes(data_frame.read(2), byteorder="little", signed=False)
                word4 = int.from_bytes(data_frame.read(2), byteorder="little", signed=False)
                self.raw_data = f"{str(hex(word1))[2:].rjust(4, '0')} {str(hex(word2))[2:].rjust(4, '0')} {str(hex(word3))[2:].rjust(4, '0')} {str(hex(word4))[2:].rjust(4, '0')}"
                self.data = f"DATA: {word1}, {word2}, {word3}, {word4}"
            
            case "R_PDO_3":
                data_frame = io.BytesIO(payload)
                word1 = int.from_bytes(data_frame.read(2), byteorder="little", signed=False)
                word2 = int.from_bytes(data_frame.read(2), byteorder="little", signed=False)
                word3 = int.from_bytes(data_frame.read(2), byteorder="little", signed=False)
                word4 = int.from_bytes(data_frame.read(2), byteorder="little", signed=False)
                self.raw_data = f"{str(hex(word1))[2:].rjust(4, '0')} {str(hex(word2))[2:].rjust(4, '0')} {str(hex(word3))[2:].rjust(4, '0')} {str(hex(word4))[2:].rjust(4, '0')}"
                self.data = f"DATA: {word1}, {word2}, {word3}, {word4}"
           
            case "T_PDO_4":
                data_frame = io.BytesIO(payload)
                word1 = int.from_bytes(data_frame.read(2), byteorder="little", signed=False)
                word2 = int.from_bytes(data_frame.read(2), byteorder="little", signed=False)
                word3 = int.from_bytes(data_frame.read(2), byteorder="little", signed=False)
                word4 = int.from_bytes(data_frame.read(2), byteorder="little", signed=False)
                self.raw_data = f"{str(hex(word1))[2:].rjust(4, '0')} {str(hex(word2))[2:].rjust(4, '0')} {str(hex(word3))[2:].rjust(4, '0')} {str(hex(word4))[2:].rjust(4, '0')}"
                self.data = f"DATA: {word1}, {word2}, {word3}, {word4}"
            
            case "R_PDO_4":
                data_frame = io.BytesIO(payload)
                word1 = int.from_bytes(data_frame.read(2), byteorder="little", signed=False)
                word2 = int.from_bytes(data_frame.read(2), byteorder="little", signed=False)
                word3 = int.from_bytes(data_frame.read(2), byteorder="little", signed=False)
                word4 = int.from_bytes(data_frame.read(2), byteorder="little", signed=False)
                self.raw_data = f"{str(hex(word1))[2:].rjust(4, '0')} {str(hex(word2))[2:].rjust(4, '0')} {str(hex(word3))[2:].rjust(4, '0')} {str(hex(word4))[2:].rjust(4, '0')}"
                self.data = f"DATA: {word1}, {word2}, {word3}, {word4}"
            
            case "T_SDO":
                data_frame = io.BytesIO(payload)
                cmd = int.from_bytes(data_frame.read(1), byteorder="little", signed=False)
                entry = int.from_bytes(data_frame.read(2), byteorder="little", signed=False)
                subentry = int.from_bytes(data_frame.read(1), byteorder="little", signed=False)
                data = None
                data = int.from_bytes(data_frame.read(4), byteorder="little", signed=False)
                data_for_raw = f"{data:08x}"
                self.raw_data = f"{str(hex(cmd))[2:].rjust(2, '0')} {str(hex(entry))[2:].rjust(4, '0')} {str(hex(subentry))[2:].rjust(2, '0')} {data_for_raw[-2:]}{data_for_raw[-4:-2]}{data_for_raw[-6:-4]}{data_for_raw[-8:-6]}"
                if data in SDO_ABORT_CODES:
                    self.data = f"ERROR: 0x{data:08x} - {SDO_ABORT_CODES_DICT[data]}"
                else:
                    self.data = f"DATA: 0x{data:08x} ({data})"
            
            case "R_SDO":
                data_frame = io.BytesIO(payload)
                cmd = int.from_bytes(data_frame.read(1), byteorder="little", signed=False)
                entry = int.from_bytes(data_frame.read(2), byteorder="little", signed=False)
                subentry = int.from_bytes(data_frame.read(1), byteorder="little", signed=False)
                data = None
                data = int.from_bytes(data_frame.read(4), byteorder="little", signed=False)
                data_for_raw = f"{data:08x}"
                self.raw_data = f"{str(hex(cmd))[2:].rjust(2, '0')} {str(hex(entry))[2:].rjust(4, '0')} {str(hex(subentry))[2:].rjust(2, '0')} {data_for_raw[-2:]}{data_for_raw[-4:-2]}{data_for_raw[-6:-4]}{data_for_raw[-8:-6]}"
                if data in SDO_ABORT_CODES:
                    self.data = f"ERROR: 0x{data:08x} - {SDO_ABORT_CODES_DICT[data]}"
                else:
                    self.data = f"DATA: 0x{data:08x} ({data})"
            
            case "HEARTBEAT":
                data_frame = io.BytesIO(payload)
                state = int.from_bytes(data_frame.read(1), byteorder="little", signed=False)
                self.raw_data = str(hex(state))[2:].rjust(2, '0')
                match state:
                    case 0x0:
                        self.data = f"BOOT-UP State"
                    case 0x04:
                        self.data = f"STOPPED State"
                    case 0x05:
                        self.data = f"OPERATIONAL State"
                    case 0x7f:
                        self.data = f"PRE-OPERATIONAL State"

    def return_data(self) -> CanOpenMsg:
        msg = CanOpenMsg()
        msg.type = self.type
        msg.id = self.id
        msg.data = self.data
        msg.raw_data = f"{str(hex(self.cobid))}    {self.raw_data}"
        return msg

    def return_log(self) -> LogDataMsg:
        log_msg = LogDataMsg()
        log_msg.device_id = self.id
        dt = datetime.now()
        ts = datetime.timestamp(dt)
        log_msg.timestamp = ts
        log_msg.pdo_num = self.type
        log_msg.raw_data = self.raw_data
        return log_msg
    
            