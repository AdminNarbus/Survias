from pathlib import Path
import tempfile
import unittest

from download_utils import find_completed_excel


class DownloadUtilsTests(unittest.TestCase):
    def test_ignores_chrome_temporary_files(self):
        with tempfile.TemporaryDirectory() as directory:
            temporary = Path(directory) / ".com.google.Chrome.OwrZ8N"
            temporary.write_bytes(b"partial download")

            self.assertIsNone(find_completed_excel(directory))

    def test_returns_only_a_completed_excel_file(self):
        with tempfile.TemporaryDirectory() as directory:
            temporary = Path(directory) / ".com.google.Chrome.OwrZ8N"
            excel = Path(directory) / "Transitos_TKVT97.xlsx.xlsx"
            temporary.write_bytes(b"partial download")
            excel.write_bytes(b"completed workbook")

            self.assertEqual(find_completed_excel(directory), str(excel))


if __name__ == "__main__":
    unittest.main()
