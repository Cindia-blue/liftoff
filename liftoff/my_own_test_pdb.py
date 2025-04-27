import pdb

def buggy_function():
    a = 5
    b = 0
    pdb.set_trace()
    return a / b  # will crash

buggy_function()