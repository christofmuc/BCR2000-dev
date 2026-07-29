import io
import sys
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import bcfwconvert
import bcfwflash


class FakeMidiDevice:
    def __init__(self, incoming=b""):
        self.incoming = io.BytesIO(incoming)
        self.written = bytearray()

    def fileno(self):
        return 42

    def read(self, count):
        return self.incoming.read(count)

    def write(self, data):
        self.written.extend(data)
        return len(data)

    def flush(self):
        pass


class FirmwareFlasherTests(unittest.TestCase):
    def test_shared_encoding_matches_converter(self):
        data = [(index * 61 + 7) & 0xFF for index in range(7 * 8)]
        self.assertEqual(
            bcfwflash.syx_explode(data),
            bcfwconvert.syx_explode(data),
        )
        self.assertEqual(
            bcfwflash.syx_implode(bcfwflash.syx_explode(data)),
            data,
        )

    def test_midi_receive_sysex_ignores_other_bytes(self):
        device = FakeMidiDevice(b"\x90\x40\x7f\xf0\x7d\x01\xf7")
        with mock.patch.object(
            bcfwflash.select, "select", return_value=([42], [], [])
        ):
            message = bcfwflash.midi_receive_sysex(device)

        self.assertEqual(message, [0xF0, 0x7D, 0x01, 0xF7])

    def test_midi_check_sysex_rejects_short_message(self):
        with self.assertRaisesRegex(bcfwflash.BCFWException, "malformed"):
            bcfwflash.midi_check_sysex([0xF0, 0xF7], [0x35])

    def test_send_display_builds_expected_firmware_packet(self):
        device = FakeMidiDevice()

        bcfwflash.send_display(device, "TEST")

        packet = list(device.written)
        self.assertEqual(
            packet[:7], [0xF0, 0x00, 0x20, 0x32, 0x7F, 0x7F, 0x34]
        )
        self.assertEqual(packet[-1], 0xF7)
        argument = bcfwflash.syx_decode(
            bcfwflash.syx_implode(packet[7:-1])
        )
        self.assertEqual(argument[:2], [0xFF, 0x00])
        self.assertEqual(bytes(argument[3:7]), b"TEST")
        checksum = 0
        for byte in argument[3:]:
            checksum = bcfwflash.syx_checksum_update(byte, checksum)
        self.assertEqual(argument[2], checksum)

    def test_flash_upload_discards_non_sysex_prefix(self):
        firmware = bcfwconvert.dump2syx(
            [0x42] * 0x1000, 0x2000, 0x15
        )
        acknowledgement = bytes(
            [0xF0, 0x00, 0x20, 0x32, 0x7F, 0x15, 0x35, 0x00, 0x2F, 0, 0xF7]
        )
        device = FakeMidiDevice(acknowledgement)

        with mock.patch.object(
            bcfwflash.select, "select", return_value=([42], [], [])
        ):
            bcfwflash.flash_upload(device, [1, 2, 3] + firmware)

        self.assertEqual(bytes(device.written), bytes(firmware))

    def test_flash_get_validates_page_alignment(self):
        with self.assertRaisesRegex(
            bcfwflash.BCFWException, "Start address"
        ):
            bcfwflash.flash_get(FakeMidiDevice(), 1, 0x100)
        with self.assertRaisesRegex(bcfwflash.BCFWException, "Count"):
            bcfwflash.flash_get(FakeMidiDevice(), 0, 1)


if __name__ == "__main__":
    unittest.main()
