import util

class Transaction(util.Attributes):
    def __init__(self, id_, date=None, with_time=False, description=None,
                 category=None):
        self.id_ = id_
        self.date = date
        self.with_time = with_time
        self.description = description
        self.category = category
        self._keys = ["id_", "date", "with_time", "description", "category"]

class CreditOrDebit(Transaction):
    def __init__(self, id_, account, value, date=None, with_time=False,
                 description=None, category=None):
        super().__init__(id_=id_, date=date, with_time=with_time,
                         description=description, category=category)
        self.account = account
        self.value = value
        self._keys = ["id_", "account", "value", "date", "with_time",
                      "description", "category"]

class Credit(CreditOrDebit):
    def __init__(self, id_, account, value, date=None, with_time=False,
                 description=None, category=None):
        super().__init__(id_=id_, account=account, value=value,
                         date=date, with_time=with_time,
                         description=description, category=category)

class Debit(CreditOrDebit):
    def __init__(self, id_, account, value, date=None, with_time=False,
                 description=None, category=None):
        super().__init__(id_=id_, account=account, value=-value,
                         date=date, with_time=with_time,
                         description=description, category=category)

class Transfer(Transaction):
    def __init__(self, id_, source_account, target_account, value,
                 date=None, with_time=False, description=None, category=None):
        super().__init__(id_=id_, date=date, with_time=with_time,
                         description=description, category=category)
        self.source_account = source_account
        self.target_account = target_account
        self.value = value
        self._keys = ["id_", "source_account", "target_account", "value",
                      "date", "with_time", "description", "category"]

class Account(util.Attributes):
    def __init__(self, name):
        self.name = name
        self._keys = ["name"]
