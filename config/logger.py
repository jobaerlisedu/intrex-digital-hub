import logging

def get_logger(name):
    return logging.getLogger(name)

hrm_logger = get_logger('hrm')
billing_logger = get_logger('billing')
inventory_logger = get_logger('inventory')
investment_logger = get_logger('investment')
solutions_logger = get_logger('solutions')
training_logger = get_logger('training')
accounts_logger = get_logger('accounts')
firebase_logger = get_logger('config.firebase')
