import os
import re


ACCOUNT_KEY_PATTERN = re.compile(r"^SURVIAS_(RUT|PASSWORD)(\d+)$")


def load_survias_accounts(environ=None):
    environ = os.environ if environ is None else environ
    accounts_by_number = {}

    for key, value in environ.items():
        match = ACCOUNT_KEY_PATTERN.match(key)
        if not match:
            continue
        field, number = match.groups()
        accounts_by_number.setdefault(int(number), {})[field] = value.strip()

    accounts = []
    for number in sorted(accounts_by_number):
        values = accounts_by_number[number]
        if not values.get("RUT") or not values.get("PASSWORD"):
            raise ValueError(
                f"La cuenta {number} debe tener SURVIAS_RUT{number} "
                f"y SURVIAS_PASSWORD{number} configurados."
            )
        accounts.append((values["RUT"], values["PASSWORD"]))

    if not accounts:
        raise ValueError(
            "No se encontraron cuentas. Configura SURVIAS_RUT1 y "
            "SURVIAS_PASSWORD1 en el archivo .env."
        )

    return accounts


def run_accounts(accounts, scrape_func):
    results = []

    for position, (rut, password) in enumerate(accounts, start=1):
        print(f"\n{'=' * 50}")
        print(f" PROCESANDO CUENTA [{position}/{len(accounts)}] - RUT: {rut}")
        print(f"{'=' * 50}")

        try:
            success = bool(scrape_func(rut, password))
        except Exception as exc:
            print(f"Error inesperado al procesar la cuenta {position}: {exc}")
            success = False

        results.append((rut, success))

    print("\nResumen de cuentas procesadas:")
    for rut, success in results:
        status = "OK" if success else "FALLÓ"
        print(f"- RUT {rut}: {status}")

    return all(success for _, success in results)
