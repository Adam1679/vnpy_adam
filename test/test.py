class A(object):
    def __init__(self, param):
        self.q = 0
        self.w = 0
        self.e = param

a = A(666)
print a.q,a.e
