import util

class Transaction:
    def __init__(self, id_, date=None, description=None, category=None):
        self.id_ = id_
        self.date = date
        self.description = description
        self.category = category

    def __repr__(self):
        return util.make_repr(self, ["id_", "date", "description", "category"])

class CreditOrDebit(Transaction):
    def __init__(self, id_, account, value, date=None, description=None,
                 category=None):
        super().__init__(id_=id_, date=date, description=description,
                         category=category)
        self.account = account
        self.value = value

    def __repr__(self):
        return util.make_repr(self, ["id_", "account", "value", "date",
                                     "description", "category"])

class Credit(CreditOrDebit):
    def __init__(self, id_, account, value, date=None, description=None,
                 category=None):
        super().__init__(id_=id_, account=account, value=value, date=date,
                         description=description, category=category)

class Debit(CreditOrDebit):
    def __init__(self, id_, account, value, date=None, description=None,
                 category=None):
        super().__init__(id_=id_, account=account, value=-value, date=date,
                         description=description, category=category)

class Transfer(Transaction):
    def __init__(self, id_, source_account, target_account, value,
                 date=None, description=None, category=None):
        super().__init__(id_=id_, date=date, description=description,
                         category=category)
        self.source_account = source_account
        self.target_account = target_account
        self.value = value

    def __repr__(self):
        return util.make_repr(self, ["id_", "source_account", "target_account",
                                     "value", "date", "description",
                                     "category"])

class Account:
    def __init__(self, name):
        self.name = name
