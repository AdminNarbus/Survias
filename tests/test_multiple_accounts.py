import unittest
from unittest.mock import Mock

import account_runner


class MultipleAccountsTests(unittest.TestCase):
    def test_loads_numbered_accounts_in_numeric_order(self):
        environ = {
            "SURVIAS_RUT10": "rut-10",
            "SURVIAS_PASSWORD10": "password-10",
            "SURVIAS_RUT2": "rut-2",
            "SURVIAS_PASSWORD2": "password-2",
            "SURVIAS_RUT1": "rut-1",
            "SURVIAS_PASSWORD1": "password-1",
        }

        accounts = account_runner.load_survias_accounts(environ)

        self.assertEqual(
            accounts,
            [
                ("rut-1", "password-1"),
                ("rut-2", "password-2"),
                ("rut-10", "password-10"),
            ],
        )

    def test_rejects_an_incomplete_numbered_account(self):
        environ = {
            "SURVIAS_RUT1": "rut-1",
            "SURVIAS_PASSWORD1": "password-1",
            "SURVIAS_RUT2": "rut-2",
        }

        with self.assertRaisesRegex(ValueError, "cuenta 2"):
            account_runner.load_survias_accounts(environ)

    def test_runs_every_account_even_when_one_fails(self):
        scraper = Mock(side_effect=[False, True])
        accounts = [("rut-1", "password-1"), ("rut-2", "password-2")]

        success = account_runner.run_accounts(accounts, scraper)

        self.assertFalse(success)
        self.assertEqual(
            scraper.call_args_list,
            [
                unittest.mock.call("rut-1", "password-1"),
                unittest.mock.call("rut-2", "password-2"),
            ],
        )


if __name__ == "__main__":
    unittest.main()
