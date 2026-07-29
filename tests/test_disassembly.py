import importlib.util
import io
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load_script(name):
    path = ROOT / "disassembly" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


da2diss = load_script("da2diss")
diss2da = load_script("diss2da")


class DisassemblyAnnotationTests(unittest.TestCase):
    def test_findlen_supports_repeated_values(self):
        self.assertEqual(diss2da.findlen("01 92 85 00*5 29 04"), 10)

    def test_extracts_instruction_comment_and_data_annotation(self):
        disassembly = io.StringIO(
            "   0: e3a00000  mov r0, #0 ; initialize\n"
            "   4: 01 02 03\n"
        )
        annotation = io.StringIO()

        diss2da.parse_diss(disassembly, annotation)

        self.assertEqual(
            annotation.getvalue(),
            ": .___ disassembly annotation\n"
            ": .daversion 0.1\n"
            "0: .cl  ; initialize\n"
            "4: .byte [3]\n",
        )

    def test_data_annotations_reconstruct_without_objdump(self):
        annotation = io.StringIO(
            ": .___ disassembly annotation\n"
            ": .daversion 0.1\n"
            "0: .byte [2]\n"
            "2: .ascii [4]\n"
        )
        output = io.StringIO()
        with tempfile.TemporaryDirectory() as directory:
            binary = Path(directory) / "sample.bin"
            binary.write_bytes(b"\x01\x01ABCD")

            da2diss.parse_da(annotation, str(binary), output)

        self.assertEqual(
            output.getvalue(),
            '       0:\t01*2\n'
            '       2:\t"ABCD"\n',
        )


if __name__ == "__main__":
    unittest.main()

