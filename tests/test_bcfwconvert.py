import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import bcfwconvert


class FirmwareConversionTests(unittest.TestCase):
    def test_word_pack_round_trip(self):
        for value in (0, 1, 0x12345678, 0xFFFFFFFF):
            self.assertEqual(bcfwconvert.wunpack(bcfwconvert.wpack(value)), value)

    def test_sysex_seven_bit_encoding_round_trip(self):
        data = [(index * 73 + 0x80) & 0xFF for index in range(7 * 19)]
        encoded = bcfwconvert.syx_explode(data)

        self.assertTrue(all(byte < 0x80 for byte in encoded))
        self.assertEqual(bcfwconvert.syx_implode(encoded), data)

    def test_sysex_ciphers_are_involutions(self):
        data = [(index * 41 + 17) & 0xFF for index in range(512)]

        self.assertEqual(
            bcfwconvert.syx_decode(bcfwconvert.syx_decode(data)),
            data,
        )
        self.assertEqual(
            bcfwconvert.syx_decode_write(
                bcfwconvert.syx_decode_write(data, 7), 7
            ),
            data,
        )

    def test_os_dump_round_trip_including_unaligned_lengths(self):
        for size in (1, 4, 257, 4088, 4093):
            with self.subTest(size=size):
                image = [(index * 29 + size) & 0xFF for index in range(size)]
                dump = bcfwconvert.os2dump(image)
                self.assertEqual(bcfwconvert.dump2os(dump), image)

    def test_firmware_sysex_round_trip_across_64k_address(self):
        dump = [(index * 17 + 3) & 0xFF for index in range(0xF000)]

        sysex = bcfwconvert.dump2syx(dump, 0x2000, 0x15)
        decoded = bcfwconvert.syx2dump(sysex)

        self.assertEqual(decoded, dump)

    def test_packet_checksum_error_is_rejected(self):
        sysex = bcfwconvert.dump2syx([0x55] * 0x1000, 0x2000, 0x15)
        sysex[20] ^= 1

        with self.assertRaisesRegex(bcfwconvert.BCFWException, "Checksum"):
            bcfwconvert.syx2dump(sysex)

    def test_cli_round_trip_uses_binary_files(self):
        image = bytes((index * 11 + 9) & 0xFF for index in range(4088))
        with tempfile.TemporaryDirectory() as directory:
            directory = Path(directory)
            image_path = directory / "input.bin"
            sysex_path = directory / "firmware.syx"
            result_path = directory / "result.bin"
            image_path.write_bytes(image)

            subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "bcfwconvert.py"),
                    "-i",
                    str(image_path),
                    "-I",
                    "os",
                    "-o",
                    str(sysex_path),
                    "-O",
                    "syx",
                    "-m",
                    "bcr2000",
                ],
                check=True,
                capture_output=True,
            )
            subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "bcfwconvert.py"),
                    "-i",
                    str(sysex_path),
                    "-I",
                    "syx",
                    "-o",
                    str(result_path),
                    "-O",
                    "os",
                ],
                check=True,
                capture_output=True,
            )

            self.assertEqual(result_path.read_bytes(), image)


if __name__ == "__main__":
    unittest.main()

