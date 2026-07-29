import hashlib
import os
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import bcfwconvert


class OfficialFirmwareCompatibilityTests(unittest.TestCase):
    @unittest.skipUnless(
        os.environ.get("BCR2000_FIRMWARE"),
        "set BCR2000_FIRMWARE to test a local official 1.10 image",
    )
    def test_bcr2000_110_decodes_and_round_trips_exactly(self):
        path = Path(os.environ["BCR2000_FIRMWARE"])
        firmware = path.read_bytes()

        self.assertEqual(
            hashlib.md5(firmware).hexdigest(),
            "9da7697dc27d5876a5fe21d2c565cde4",
        )

        dump = bcfwconvert.syx2dump(list(firmware))
        image = bcfwconvert.dump2os(dump)
        self.assertEqual(len(image), 63704)
        self.assertEqual(
            hashlib.sha256(bytes(image)).hexdigest(),
            "59a48989c252fb2b6e2a2d2fb146f40773d9a7d28ee60d69f87acd1d47916a1d",
        )

        rebuilt = bcfwconvert.dump2syx(
            bcfwconvert.os2dump(image), 0x2000, 0x15
        )
        self.assertEqual(bytes(rebuilt), firmware)


if __name__ == "__main__":
    unittest.main()

