import datetime

# Values coming from https://www.ebi.ac.uk/ena/browser/view/ERC000011
not_provided_check_list = ['not applicable', 'not collected', 'not provided', 'restricted access',
                           'missing: control sample', 'missing: sample group', 'missing: synthetic construct',
                           'missing: lab stock', 'missing: third party data',
                           'missing: data agreement established pre-2023', 'missing: endangered species',
                           'missing: human-identifiable', 'missing']


def check_date(date):
    return isinstance(date, datetime.date) or \
           isinstance(date, datetime.datetime) or \
           check_date_str_format(date) or \
           str(date).lower() in not_provided_check_list


def check_date_str_format(d):
    try:
        datetime.datetime.strptime(d, "%Y-%m-%d")
        return True
    except ValueError:
        pass
    try:
        datetime.datetime.strptime(d, "%Y-%m")
        return True
    except ValueError:
        pass
    try:
        datetime.datetime.strptime(d, "%Y")
        return True
    except ValueError:
        return False
