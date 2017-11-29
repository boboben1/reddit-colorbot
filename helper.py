

def is_number(s):
    """ Returns True if string is a number. """
    return s.replace('.','',1).isdigit()


def s2b(s,default):
    if not s: return default
    if s == "True": return True
    if s == "False": return False
    raise ValueError("string must be empty, True or False.")

