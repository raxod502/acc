import dateutil.parser

class Config:
    def default_credit_to_account(self):
        # FIXME
        return "checking"

    def default_debit_from_account(self):
        # FIXME
        return "checking"

    def default_transfer_from_account(self):
        # FIXME
        return "saving"

    def default_transfer_to_account(self):
        # FIXME
        return "checking"

    def alternate_transfer_from_account(self):
        # FIXME
        return "checking"

    def alternate_transfer_to_account(self):
        # FIXME
        return "saving"

    def make_date(self, date):
        # FIXME
        if not date:
            return None, False
        try:
            return dateutil.parser.parse(date), False
        except ValueError:
            return None, False

    def make_id(self):
        # FIXME
        return "4"
