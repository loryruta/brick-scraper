from op import Registry


@Registry.register
class Dummy:
    def execute(self):
        pass
